# api/itunes.py
# Todas las consultas a la iTunes Search API en un solo módulo.
# Referencia: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/

import requests
from typing import Any

from utils.errores import ErrorItunes

# Configuración global
_URL_SEARCH = "https://itunes.apple.com/search"
_URL_LOOKUP = "https://itunes.apple.com/lookup"
_PAIS       = "us"
_TIMEOUT    = 10


# ---------------------------------------------------------------------------
# Función base — todas las peticiones pasan por aquí
# ---------------------------------------------------------------------------

def _get(url: str, params: dict) -> dict[str, Any]:
    """
    Centraliza el manejo de errores de red.
    """
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise ErrorItunes("La petición superó el tiempo límite.")
    except requests.exceptions.ConnectionError:
        raise ErrorItunes("No se pudo conectar. Verificar la conexión.")
    except requests.exceptions.HTTPError as e:
        raise ErrorItunes(f"Error HTTP ", f"{e.response.status_code}.")
    except Exception as e:
        raise ErrorItunes("Error no Registrado.", str(e))


# ---------------------------------------------------------------------------
# Búsqueda de canción — función principal del pipeline
# ---------------------------------------------------------------------------

def buscar_cancion_itunes(titulo: str, artista: str, limite: int = 5, region: str = _PAIS) -> list[dict]:
    """
    Busca una canción por título y artista en iTunes.
    Retorna solo los resultados que cumplen las propiedades mínimas

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
        "country": region,
    })

    resultados = data.get("results", [])
    # Filtrar solo canciones válidas antes de retornar
    return [r for r in resultados]


# ---------------------------------------------------------------------------
# Búsqueda de álbumes de un artista
# ---------------------------------------------------------------------------

def buscar_albumes_artista(nombre_artista: str, limite: int = 5, region: str = _PAIS) -> list[dict]:
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
        "country": region,
    })

    return data.get("results", [])


# ---------------------------------------------------------------------------
# Búsqueda de canciones por ID de álbum (iTunes lookup)
# ---------------------------------------------------------------------------

def buscar_canciones_album(id_album: int, region: str = _PAIS) -> list[dict]:
    """
    Retorna las canciones de un álbum dado su código iTunes.
    Usa el endpoint /lookup que es más preciso que /search.
    """
    if not id_album:
        raise ValueError("El id_album no puede ser 0 o vacío.")

    data = _get(_URL_LOOKUP, params={
        "id": id_album,
        "entity": "song",
        "country": region,
    })

    resultados = data.get("results", [])
    return [r for r in resultados if r.get("wrapperType") == "track"]


def descargar_caratula_itunes(url_descarga: str) -> bytes:
    if not url_descarga:
        raise ErrorItunes("La url no es válida.", "No se pudo descargar la imagen pues la url no es válida.")
    try:
        resp = requests.get(url_descarga, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        raise ErrorItunes("Error al descargar carátula", str(e))


# ---------------------------------------------------------------------------
# Configuración Versión Búsqueda Ampliada
# ---------------------------------------------------------------------------

REGIONES: dict[str, str] = {
    "Estados Unidos": "us",
    "España":         "es",
    "Chile":          "cl",
    "México":         "mx",
    "Argentina":      "ar",
    "Uruguay":        "uy",
    "Brasil":         "br",
    "Reino Unido":    "gb",
    "Francia":        "fr",
}

_ALBUMES_POR_NIVEL: dict[int, int] = {
    1: 0,
    2: 0,
    3: 1,
    4: 3,
    5: 5,
}

# Regiones alternativas que se consultan en nivel 5
_REGIONES_EXTRA_NIVEL_5 = ["es", "gb", "mx"]


# ---------------------------------------------------------------------------
# Tipo de retorno
# ---------------------------------------------------------------------------


class ResultadoBusqueda:
    """
    Contenedor del resultado de una búsqueda por niveles.
    """
    def __init__(self):
        self.cancion_principal: list[dict] = []
        self.album_principal:   list[dict] = []
        self.albumes_artista:   list[dict] = []
        self.canciones_extra:   list[dict] = []
        self.regiones_extra:    list[dict] = []

    def todas_las_canciones(self) -> list[dict]:
        """Retorna todas las canciones encontradas en una sola lista plana."""
        return (
            self.cancion_principal +
            self.album_principal   +
            self.canciones_extra   +
            self.regiones_extra
        )

    def resumen(self) -> str:
        return (
            f"Canción principal: {len(self.cancion_principal)} resultado(s)\n"
            f"Álbum principal:   {len(self.album_principal)} pista(s)\n"
            f"Álbumes extra:     {len(self.albumes_artista)} álbum(es)\n"
            f"Canciones extra:   {len(self.canciones_extra)} pista(s)\n"
            f"Regiones extra:    {len(self.regiones_extra)} resultado(s)"
        )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _extraer_id_album(resultados_cancion: list[dict]) -> int | None:
    """
    Extrae el collectionId del primer resultado con datos de álbum.
    """
    for resultado in resultados_cancion:
        id_album = resultado.get("collectionId")
        if id_album:
            return id_album
    return None


def _buscar_canciones_de_albumes(albumes: list[dict]) -> list[dict]:
    """
    Dado una lista de álbumes, retorna todas sus canciones combinadas.
    Ignora álbumes sin collectionId válido.
    """
    canciones: list[dict] = []
    for album in albumes:
        id_album = album.get("collectionId")
        if not id_album:
            continue
        try:
            pistas = buscar_canciones_album(id_album)
            canciones.extend(pistas)
        except ErrorItunes:
            pass
    return canciones


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def busqueda_itunes_por_nivel(
    nombre_artista: str,
    titulo_cancion: str,
    nivel: int = 1,
    region: str = "Estados Unidos",
) -> ResultadoBusqueda:
    """
    Realiza una búsqueda progresiva en iTunes según el nivel de profundidad.

    Parámetros:
    - nombre_artista: artista de la canción.
    - titulo_cancion: título de la canción.
    - nivel: profundidad de búsqueda (1-5).
    - region: región principal de búsqueda (clave de REGIONES).

    Retorna un ResultadoBusqueda con los datos organizados por origen.
    """
    if nivel not in _ALBUMES_POR_NIVEL:
        raise ValueError(f"Nivel inválido: {nivel}. Debe ser entre 1 y 5.")
    if region not in REGIONES:
        raise ValueError(f"Región desconocida: '{region}'. Opciones: {list(REGIONES)}")

    codigo_region = REGIONES[region]
    resultado = ResultadoBusqueda()

    # ------------------------------------------------------------------
    # Paso 1 — Buscar la canción
    # ------------------------------------------------------------------
    resultado.cancion_principal = buscar_cancion_itunes(
        titulo=titulo_cancion,
        artista=nombre_artista,
        limite=7
    )

    if nivel == 1:
        return resultado

    # ------------------------------------------------------------------
    # Paso 2 — Buscar el álbum completo donde aparece la canción (niveles > 1)
    # ------------------------------------------------------------------
    id_album = _extraer_id_album(resultado.cancion_principal)
    if id_album:
        resultado.album_principal = buscar_canciones_album(id_album)

    if nivel == 2:
        return resultado

    # ------------------------------------------------------------------
    # Paso 3 — Buscar álbumes adicionales del artista (niveles 3-5)
    # ------------------------------------------------------------------
    cantidad_albumes = _ALBUMES_POR_NIVEL[nivel]
    albumes_artista = buscar_albumes_artista(
        nombre_artista=nombre_artista,
        limite=cantidad_albumes + 2,
    )

    # Excluir el álbum principal
    albumes_extra = [
        a for a in albumes_artista
        if a.get("collectionId") != id_album
    ][:cantidad_albumes]

    resultado.albumes_artista = albumes_extra
    resultado.canciones_extra = _buscar_canciones_de_albumes(albumes_extra)

    if nivel < 5:
        return resultado

    # ------------------------------------------------------------------
    # Paso 4 — Buscar en regiones alternativas (solo nivel 5)
    # ------------------------------------------------------------------
    for codigo_extra in _REGIONES_EXTRA_NIVEL_5:
        if codigo_extra == codigo_region:
            continue
        try:
            resultados_region = buscar_cancion_itunes(
                titulo=titulo_cancion,
                artista=nombre_artista,
                limite=3,
            )
            resultado.regiones_extra.extend(resultados_region)
        except ErrorItunes:
            pass

    return resultado