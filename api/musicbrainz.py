# api/musicbrainz.py
# Consultas a la MusicBrainz API.
# Docs: https://musicbrainz.org/doc/MusicBrainz_API
#
# Reglas importantes de la API:
# - User-Agent obligatorio (nombre app, versión, contacto).
# - Rate limit: 1 petición/segundo. Sin autenticación.
# - Formato JSON con &fmt=json.

import time
import requests
from typing import Any, Dict

from utils.errores import ErrorMusicBrainz
from config.setup import CORREO_PERSONAL

_URL_BASE  = "https://musicbrainz.org/ws/2"
_TIMEOUT   = 10
_INTERVALO = 1.1

_HEADERS = {
    "User-Agent": f"ScriptBibliotecaMusical/2.5 ({CORREO_PERSONAL})"
}

_ultimo_request: float = 0.0


def _get(endpoint: str, params: dict) -> dict:
    """
    Petición GET con rate limiting automático y manejo de errores.
    """
    global _ultimo_request

    espera = _INTERVALO - (time.monotonic() - _ultimo_request)
    if espera > 0:
        time.sleep(espera)

    try:
        response = requests.get(
            f"{_URL_BASE}/{endpoint}",
            params={**params, "fmt": "json"},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        _ultimo_request = time.monotonic()
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ErrorMusicBrainz("La petición superó el tiempo límite.")
    except requests.exceptions.ConnectionError:
        raise ErrorMusicBrainz("No se pudo conectar. Verificar la conexión.")
    except requests.exceptions.HTTPError as e:
        raise ErrorMusicBrainz(f"Error HTTP", f"{e.response.status_code}.")
    except Exception as e:
        raise ErrorMusicBrainz("Error no Registrado.", str(e))


# ---------------------------------------------------------------------------
# Búsqueda principal
# ---------------------------------------------------------------------------

def buscar_cancion_mbz(titulo: str, artista: str, limite: int = 5) -> list[Any]:
    """
    Busca una canción en MusicBrainz por título y artista.
    Retorna los recordings ordenados por score descendente.

    MusicBrainz usa Lucene para las queries:
    - title:"Nombre Cancion" AND artist:"Nombre Artista"
    """
    if not titulo or not artista:
        raise ValueError("Título y artista son obligatorios.")

    query = f'title:"{titulo}" AND artist:"{artista}"'
    data = _get("recording/", {"query": query, "limit": limite})

    return data["recordings"]


def buscar_albumes_artistas_mbz(id_artista: str, limite: int = 10):
    if not id_artista:
        raise ValueError("ID Artista es obligatorio")
    
    query = f"?artist={id_artista}&type=album"
    resp = _get("release-group", {"query": query, "limit": limite})
    return resp


def buscar_cancion_mbz_oficial(titulo: str, artista: str, limite: int = 5) -> Dict:
    if not titulo or not artista:
        raise ValueError("Título y artista son obligatorios.")

    query=f'recording:"{titulo}" AND artist:"{artista}" AND status:official AND primarytype:album'

    data = _get("recording/", {"query": query, "limit": limite})
    return data


