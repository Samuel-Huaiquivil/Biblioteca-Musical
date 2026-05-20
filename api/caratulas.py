# api/caratulas.py
# Descarga carátulas de alta calidad desde Cover Art Archive (CAA).
# CAA es el servicio oficial de imágenes de MusicBrainz.
# Docs: https://musicbrainz.org/doc/Cover_Art_Archive/API
#
# Flujo:
#   1. Si no se tiene el UUID del release, se busca en MusicBrainz.
#   2. Se consulta CAA para obtener la lista de imágenes disponibles.
#   3. Se descarga la imagen frontal de mayor resolución disponible.
#   4. Se recomprime a JPEG con calidad controlada para limitar el peso.
#   5. Si el resultado sigue siendo muy pesado, se reduce la resolución.

import io
import requests
from PIL import Image   # pip install Pillow

from api.musicbrainz import buscar_cancion_mbz, obtener_mejor_recording
from utils.errores import ErrorAPI

_URL_CAA     = "https://coverartarchive.org/release"
_TIMEOUT     = 15
_HEADERS     = {"User-Agent": "ScriptBibliotecaMusical/2.3 (raula9396@gmail.com)"}

# Límites de calidad
_RESOLUCION_DESCARGA = 1200   # px — pedimos la mejor calidad disponible
_RESOLUCION_MAXIMA   = 1200   # px — lado máximo tras redimensionar
_RESOLUCION_FALLBACK =  500   # px — si la imagen sigue pesando mucho
_PESO_MAXIMO_BYTES   = 300_000   # 300 KB — tope antes de reducir calidad
_CALIDAD_JPEG        = 85        # calidad JPEG inicial (0-100)
_CALIDAD_JPEG_MIN    = 60        # calidad mínima antes de reducir resolución


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get(url: str) -> requests.Response:
    """GET con manejo de errores centralizado."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        raise ErrorAPI("CoverArtArchive", "La petición superó el tiempo límite.")
    except requests.exceptions.ConnectionError:
        raise ErrorAPI("CoverArtArchive", "No se pudo conectar.")
    except requests.exceptions.HTTPError as e:
        raise ErrorAPI("CoverArtArchive", f"Error HTTP {e.response.status_code}.")
    except Exception as e:
        raise ErrorAPI("CoverArtArchive", str(e))


def _buscar_uuid_release(titulo: str, artista: str) -> str | None:
    """
    Busca el UUID del release (álbum) en MusicBrainz a partir de
    título y artista. Reutiliza la función ya existente en api/musicbrainz.py.
    Retorna el UUID del mejor release encontrado, o None si no hay resultados.
    """
    try:
        recordings = buscar_cancion_mbz(titulo, artista, limite=5)
        mejor = obtener_mejor_recording(recordings)
        if not mejor or not mejor.releases:
            return None
        # Preferir release oficial con fecha conocida
        oficiales = [r for r in mejor.releases if r.status.lower() == "official"]
        candidatos = oficiales or mejor.releases
        mejor_release = min(candidatos, key=lambda r: r.date or "9999")
        return mejor_release.id or None
    except ErrorAPI:
        return None


def _seleccionar_imagen_frontal(imagenes: list[dict]) -> dict | None:
    """
    De la lista de imágenes de CAA, elige la frontal de mayor resolución.
    CAA marca las imágenes frontales con type 'Front'.
    """
    frontales = [img for img in imagenes if img.get("front") is True]
    if not frontales:
        # Si no hay ninguna marcada como frontal, tomar la primera disponible
        frontales = imagenes

    if not frontales:
        return None

    # Preferir la que tenga thumbnails (indica que fue procesada correctamente)
    con_thumbnails = [img for img in frontales if img.get("thumbnails")]
    return con_thumbnails[0] if con_thumbnails else frontales[0]


def _url_mejor_resolucion(imagen: dict, resolucion: int = 1200) -> str:
    """
    Elige la URL de la resolución más adecuada disponible en CAA.
    CAA ofrece: 250, 500, 1200 px (y la original sin redimensionar).
    """
    thumbnails = imagen.get("thumbnails", {})

    # Intentar en orden de preferencia según la resolución pedida
    if resolucion >= 1200 and thumbnails.get("1200"):
        return thumbnails["1200"]
    if resolucion >= 500 and thumbnails.get("500"):
        return thumbnails["500"]
    if thumbnails.get("250"):
        return thumbnails["250"]

    # Fallback: URL original de la imagen
    return imagen.get("image", "")


def _comprimir(imagen_bytes: bytes, resolucion_max: int, calidad: int) -> bytes:
    """
    Convierte la imagen a JPEG, la redimensiona si supera resolucion_max,
    y la comprime con la calidad indicada.
    Siempre retorna bytes JPEG, independiente del formato original (PNG, WEBP, etc.)
    """
    img = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")

    # Redimensionar si algún lado supera el máximo (mantiene proporción)
    if img.width > resolucion_max or img.height > resolucion_max:
        img.thumbnail((resolucion_max, resolucion_max), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=calidad, optimize=True)
    return buffer.getvalue()


def _ajustar_peso(imagen_bytes: bytes) -> bytes:
    """
    Reduce la calidad o resolución de la imagen hasta que entre en el peso máximo.
    Estrategia:
      1. Intentar reducir calidad JPEG gradualmente.
      2. Si sigue siendo muy pesada, reducir resolución al fallback (500px).
    """
    # Intentar reducir calidad primero (menos pérdida visual)
    calidad = _CALIDAD_JPEG
    while calidad >= _CALIDAD_JPEG_MIN:
        resultado = _comprimir(imagen_bytes, _RESOLUCION_MAXIMA, calidad)
        if len(resultado) <= _PESO_MAXIMO_BYTES:
            return resultado
        calidad -= 10

    # Si la calidad mínima no alcanza, reducir la resolución
    resultado = _comprimir(imagen_bytes, _RESOLUCION_FALLBACK, _CALIDAD_JPEG)
    return resultado


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def obtener_caratula(
    titulo: str,
    artista: str,
    uuid_release: str | None = None,
) -> bytes | None:
    """
    Descarga la carátula frontal de un álbum desde Cover Art Archive.

    Parámetros:
    - titulo:        título de la canción (para buscar en MusicBrainz si falta el UUID).
    - artista:       nombre del artista.
    - uuid_release:  UUID del release en MusicBrainz. Si ya lo tienes (de una
                     búsqueda previa), se usa directamente y se evita una consulta extra.

    Retorna:
    - bytes JPEG de la carátula, optimizados para no superar 300KB.
    - None si no se encontró carátula o hubo un error no crítico.
    """
    # Paso 1 — Obtener UUID del release
    if not uuid_release:
        uuid_release = _buscar_uuid_release(titulo, artista)

    if not uuid_release:
        return None

    # Paso 2 — Consultar CAA para obtener lista de imágenes
    try:
        resp = _get(f"{_URL_CAA}/{uuid_release}")
        data = resp.json()
    except ErrorAPI:
        return None

    imagenes = data.get("images", [])
    if not imagenes:
        return None

    # Paso 3 — Seleccionar la imagen frontal
    imagen = _seleccionar_imagen_frontal(imagenes)
    if not imagen:
        return None

    # Paso 4 — Descargar la imagen en la mejor resolución disponible
    url_imagen = _url_mejor_resolucion(imagen, _RESOLUCION_DESCARGA)
    if not url_imagen:
        return None

    try:
        resp_imagen = _get(url_imagen)
        imagen_bytes = resp_imagen.content
    except ErrorAPI:
        return None

    # Paso 5 — Comprimir y ajustar peso
    try:
        return _ajustar_peso(imagen_bytes)
    except Exception:
        # Si Pillow falla (formato raro), retornar los bytes originales
        return imagen_bytes if len(imagen_bytes) <= _PESO_MAXIMO_BYTES else None