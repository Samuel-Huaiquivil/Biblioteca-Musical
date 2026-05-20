import os
import shutil
from pathlib import Path

from utils.obtener_datos_cancion import obtener_datos_cancion
from utils.errores import ErrorArchivo
from utils.listar_mp3 import listar_elementos_ruta


def _mover_archivo_simple(archivo: Path, destino: Path) -> Path | None:
    try:
        if not destino:
            return None
        shutil.move(archivo, destino)
        ruta_final = destino / archivo.name
        return ruta_final
    except FileNotFoundError:
        print("El archivo no existe")
    except Exception as e:
        raise Exception(f"Ocurrió un error: {e}") from e

def _renombrar_archivo_musica(archivo: Path):
    try:
        datos = obtener_datos_cancion(ruta=archivo)
        titulo = datos["tit"]
        artista = datos["art"]
        if titulo and artista:
            artista_principal = artista.split("/")[0]
            nuevo_nombre = f"{artista_principal} - {titulo}.mp3".replace("/", "-")
            ruta_final = archivo.parent / nuevo_nombre
            archivo.rename(ruta_final)
            return None
    except ErrorArchivo:
        raise Exception(f"Error al mover archivo: '{archivo.name}'")

def mover_y_renombrar_cancion(ruta_cancion: Path, ruta_destino: Path) -> None:
    '''
    Toma la ruta de la canción, la renombra al estandar [Artista - Cancion.mp3].\n
    Luego mueve el archivo mp3 a la ruta destino.

    Params
    - ruta_cancion: Ruta original de la canción.
    - ruta_destino: Ruta de destino para el archivo mp3.
    '''
    nueva_ruta_archivo = _mover_archivo_simple(ruta_cancion, ruta_destino)
    if nueva_ruta_archivo:
        _renombrar_archivo_musica(nueva_ruta_archivo)