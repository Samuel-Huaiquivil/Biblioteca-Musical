# utils/id3.py
import mimetypes

from pathlib import Path
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.id3._util import ID3NoHeaderError
from mutagen.id3._frames import (TIT2, TIT3, TPE1, TPE2, TALB, TDRC, TRCK, TCON, TPOS, APIC)

from models.schemas_v5 import DatosMusica
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
    except Exception as e:
        raise ErrorArchivo(f"Error al procesar archivo: '{ruta.name}'.", str(e)) from e


def _formatear_artistas(principal: str, colaboradores: list[str]) -> str:
    """
    Combina artista principal y colaboradores en un string separado por '/'.
    Formato estándar ID3 para múltiples artistas en TPE1.
    Ejemplo: 'Artista Principal/Colaborador 1/Colaborador 2'
    """
    todos = [principal] + [a for a in colaboradores if a]
    return "/".join(todos)


def _limpiar_tags(ruta: Path) -> None:
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
        raise ErrorArchivo(f"Error al limpiar tags del archivo: '{ruta.name}'.",f" Detalles: {str(e)}.") from e


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
        raise ErrorArchivo(f"El archivo '{ruta.name}' no existe.")
    if ruta.suffix.lower() != ".mp3":
        raise ErrorArchivo(f"El archivo '{ruta.name}' no es un .mp3.")

    try:
        _limpiar_tags(ruta)
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

        tags.save(ruta, v2_version=3)

    except Exception as e:
        raise ErrorArchivo(f"Error al escribir tags: '{ruta.name}'.", f" Detalles: {e}.") from e


def incrustar_portada(ruta_mp3: Path, ruta_img: Path):
    """Incrusta la imagen dentro del archivo MP3 como portada frontal."""
    if not ruta_mp3.exists():
        raise ErrorArchivo(f"El archivo '{ruta_mp3.name}' no existe.")
    if ruta_mp3.suffix.lower() != ".mp3":
        raise ErrorArchivo(f"El archivo '{ruta_mp3.name}' no es un .mp3.")
    if not ruta_img.exists():
        raise ErrorArchivo(f"El archivo '{ruta_img.name}' no existe.")

    try:
        audio = _cargar_id3(ruta=ruta_mp3)

        # Eliminar las carátulas existentes.
        audio.delall("APIC")

        mime_type, _ = mimetypes.guess_type(ruta_img)
        if mime_type is None:
            mime_type = "image/jpeg"

        with open(ruta_img, 'rb') as img:
            audio.add(APIC(
                encoding=3,              # UTF-8
                mime=mime_type,          # tipo detectado
                type=3,                  # portada frontal
                desc="Front Cover",
                data=img.read()
            ))
        audio.save()

        return None

    except Exception as e:
        raise ErrorArchivo(f"Problemas al insertar tags.", f"Archivo: {ruta_mp3.name}. Detalles: {e}") from e
