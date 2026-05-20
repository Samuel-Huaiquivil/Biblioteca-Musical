# processing/id3.py
# Escribe los tags ID3 en archivos .mp3 usando los datos del dominio.
import mimetypes
from pathlib import Path
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.id3._util import ID3NoHeaderError
from mutagen.id3._frames import TIT1, TIT2, TIT3, TPE1, TPE2, TALB, TDRC, TRCK, TCON, TPOS, APIC

from models.schemas import DatosMusica, DatosCaratula
from utils.errores import ErrorArchivo


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

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


def _formatear_artistas(principal: str, colaboradores: list[str]) -> str:
    """
    Combina artista principal y colaboradores en un string separado por '/'.
    Formato estándar ID3 para múltiples artistas en TPE1.
    Ejemplo: 'Artista Principal/Colaborador 1/Colaborador 2'
    """
    todos = [principal] + [a for a in colaboradores if a]
    return "/".join(todos)


# ---------------------------------------------------------------------------
# Escritura principal
# ---------------------------------------------------------------------------

def escribir_tags(ruta: Path, datos: DatosMusica) -> None:
    """
    Escribe los tags ID3 en el archivo .mp3.
    Sobrescribe los tags existentes con los datos del dominio.

    Tags escritos:
    - TIT2: título de la canción
    - TIT1: grupo/colección (opcional)
    - TIT3: subtítulo, ej. "feat. X" (opcional)
    - TPE1: artista(s) — principal + colaboradores separados por '/'
    - TPE2: artista del álbum (artista principal solo)
    - TALB: título del álbum
    - TDRC: año de lanzamiento
    - TRCK: número de pista
    - TCON: género musical
    """
    if not ruta.exists():
        raise ErrorArchivo(str(ruta), "El archivo no existe.")
    if ruta.suffix.lower() != ".mp3":
        raise ErrorArchivo(str(ruta), "El archivo no es un .mp3.")

    try:
        limpiar_tags(ruta)
        tags = _cargar_id3(ruta)

        # Obligatorios
        tags[TIT2.__name__] = TIT2(encoding=3, text=datos.titulo)
        tags[TPE1.__name__] = TPE1(encoding=3, text=_formatear_artistas(
            datos.artista_principal, datos.artistas_colab
        ))
        tags[TPE2.__name__] = TPE2(encoding=3, text=datos.artista_principal)
        tags[TALB.__name__] = TALB(encoding=3, text=datos.album)
        tags[TDRC.__name__] = TDRC(encoding=3, text=str(datos.anio))
        tags[TRCK.__name__] = TRCK(encoding=3, text=str(datos.num_pista))
        tags[TCON.__name__] = TCON(encoding=3, text=datos.genero)

        # Opcionales — solo se escriben si tienen valor
        if datos.subtitulo:
            tags[TIT3.__name__] = TIT3(encoding=3, text=datos.subtitulo)

        tags.save(ruta, v2_version=3)  # ID3v2.3 — máxima compatibilidad

    except Exception as e:
        raise ErrorArchivo(str(ruta), f"Error al escribir tags: {e}") from e


def limpiar_tags(ruta: Path) -> None:
    """
    Elimina todos los tags ID3 del archivo.
    Útil antes de una reescritura completa o para limpiar archivos corruptos.
    """
    if not ruta.exists():
        raise ErrorArchivo(str(ruta), "El archivo no existe.")
    try:
        tags = ID3(ruta)
        tags.delete()
    except ID3NoHeaderError:
        pass  # Si no tiene tags, no hay nada que limpiar
    except Exception as e:
        raise ErrorArchivo(str(ruta), f"Error al limpiar tags: {e}") from e


# ---------------------------------------------------------------------------
# Conversión desde modelos del dominio
# ---------------------------------------------------------------------------

def modelos_a_datos_musica(clases: dict) -> DatosMusica:
    """
    Convierte el diccionario de clases del dominio al modelo DatosMusica
    listo para escribir con escribir_tags().

    Entrada esperada:
    {
        'genero':   Genero,
        'artistas': GrupoArtistas,
        'album':    Album,
        'cancion':  Cancion,
    }
    """
    genero = clases["genero"]
    artistas = clases["artistas"]
    album = clases["album"]
    cancion = clases["cancion"]

    return DatosMusica(
        titulo=cancion.titulo,
        album=album.titulo,
        artista_principal=artistas.principal,
        artistas_colab=(artistas.colaboradores or []) + (artistas.feat or []),
        anio=album.lanzamiento.year,
        num_pista=cancion.num_pista,
        genero=genero.nombre,
    )

