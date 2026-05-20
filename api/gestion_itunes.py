# api/gestion_itunes.py
# Búsqueda avanzada y progresiva en iTunes.
# Cada nivel añade más contexto sobre el artista y su discografía.
#
# Nivel 1 → Solo la canción buscada (mínimo)
# Nivel 2 → Canción + álbum completo donde aparece
# Nivel 3 → Nivel 2 + 1 álbum adicional del artista con sus canciones
# Nivel 4 → Nivel 2 + 3 álbumes adicionales con sus canciones
# Nivel 5 → Nivel 4 + búsqueda en regiones alternativas

from typing import Any
from api.itunes import buscar_cancion_itunes, buscar_canciones_album, buscar_albumes_artista
from utils.errores import ErrorAPI

# ---------------------------------------------------------------------------
# Configuración
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

# Cuántos álbumes adicionales pedir por nivel (además del álbum de la canción)
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
    Separa los datos por origen para que el ponderador pueda trabajar mejor.
    """
    def __init__(self):
        self.cancion_principal: list[dict] = []   # resultados de la canción buscada
        self.album_principal:   list[dict] = []   # tracklist del álbum de la canción
        self.albumes_artista:   list[dict] = []   # otros álbumes del artista
        self.canciones_extra:   list[dict] = []   # canciones de esos álbumes extra
        self.regiones_extra:    list[dict] = []   # resultados de otras regiones (nivel 5)

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
    Es el id que se usa para buscar el tracklist completo del álbum.
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
        except ErrorAPI:
            pass  # Si un álbum falla, seguimos con los demás
    return canciones


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def busqueda_itunes_por_nivel(
    nombre_artista: str,
    titulo_cancion: str,
    nivel: int = 2,
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
    # Paso 1 — Buscar la canción (todos los niveles)
    # ------------------------------------------------------------------
    resultado.cancion_principal = buscar_cancion_itunes(
        titulo=titulo_cancion,
        artista=nombre_artista,
        limite=10,   # siempre pedimos varios para tener más opciones al ponderar
    )

    if nivel == 1:
        return resultado

    # ------------------------------------------------------------------
    # Paso 2 — Buscar el álbum completo donde aparece la canción (niveles 2-5)
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
        limite=cantidad_albumes + 2,  # pedimos un par extra por si alguno falla
    )

    # Excluir el álbum principal para no duplicar canciones
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
            continue  # no repetir la región principal
        try:
            resultados_region = buscar_cancion_itunes(
                titulo=titulo_cancion,
                artista=nombre_artista,
                limite=5,
            )
            resultado.regiones_extra.extend(resultados_region)
        except ErrorAPI:
            pass  # si una región falla, seguimos con las demás

    return resultado