import io
import requests

from PIL import Image

from utils.errores import ErrorConsulta, ErrorCoverArchive
from config.setup import CORREO_PERSONAL

_TIMEOUT = 15
_HEADERS = {"User-Agent": f"ScriptBibliotecaMusical/2.5 ({CORREO_PERSONAL})"}
_RES_MAXIMA = 1200
_RES_FALLBACK = 500
_PESO_MAX = 300_000
_CAL_JPEG = 85
_CAL_JPEG_MIN = 60


# =================================
# FUNCIONES AUXILIARES  
# =================================

def get_url(url: str) -> requests.Response:
    """GET con manejo de errores centralizado."""
    if not url:
        raise ErrorConsulta("No se ingresó una url válida.", f"La url: '{url}' no es válida")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        raise ErrorCoverArchive("La petición superó el tiempo límite.", f"El sitio no respondió luego de {_TIMEOUT} segundos.")
    except requests.exceptions.ConnectionError:
        raise ErrorCoverArchive("No se pudo conectar.", "Problema de conexión con la red.")
    except requests.exceptions.HTTPError as e:
        raise ErrorCoverArchive("Error HTTP", f"{e.response.status_code}.")
    except Exception as e:
        raise ErrorCoverArchive("Error No Registrado", str(e))

def _seleccionar_imagen_frontal(imagenes: list[dict]) -> dict:
    """
    De la lista de imágenes de CAA, elige la frontal de mayor resolución.
    """
    frontales = [img for img in imagenes if img.get("front") is True]
    if not frontales:
        frontales = imagenes

    if not frontales:
        raise ErrorCoverArchive("No existen carátulas adjuntas.")

    con_thumbnails = [img for img in frontales if img.get("thumbnails")]
    return con_thumbnails[0] if con_thumbnails else frontales[0]

def _url_mejor_resolucion(imagen: dict, resolucion: int = 1200) -> str:
    """
    Elige la URL de la resolución más adecuada disponible en CAA.
    """
    thumbnails = imagen.get("thumbnails", {})

    if resolucion >= 1200 and thumbnails.get("1200"):
        return thumbnails["1200"]
    if resolucion >= 500 and thumbnails.get("500"):
        return thumbnails["500"]
    if thumbnails.get("250"):
        return thumbnails["250"]

    return imagen.get("image", "")

def _comprimir(imagen_bytes: bytes, resolucion_max: int, calidad: int) -> bytes:
    """
    Convierte la imagen a JPEG, la redimensiona si supera resolucion_max,
    y la comprime con la calidad indicada.
    Siempre retorna bytes JPEG, independiente del formato original (PNG, WEBP, etc.)
    """
    img = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")

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
    calidad = _CAL_JPEG
    while calidad >= _CAL_JPEG_MIN:
        resultado = _comprimir(imagen_bytes, _RES_MAXIMA, calidad)
        if len(resultado) <= _PESO_MAX:
            return resultado
        calidad -= 10

    resultado = _comprimir(imagen_bytes, _RES_FALLBACK, _CAL_JPEG)
    return resultado

# =================================
# FUNCIONES PRINCIPALES
# =================================

def descargar_caratula_coverarchive(resp_imgs: list[dict]) -> bytes:
    if not resp_imgs:
        raise ErrorCoverArchive("Sin datos", "No existen carátulas asociadas al álbum.")
    
    imagen = _seleccionar_imagen_frontal(resp_imgs)

    url_imagen = _url_mejor_resolucion(imagen, _RES_MAXIMA)

    if not url_imagen:
        raise ErrorCoverArchive(
            "No existen carátulas adjuntas.",
            "No se pudo seleccionar una url, pues habían url válidas."
        )

    try:
        resp = get_url(url_imagen)
        img_bytes = resp.content
    except Exception:
        raise

    try:
        return _ajustar_peso(img_bytes)
    except Exception:
        if len(img_bytes) <= _PESO_MAX:
            return img_bytes
        else:
            raise ErrorCoverArchive(
                "La imagen ha sido descartada.",
                f"La imagen de CoverArchive supera el tamaño máximo establecido: {_PESO_MAX} bytes. Tampoco se pudo ajustar el tamaño."
            )

