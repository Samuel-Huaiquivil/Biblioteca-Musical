# utils/caratulas.py
# Gestión de carátula en Imágenes Locales

import os
import requests
from pathlib import Path
from requests.exceptions import RequestException, Timeout, HTTPError
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.id3._frames import APIC
from mutagen.id3._util import ID3NoHeaderError

from models.schemas import Caratula, DatosCaratula, SalidaCaratula
from utils.errores import ErrorArchivo, ErrorBaseDatos, ErrorInsercion
from config.setup import _ruta_caratulas
from database.caratulas import pipeline_caratula
if _ruta_caratulas:
    R_CARAT = Path(_ruta_caratulas)

# ---------------------------------------------------------------------------
# Funciones Auxiliares.
# ---------------------------------------------------------------------------


def _listar_todas_las_caratulas(ruta_busqueda: Path):
    '''
    Devuelve una lista de los elementos jpg o png.

    Las carátulas están en un formato := {id_itunes}.jpg -- {id_mbz}.jpg 
    '''
    lista_jpg = [archivo for archivo in os.listdir(ruta_busqueda) if archivo.endswith('.jpg')]
    lista_png = [archivo for archivo in os.listdir(ruta_busqueda) if archivo.endswith('.png')]
    return lista_jpg + lista_png


def _descargar_caratula_localmente(
    url_descarga: str,
    nombre_archivo: str,
    ruta_destino: Path = R_CARAT
) -> Path | None:
    """
    Descarga la carátula desde la URL proporcionada.
    Retorna la ruta al archivo si la descarga es exitosa, None si no se pudo.
    """
    try:
        if not url_descarga or not url_descarga.startswith(("http://", "https://")):
            raise ValueError("URL inválida para descarga de carátula.")

        response = requests.get(url_descarga, timeout=10, stream=True)
        response.raise_for_status()  # lanza HTTPError si el código no es 200-299

        ruta_destino.mkdir(parents=True, exist_ok=True)
        ruta_archivo = ruta_destino / f"{nombre_archivo}.jpg"

        with open(ruta_archivo, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if ruta_archivo.exists() and ruta_archivo.stat().st_size > 0:
            return ruta_archivo
        return None

    except (Timeout, HTTPError) as e:
        raise ErrorArchivo(nombre_archivo, f"Error HTTP/Timeout al descargar carátula: {e}") from e
    
    except RequestException as e:
        raise ErrorArchivo(nombre_archivo, f"Error de conexión al descargar carátula: {e}") from e
    
    except Exception as e:
        raise ErrorArchivo(nombre_archivo, f"Error inesperado al descargar carátula: {e}") from e


def _busqueda_caratula(nombre_archivo: str, ruta_caratulas: Path) -> Path | None:
    "Busca en la carpeta de carátula para ver si ya está descargada"
    lista_caratulas = _listar_todas_las_caratulas(ruta_busqueda=ruta_caratulas)
    if not lista_caratulas:
        return None
    for caratula in lista_caratulas:
        if nombre_archivo == caratula[:-4]:
            return ruta_caratulas / caratula
    return None


def _cargar_id3(ruta: Path) -> ID3:
    """
    Carga el objeto ID3 del archivo. Si no tiene header, lo crea.
    """
    try:
        return ID3(ruta)
    except ID3NoHeaderError:
        audio = MP3(ruta)
        audio.add_tags(ID3=ID3)
        assert isinstance(audio.tags, ID3) 
        return audio.tags


def _convertir_a_datos_caratula(caratula_local: SalidaCaratula) -> DatosCaratula:
    if not caratula_local:
        raise ErrorBaseDatos("Error al convertir a Datos Carátula")
    if not caratula_local.imagen_bytes:
        raise ErrorBaseDatos("No existe carátula valida")
    return DatosCaratula(
        cod_album=caratula_local.id_album,
        imagen_bytes=caratula_local.imagen_bytes
    )


def _ruta_a_datos_caratula(ruta_imagen: Path) -> DatosCaratula:
    nombre_archivo = ruta_imagen.stem
    try:
        with open(ruta_imagen, "rb") as f:
            return DatosCaratula(
                cod_album=1,
                imagen_bytes=f.read()
            )
    except Exception as e:
        raise Exception (f"Error al operar el archivo") from e
    

def manejar_bytes(ruta: Path) -> bytes:
    """
    Lee un archivo de imagen desde la ruta dada y retorna sus bytes.
    """
    try:
        with open(ruta, "rb") as f:
            return f.read()
    except Exception as e:
        raise ErrorArchivo(ruta.name, f"Error al leer bytes de la carátula: {e}") from e


# ---------------------------------------------------------------------------
# Insertar caratula - A través de la clase DatosCaratula
# ---------------------------------------------------------------------------

def escribir_caratula(ruta: Path, caratula: DatosCaratula) -> None:
    """
    Inserta la carátula del álbum como tag APIC en el archivo .mp3.
    Llama a esta función por separado para mantener la lógica de imagen
    desacoplada de los tags de texto.

    APIC type=3 → Cover (front) — el tipo que usan todos los reproductores.
    """
    if not ruta.exists():
        raise ErrorArchivo(str(ruta), "El archivo no existe.")

    try:
        tags = _cargar_id3(ruta)

        tags["APIC:"] = APIC(
            encoding=3,         # UTF-8
            mime="image/jpeg",  # la mayoría de carátulas de iTunes son JPEG
            type=3,             # Cover (front)
            desc="Cover",
            data=caratula.imagen_bytes,
        )

        tags.save(ruta, v2_version=3)

    except Exception as e:
        raise ErrorArchivo(str(ruta), f"Error al escribir carátula: {e}") from e


# ===========================================================================
# PIPELINE CARATULAS - Gestiona la inserción de las carátulas.
# ===========================================================================

def gestion_caratulas(
    caratula: Caratula,
    ruta_caratulas: Path,
    base_datos: Path | None = None
) -> DatosCaratula:
    # Busqueda en la base de datos
    salida_caratula = pipeline_caratula(caratula, caratula.codigo_album, base_datos)
    if salida_caratula.imagen_bytes:
        return _convertir_a_datos_caratula(salida_caratula)
    
    # Busqueda local
    codigo_str = str(caratula.codigo_album)
    ruta_img = _busqueda_caratula(codigo_str, ruta_caratulas)

    if ruta_img:
        return _ruta_a_datos_caratula(ruta_imagen=ruta_img)

    try:
        #Descarga Local
        ruta = _descargar_caratula_localmente(
            caratula.url_caratula,
            str(caratula.codigo_album),
            ruta_caratulas
            )
        if ruta:
            return _ruta_a_datos_caratula(ruta_imagen=ruta)
        else:
            raise ErrorInsercion("Caratula", "Error gestión archivo")
    except Exception as e:
        raise ErrorInsercion ("Caratula", "Error al gestionar carátulas") from e
