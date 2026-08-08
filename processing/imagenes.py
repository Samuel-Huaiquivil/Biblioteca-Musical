import io
from pathlib import Path
import requests
from PIL import Image, UnidentifiedImageError

from utils.errores import ErrorConsulta, ErrorCoverArchive, ErrorImagen, ErrorItunes

_TIMEOUT = 15
_HEADERS = {"User-Agent": "ScriptBibliotecaMusical/2.3 (raula9396@gmail.com)"}
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
        raise ErrorConsulta("La petición superó el tiempo límite.", f"El sitio no respondió luego de {_TIMEOUT} segundos.")
    except requests.exceptions.ConnectionError:
        raise ErrorConsulta("No se pudo conectar.", "Problema de conexión con la red.")
    except requests.exceptions.HTTPError as e:
        raise ErrorConsulta("Error HTTP", f"{e.response.status_code}.")
    except Exception as e:
        raise ErrorConsulta("Error No Registrado", str(e))

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

def descargar_estandar_mbz(resp_imgs: list[dict]) -> bytes:
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
                f"La imagen de CoverArchive supera el tamaño máximo establecido: {_PESO_MAX} bytes. Tampoco se pudo ajustar el tamanño."
            )
    

def descargar_estandar_itunes(url_descarga: str) -> bytes:
    if not url_descarga:
        raise ErrorItunes("La url no es válida.", "No se pudo descargar la imagen pues la url no es válida.")
    try:
        resp = get_url(url_descarga)
        return resp.content
    except Exception:
        raise


def guardar_bytes_imagen(bytes_img: bytes, nombre_img: str, ruta: Path) -> Path:
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        ruta_archivo = ruta / f"{nombre_img}.jpg"

        with open(ruta_archivo, "wb") as f:
            f.write(bytes_img)

        if ruta_archivo.exists() and ruta_archivo.stat().st_size > 0:
            return ruta_archivo 
        else:
            raise ErrorImagen(
                nombre_img,
                "La imagen no ha podido ser guardada."
            )
    except Exception as e:
        raise ErrorImagen(nombre_img, str(e))

# ------------
# EJEMPLO
# ------------
MIN_WIDTH, MIN_HEIGHT = 400, 400
MAX_WIDTH, MAX_HEIGHT = 1200, 1200
CALIDAD_COMPRESION = 85 # De 0 a 100. 85 es un excelente balance.

def procesar_y_guardar_imagen(contenido_bytes, ruta_destino):
    """
    Recibe los bytes de la imagen, aplica las reglas y la guarda.
    Retorna True si fue exitoso, False si fue descartada.
    """
    try:
        # Cargamos la imagen en memoria
        imagen = Image.open(io.BytesIO(contenido_bytes))
        
        # Convertimos a RGB por si es un PNG con transparencia o formato raro
        if imagen.mode in ("RGBA", "P", "CMYK"):
            imagen = imagen.convert("RGB")
            
        ancho, alto = imagen.size

        if ancho < MIN_WIDTH or alto < MIN_HEIGHT:
            print(f"  -> Descartada: Muy pequeña ({ancho}x{alto})")
            return False

        imagen.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
        
        imagen.save(ruta_destino, format="JPEG", optimize=True, quality=CALIDAD_COMPRESION)
        return True
        
    except UnidentifiedImageError:
        print("  -> Descartada: El archivo no es una imagen válida.")
        return False
    except Exception as e:
        print(f"  -> Error procesando imagen: {e}")
        return False

def descargar_con_estandar(grupo_urls, ruta_destino):
    """
    Itera sobre el grupo de URLs buscando una imagen que cumpla el estándar.
    """
    for url in grupo_urls:
        try:
            print(f"Intentando: {url}")
            respuesta = requests.get(url, timeout=10)
            respuesta.raise_for_status()
            
            # En vez de guardar en disco inmediatamente, pasamos los bytes al procesador
            exito = procesar_y_guardar_imagen(respuesta.content, ruta_destino)
            
            if exito:
                print(f"¡Éxito! Imagen procesada y guardada en: {ruta_destino}")
                return True
            else:
                # Si falló la validación (ej. muy pequeña), intentamos con la siguiente
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"  -> Fallo de red. Intentando con la siguiente...")
            continue 

    print(f"Error crítico: Ninguna imagen del grupo cumplió los estándares.")
    return False
