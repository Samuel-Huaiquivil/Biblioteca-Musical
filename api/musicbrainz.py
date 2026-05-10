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
from pydantic import ValidationError

from models.schemas_mbz import RespuestaMbz, RecordingMbz
from utils.errores import ErrorAPI

_URL_BASE  = "https://musicbrainz.org/ws/2"
_TIMEOUT   = 10
_INTERVALO = 1.1   # segundos entre peticiones (respeta el rate limit)

# MusicBrainz exige un User-Agent descriptivo. Cámbialo por tus datos.
_HEADERS = {
    "User-Agent": "ScriptBibliotecaMusical/2.3 (raula9396@gmail.com)"
}

_ultimo_request: float = 0.0


def _get(endpoint: str, params: dict) -> dict:
    """
    Petición GET con rate limiting automático y manejo de errores.
    """
    global _ultimo_request

    # Respetar el rate limit sin bloquear más de lo necesario
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
        raise ErrorAPI("MusicBrainz", "La petición superó el tiempo límite.")
    except requests.exceptions.ConnectionError:
        raise ErrorAPI("MusicBrainz", "No se pudo conectar. Verifica tu conexión.")
    except requests.exceptions.HTTPError as e:
        raise ErrorAPI("MusicBrainz", f"Error HTTP {e.response.status_code}.")
    except Exception as e:
        raise ErrorAPI("MusicBrainz", str(e))


# ---------------------------------------------------------------------------
# Búsqueda principal
# ---------------------------------------------------------------------------

def buscar_cancion_mbz(titulo: str, artista: str, limite: int = 5) -> list[RecordingMbz]:
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

    try:
        respuesta = RespuestaMbz(**data)
    except ValidationError as e:
        raise ErrorAPI("MusicBrainz", f"Respuesta inesperada: {e}") from e

    # Ordenar por score descendente (MusicBrainz ya los envía ordenados,
    # pero lo hacemos explícito por claridad)
    return sorted(respuesta.recordings, key=lambda r: r.score, reverse=True)


# ---------------------------------------------------------------------------
# Selección del mejor resultado
# ---------------------------------------------------------------------------

def obtener_mejor_recording(recordings: list[RecordingMbz]) -> RecordingMbz | None:
    """
    Selecciona el recording más adecuado de la lista.

    Criterios adicionales al score de MusicBrainz:
    - Prefiere releases con status 'Official' sobre Bootleg/Promotion.
    - Penaliza recordings sin releases asociados.
    - En empate, prefiere el release con fecha más antigua (original).
    """
    if not recordings:
        return None

    def puntaje(rec: RecordingMbz) -> float:
        puntos = float(rec.score)

        releases_oficiales = [
            r for r in rec.releases if r.status.lower() == "official"
        ]

        if not rec.releases:
            puntos -= 20        # Sin álbum asociado es sospechoso
        elif releases_oficiales:
            puntos += 10        # Tiene al menos un release oficial

            # Bonus por release más antiguo (versión original)
            fechas = [r.date for r in releases_oficiales if r.date]
            if fechas:
                fecha_min = min(fechas)
                if len(fecha_min) >= 4:  # al menos tiene el año
                    anio = int(fecha_min[:4])
                    # Pequeño bonus inversamente proporcional al año
                    puntos += max(0, (2000 - anio) * 0.1)

        return puntos

    return max(recordings, key=puntaje)
