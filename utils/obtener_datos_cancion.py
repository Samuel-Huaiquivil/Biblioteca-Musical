# utils/obtener_datos_cancion.py
# Extrae título y artista de un archivo .mp3 por tres métodos en cascada.
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from pathlib import Path
from typing import Optional
from utils.errores import ErrorArchivo


# Tipo de retorno interno: (titulo, artista) o None si no se pudo obtener
_DatosCancion = tuple[str, str]


def _desde_id3(ruta: Path) -> Optional[_DatosCancion]:
    """Intenta leer título y artista desde tags ID3 estándar."""
    try:
        audio = MP3(ruta, ID3=ID3)
        titulo = audio["TIT2"].text[0]
        artista = audio["TPE1"].text[0]
        if titulo and artista:
            return titulo.strip(), artista.strip()
    except (KeyError, Exception):
        pass
    return None


def _desde_easy_id3(ruta: Path) -> Optional[_DatosCancion]:
    """Intenta leer título y artista desde EasyID3."""
    try:
        audio = MP3(ruta, ID3=EasyID3)
        titulos = audio.get("title", [])
        artistas = audio.get("artist", [])
        titulo = titulos[0] if titulos else ""
        artista = artistas[0] if artistas else ""
        if titulo and artista:
            return titulo.strip(), artista.strip()
    except Exception:
        pass
    return None


def _desde_nombre_archivo(ruta: Path) -> Optional[_DatosCancion]:
    """
    Intenta extraer título y artista del nombre del archivo.
    Asume formato: 'Artista - Titulo.mp3'
    Usa maxsplit=1 para no cortar en guiones dentro del título.
    """
    partes = ruta.stem.split(" - ", maxsplit=1)
    if len(partes) == 2:
        artista, titulo = partes
        return titulo.strip(), artista.strip()
    return None


def obtener_datos_cancion(ruta: Path) -> dict[str, str]:
    """
    Obtiene título y artista de un archivo .mp3.
    Intenta en orden: ID3 → EasyID3 → nombre de archivo.
    Retorna {'tit': ..., 'art': ...} con strings vacíos si no encuentra nada.
    """
    if not ruta.exists():
        raise ErrorArchivo(str(ruta), "El archivo no existe.")

    for metodo in [_desde_id3, _desde_easy_id3, _desde_nombre_archivo]:
        resultado = metodo(ruta)
        if resultado:
            titulo, artista = resultado
            return {"tit": titulo, "art": artista}

    return {"tit": "", "art": ""}
