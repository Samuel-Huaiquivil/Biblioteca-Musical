import random
import shutil
from pathlib import Path
from typing import Optional

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from utils.errores import ErrorArchivo, ErrorImagen

# -----------------------------
# Listar elementos
# -----------------------------

def listar_mp3(ruta: Path, cantidad: int = 0, recursivo: bool = False) -> list[Path]:
    '''
    Devuelve una lista de archivos .mp3 en la ruta ingresada.

    Params
    - ruta: Carpeta donde buscar.
    - cantidad: Si es 0 o negativa, devuelve todos los archivos encontrados.
                Si no, devuelve una muestra aleatoria de ese tamaño.
    - recursivo: Si es True, busca también en subcarpetas.
    '''
    patron = "*.mp3"
    archivos = list(ruta.rglob(patron) if recursivo else ruta.glob(patron))

    if cantidad <= 0 or cantidad >= len(archivos):
        return archivos
    return random.sample(archivos, cantidad)


def listar_imagenes(ruta: Path, recursivo: bool = False) -> list[Path]:
    patron = "*.jpg"
    archivos = list(ruta.rglob(patron) if recursivo else ruta.glob(patron))
    return archivos


# -----------------------------
# Movimiento de archivos
# -----------------------------

def _mover_archivo_simple(archivo: Path, destino: Path) -> Path:
    "Traslada el archivo a destino y devuelve la ruta final."
    if not destino.exists():
        raise ErrorArchivo(str(destino), "El archivo destino no existe")
    try:
        shutil.move(str(archivo), str(destino))
        return destino / archivo.name
    except OSError as e:
        raise ErrorArchivo(str(archivo), f"No se pudo mover el archivo: {e}") from e


def _generar_nombre_disponible(carpeta: Path, artista: str, titulo: str) -> Path:
    "Genera un nombre único con el estándar [Artista - Cancion.mp3]"
    base = f"{artista} - {titulo}.mp3".replace("/", "-")
    ruta = carpeta / base

    contador = 2
    while ruta.exists():
        ruta = carpeta / f"{artista} - {titulo}({contador}).mp3".replace("/", "-")
        contador += 1
    return ruta


def _renombrar_archivo_musica(archivo: Path) -> Path:
    "Renombra el archivo con estándar [Artista - Cancion.mp3]. Devuelve la ruta final."
    try:
        datos = obtener_datos_cancion(ruta=archivo)
    except ErrorArchivo as e:
        raise Exception(f"Error al leer metadata de '{archivo.name}'") from e

    titulo, artistas = datos.get("tit"), datos.get("art")
    if not titulo or not artistas:
        # Sin metadata suficiente, dejamos el archivo como está.
        return archivo

    artista_principal = artistas.split("/")[0]
    ruta_final = _generar_nombre_disponible(archivo.parent, artista_principal, titulo)
    archivo.rename(ruta_final)
    return ruta_final


def mover_y_renombrar_cancion(
    ruta_cancion: Path,
    ruta_destino: Path | None = None,
    renombrar: bool = True,
) -> Path | None:
    '''
    Mueve la canción a ruta_destino (si se indica) y opcionalmente
    la renombra al estándar [Artista - Cancion.mp3].

    Params
    - ruta_cancion: Ruta original de la canción.
    - ruta_destino: Ruta de destino para el archivo mp3. Si es None, no se mueve.
    - renombrar: Si es True, renombra el archivo según sus metadatos.
    '''
    if not ruta_cancion:
        return None

    ruta_actual = ruta_cancion
    if ruta_destino:
        ruta_actual = _mover_archivo_simple(ruta_cancion, ruta_destino)

    if renombrar:
        ruta_actual = _renombrar_archivo_musica(ruta_actual)

    return ruta_actual


# -----------------------------
# Guardar bytes Imagen
# -----------------------------

def guardar_bytes_imagen(bytes_img: bytes, nombre_img: str, ruta: Path) -> Path:
    "Guarda los bytes de una imagen como .jpg en la ruta indicada."
    ruta.mkdir(parents=True, exist_ok=True)
    ruta_archivo = ruta / f"{nombre_img}.jpg"

    try:
        ruta_archivo.write_bytes(bytes_img)
    except OSError as e:
        raise ErrorImagen(nombre_img, f"No se pudo escribir el archivo: {e}") from e

    if not ruta_archivo.exists() or ruta_archivo.stat().st_size == 0:
        raise ErrorImagen(nombre_img, "La imagen no ha podido ser guardada.")

    return ruta_archivo

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