# ---------------------------------------------------------------------------
# Gestión de carátulas
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
            data=caratula.imagen,
        )

        tags.save(ruta, v2_version=3)

    except Exception as e:
        raise ErrorArchivo(str(ruta), f"Error al escribir carátula: {e}") from e


def insertar_caratula_desde_ruta(archivo_mp3: Path, ruta_img: Path) -> bool:
    "Inserta una carátula desde una imagen descargada"
    if not archivo_mp3.exists():
        raise ErrorArchivo(str(archivo_mp3), "El archivo no existe.")
    
    if not ruta_img.exists():
        raise ErrorArchivo(str(ruta_img), "La imagen no existe.")

    try:
        tags = _cargar_id3(archivo_mp3)

        # Eliminar la carátula anterior, si es que la tiene.
        if tags["APIC:"]:
            del tags["APIC:"]

        # Detectar el tipo de imagen.
        mime_type, _ = mimetypes.guess_type(ruta_img)
        if mime_type is None:
            mime_type = "image/jpeg"

        with open(ruta_img, 'rb') as img:
            tags["APIC:"] = APIC(
                encoding=3,              # UTF-8
                mime=mime_type,          # tipo detectado
                type=3,                  # portada frontal
                desc="Cover",
                data=img.read()
            )

        tags.save(archivo_mp3, v2_version=3)

        return True
    except Exception as e:
        raise ErrorArchivo(str(archivo_mp3), f"Error al insertar carátula: {e}") from e


def insertar_caratula_desde_base_datos(archivo_mp3: Path, id_caratula: int, db: Path | None) -> bool:
    if not archivo_mp3.exists():
        raise ErrorArchivo(str(archivo_mp3), "El archivo no existe.")
    try:
        from config.settings import get_connection
        with get_connection(base_datos=db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT imagen_bytes FROM Caratulas WHERE id_caratula = ?;", (id_caratula,)
            )
            fila = cursor.fetchone()
        # Objeto en bytes cargado
        imagen_bytes = fila[0]

        # Insertar Carátula con ID3
        tags = _cargar_id3(archivo_mp3)
        # Eliminar la carátula anterior, si es que existe.
        if tags["APIC:"]:
            del tags["APIC:"]

        tags["APIC:"] = APIC(
            encoding=3,         # UTF-8
            mime="image/jpeg",  # la mayoría de carátulas de iTunes son JPEG
            type=3,             # Cover (front)
            desc="Cover",
            data=imagen_bytes,
        )

        tags.save(archivo_mp3, v2_version=3)

        return True
    except Exception as e:
        raise ErrorArchivo(str(archivo_mp3), f"Error al insertar carátula: {e}") from e


def insertar_caratula_desde_datos_caratula(archivo_mp3: Path, caratula: DatosCaratula) -> bool:
    """
    Inserta la carátula del álbum como tag APIC en el archivo .mp3.
    """
    if not archivo_mp3.exists():
        raise ErrorArchivo(str(archivo_mp3), "El archivo no existe.")

    if caratula.imagen:
        try:
            tags = _cargar_id3(archivo_mp3)

            # Eliminar la carátula anterior, si es que la tiene.
            if tags["APIC:"]:
                del tags["APIC:"]

            tags["APIC:"] = APIC(
                encoding=3,         # UTF-8
                mime="image/jpeg",  # la mayoría de carátulas de iTunes son JPEG
                type=3,             # Cover (front)
                desc="Cover",
                data=caratula.imagen,
            )

            tags.save(archivo_mp3, v2_version=3)

            return True
        
        except Exception as e:
            raise ErrorArchivo(str(archivo_mp3), f"Error al escribir carátula: {e}") from e
    
    else:
        try:
            import requests
            response = requests.get(caratula.url_caratula, timeout=10, stream=True)
            if response.status_code == 200:
                imagen_bytes = response.content
            else:
                raise Exception(f"Error al descargar carátula iTunes.")

            tags = _cargar_id3(archivo_mp3)

            # Eliminar la carátula anterior, si es que la tiene.
            if tags["APIC:"]:
                del tags["APIC:"]

            tags["APIC:"] = APIC(
                encoding=3,         # UTF-8
                mime="image/jpeg",  # la mayoría de carátulas de iTunes son JPEG
                type=3,             # Cover (front)
                desc="Cover",
                data=imagen_bytes,
            )

            tags.save(archivo_mp3, v2_version=3)

            return True

        except Exception as e:
            raise ErrorArchivo(str(archivo_mp3), f"Error al escribir carátula: {e}") from e
    