import os
from typing import Any, Dict
import requests
from pathlib import Path

from config.settings import RUTA_CARATULAS
from database.repository import buscar_album_cod_itunes, buscar_caratula
from models.schemas import DatosCaratula, Album
from processing.id3 import insertar_caratula_desde_base_datos, insertar_caratula_desde_datos_caratula, insertar_caratula_desde_ruta
from utils.errores import ErrorArchivo

def _listar_todas_las_caratulas(ruta_caratulas: Path):
    '''
    Devuelve una lista de los elementos jpg o png.
    '''
    lista_jpg = [archivo for archivo in os.listdir(ruta_caratulas) if archivo.endswith('.jpg')]
    lista_png = [archivo for archivo in os.listdir(ruta_caratulas) if archivo.endswith('.png')]
    return lista_jpg + lista_png


def descargar_caratula(caratula: DatosCaratula, ruta_destino: Path) -> bool:
    """
    Descarga la carátula desde iTunes usando la clase proporcionada.
    Retorna True si logra descargar la carátula, False si no se pudo.
    """
    try:
        response = requests.get(caratula.url_caratula, timeout=10, stream=True)
        if response.status_code == 200:
            ruta_archivo = ruta_destino / f"{caratula.codigo_album}.jpg"
            with open(ruta_archivo, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            raise Exception(f"Error al descargar carátula iTunes. Código: {response.status_code}")

    except Exception as e:
        raise Exception(f"Error al descargar carátula iTunes: {e}") from e

# ===========================================================================
# BÚSQUEDAS — retornan el id local o 0 si no existe
# ===========================================================================


def busqueda_ruta_caratula(album: Album, ruta_caratulas: Path) -> Path | None:
    "Busca en la carpeta de carátula para ver si ya está descargada"
    id_album = album.codigo_itunes
    lista_caratulas = _listar_todas_las_caratulas(ruta_caratulas=ruta_caratulas)
    for caratula in lista_caratulas:
        if str(id_album) == caratula[:-4]:
            return ruta_caratulas / caratula
    return None
    

def busqueda_db_caratula(album: Album, db: Path | None = None) -> int:
    "Busca la carátula en la base de datos local"
    id_album = buscar_album_cod_itunes(album.codigo_itunes, db)
    if id_album:
        id_caratula = buscar_caratula(id_album=id_album, db=db)
        return id_caratula if id_caratula else 0
    return 0


def insertar_caratula_pipeline(
        ruta_archivo_mp3: Path, 
        ruta_caratulas: Path,
        dicc_clases: Dict[str, Any], 
        datos_caratula: DatosCaratula,
        base_datos: Path | None = None
):
    '''
    Orden de búsqueda para insertar Carátula
    1) Carátulas descargadas localmente.
    2) Carátulas en la base de datos.
    3) Descargar Carátula con la URL.
    '''
    intentos = [
        lambda: (
            ruta := busqueda_ruta_caratula(album=dicc_clases["album"], ruta_caratulas=ruta_caratulas)
        ) and insertar_caratula_desde_ruta(ruta_archivo_mp3, ruta),
        
        lambda: (
            id_caratula := busqueda_db_caratula(album=dicc_clases["album"], db=base_datos)
        ) and insertar_caratula_desde_base_datos(ruta_archivo_mp3, id_caratula, base_datos),
        
        lambda: insertar_caratula_desde_datos_caratula(ruta_archivo_mp3, datos_caratula)
    ]

    try:
        for intento in intentos:
            resultado = intento()
            if resultado: 
                return True
        return False
    except Exception as e:
        raise ErrorArchivo(str(ruta_archivo_mp3), f"Error al Insertar Carátula. {e}") from e

