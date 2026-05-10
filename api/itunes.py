# api/itunes.py
# Todas las consultas a la iTunes Search API en un solo módulo.
# Referencia: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/

import requests
from typing import Any

from models.schemas import RespuestaItunes
from utils.errores import ErrorAPI
from utils.poderador import propiedades_minimas

# Configuración global
_URL_SEARCH = "https://itunes.apple.com/search"
_URL_LOOKUP = "https://itunes.apple.com/lookup"
_PAIS       = "us"   # "us" da más resultados que "es"
_TIMEOUT    = 10     # segundos antes de abortar la petición


# ---------------------------------------------------------------------------
# Función base — todas las peticiones pasan por aquí
# ---------------------------------------------------------------------------

def _get(url: str, params: dict) -> dict[str, Any]:
    """
    Realiza una petición GET a iTunes y retorna el JSON.
    Centraliza el manejo de errores de red.
    """
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ErrorAPI("iTunes", "La petición superó el tiempo límite.")
    except requests.exceptions.ConnectionError:
        raise ErrorAPI("iTunes", "No se pudo conectar. Verifica tu conexión.")
    except requests.exceptions.HTTPError as e:
        raise ErrorAPI("iTunes", f"Error HTTP {e.response.status_code}.")
    except Exception as e:
        raise ErrorAPI("iTunes", str(e))


# ---------------------------------------------------------------------------
# Búsqueda de canción — función principal del pipeline
# ---------------------------------------------------------------------------

def buscar_cancion_itunes(titulo: str, artista: str, limite: int = 10) -> list[dict]:
    """
    Busca una canción por título y artista en iTunes.
    Retorna solo los resultados que cumplen las propiedades mínimas
    (wrapperType='track', kind='song', con IDs válidos).

    - limite: cuántos resultados pedir a iTunes. Más resultados dan más
      opciones al ponderador para elegir el mejor. Default 10.
    """
    if not titulo or not artista:
        raise ValueError("Título y artista son obligatorios para buscar en iTunes.")

    data = _get(_URL_SEARCH, params={
        "term": f"{titulo} {artista}",
        "media": "music",
        "entity": "song",
        "limit": limite,
        "country": _PAIS,
    })

    resultados = data.get("results", [])
    # Filtrar solo canciones válidas antes de retornar
    return [r for r in resultados if propiedades_minimas(r)]


# ---------------------------------------------------------------------------
# Búsqueda de álbumes de un artista
# ---------------------------------------------------------------------------

def buscar_albumes_artista(nombre_artista: str, limite: int = 5) -> list[dict]:
    """
    Retorna álbumes del artista indicado.
    Útil para poblar la base de datos con discografía completa.
    """
    if not nombre_artista:
        raise ValueError("El nombre del artista no puede estar vacío.")

    data = _get(_URL_SEARCH, params={
        "term": nombre_artista,
        "entity": "album",
        "limit": limite,
        "country": _PAIS,
    })

    return data.get("results", [])


# ---------------------------------------------------------------------------
# Búsqueda de canciones por ID de álbum (iTunes lookup)
# ---------------------------------------------------------------------------

def buscar_canciones_album(id_album: int) -> list[dict]:
    """
    Retorna las canciones de un álbum dado su código iTunes.
    Usa el endpoint /lookup que es más preciso que /search.
    """
    if not id_album:
        raise ValueError("El id_album no puede ser 0 o vacío.")

    data = _get(_URL_LOOKUP, params={
        "id": id_album,
        "entity": "song",
        "country": _PAIS,
    })

    resultados = data.get("results", [])
    # El primer resultado es el álbum, el resto son las canciones
    return [r for r in resultados if r.get("wrapperType") == "track"]


# ---------------------------------------------------------------------------
# Validar y convertir resultado individual
# ---------------------------------------------------------------------------

def validar_resultado(dicc: dict) -> RespuestaItunes:
    """
    Convierte un diccionario crudo de iTunes a RespuestaItunes (Pydantic).
    Lanza ValueError si el formato no es válido.
    """
    from pydantic import ValidationError
    try:
        return RespuestaItunes(**dicc)
    except ValidationError as e:
        raise ValueError(f"Resultado iTunes inválido: {e}") from e
