import os
import random
import shutil
from pathlib import Path
from typing import Optional

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from utils.errores import ErrorArchivo

# -----------------------------
# Listar elementos
# -----------------------------


def listar_elementos_ruta(ruta: Path, cantidad: int = 0):
    '''
    Devuelve una lista de los elementos mp3 en la ruta ingresada.\n
    Si la cantidad es 0, devuelve todos los elementos.
    '''
    lista_mp3 = [archivo for archivo in os.listdir(ruta) if archivo.endswith('.mp3')]
    if cantidad >= len(lista_mp3) or cantidad <= 0:
        return lista_mp3
    else:
        return random.sample(lista_mp3, cantidad)


# -----------------------------
# Movimiento de archivos
# -----------------------------


def _mover_archivo_simple(archivo: Path, destino: Path) -> Path | None:
    "Traslada el archivo, si es que la ruta existe"
    try:
        if not destino:
            return None
        shutil.move(archivo, destino)
        ruta_final = destino / archivo.name
        return ruta_final
    except FileNotFoundError:
        raise ErrorArchivo(str(destino), "El archivo destino no existe")
    except Exception as e:
        raise Exception(f"Ocurrió un error: {e}") from e


def _renombrar_archivo_musica(archivo: Path):
    "Renombra el archivo con estandar [Artista - Cancion.mp3]"
    try:
        datos = obtener_datos_cancion(ruta=archivo)
        titulo = datos["tit"]
        artistas = datos["art"]
        if titulo and artistas:
            artista_principal = artistas.split("/")[0]
            base_nombre = f"{artista_principal} - {titulo}.mp3".replace("/", "-")
            ruta_final = archivo.parent / base_nombre

            contador = 2
            while ruta_final.exists():
                ruta_final = archivo.parent / f"{artista_principal} - {titulo}({contador}).mp3"
                contador += 1

            archivo.rename(ruta_final)
    except ErrorArchivo:
        raise Exception(f"Error al mover archivo: '{archivo.name}'")


def mover_y_renombrar_cancion(ruta_cancion: Path, ruta_destino: Path | None, renombrar: bool = True) -> None:
    '''
    Toma la ruta de la canción, la renombra al estandar [Artista - Cancion.mp3].\n
    Luego mueve el archivo mp3 a la ruta destino.

    Params
    - ruta_cancion: Ruta original de la canción.
    - ruta_destino: Ruta de destino para el archivo mp3.
    '''
    if not ruta_cancion and not ruta_destino:
        return None
    if not ruta_destino and not renombrar:
        # No hacer nada
        return None
    if not ruta_destino and renombrar:
        # Solo Renombrar
        _renombrar_archivo_musica(ruta_cancion)
    if ruta_destino:
        nueva_ruta_archivo = _mover_archivo_simple(ruta_cancion, ruta_destino)
        if nueva_ruta_archivo:
            _renombrar_archivo_musica(nueva_ruta_archivo)
    else:
        return None


# -----------------------------
# Obtener datos archivo MP3
# -----------------------------

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
