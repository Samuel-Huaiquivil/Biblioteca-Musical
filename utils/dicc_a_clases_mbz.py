# utils/dicc_a_clases_mbz.py
# Convierte un RecordingMbz (ya validado) a los modelos del dominio.
# Equivalente a dicc_a_clases.py pero para MusicBrainz.

from datetime import date
from typing import List

from models.schemas import Album, Cancion, GrupoArtistas, Genero
from models.schemas_api import RecordingMbz, ReleaseMBZ, ArtistCreditMBZ


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mejor_release(recording: RecordingMbz) -> ReleaseMBZ | None:
    """Retorna el release oficial más antiguo, o el primero disponible."""
    oficiales = [r for r in recording.releases if r.status.lower() == "official"]
    candidatos = oficiales or recording.releases
    if not candidatos:
        return None
    return min(candidatos, key=lambda r: r.date or "9999")


def _parsear_fecha(fecha_str: str) -> date:
    """
    MusicBrainz puede retornar fechas en tres formatos:
    - YYYY           → completar como YYYY-01-01
    - YYYY-MM        → completar como YYYY-MM-01
    - YYYY-MM-DD     → usar directamente
    """
    if not fecha_str:
        return date(2000, 1, 1)
    partes = fecha_str.split("-")
    anio = int(partes[0]) if len(partes) > 0 else 2000
    mes  = int(partes[1]) if len(partes) > 1 else 1
    dia  = int(partes[2]) if len(partes) > 2 else 1
    return date(anio, mes, dia)


def _extraer_artistas(credits: List[ArtistCreditMBZ]) -> tuple[str, List[str], List[str]]:
    """
    Interpreta la lista artist-credit de MusicBrainz.

    La lista alterna entre objetos de artista y separadores (joinphrase).
    Ejemplos de joinphrase: ' feat. ', ' & ', ' / ', ', '

    Retorna: (principal, colaboradores, featurings)
    - principal: primer artista de la lista
    - colaboradores: artistas unidos por ' & ', ',' o ' / '
    - featurings: artistas unidos por ' feat. ' o ' ft. '
    """
    principal = ""
    colaboradores: List[str] = []
    featurings: List[str] = []

    artistas_con_join = [c for c in credits if c.artist is not None]

    for i, credit in enumerate(artistas_con_join):
        nombre = credit.name or (credit.artist.name if credit.artist else "")
        if not nombre:
            continue

        if i == 0:
            principal = nombre
            continue

        # Determinar rol por el joinphrase del crédito ANTERIOR
        join_anterior = artistas_con_join[i - 1].joinphrase.lower()
        if "feat" in join_anterior or "ft." in join_anterior:
            featurings.append(nombre)
        else:
            colaboradores.append(nombre)

    return principal, colaboradores, featurings


# ---------------------------------------------------------------------------
# Conversores públicos
# ---------------------------------------------------------------------------

def convertir_a_grupo_artistas_mbz(recording: RecordingMbz) -> GrupoArtistas:
    principal, colabs, feats = _extraer_artistas(recording.artist_credit)
    return GrupoArtistas(
        principal=principal or "Desconocido",
        codigo_itunes=0,           # MusicBrainz no tiene código iTunes
        colaboradores=colabs or None,
        feat=feats or None,
    )


def convertir_a_album_mbz(recording: RecordingMbz) -> Album:
    release = _mejor_release(recording)
    if not release:
        return Album()             # Valores por defecto del schema

    return Album(
        titulo=release.title,
        lanzamiento=_parsear_fecha(release.date),
        codigo_itunes=0,           # Sin código iTunes
        pistas_totales=release.track_count or 1,
        explicito=False,           # MusicBrainz no provee este dato
        codigo_mbz=release.id,
    )


def convertir_a_cancion_mbz(recording: RecordingMbz) -> Cancion:
    return Cancion(
        titulo=recording.title,
        num_pista=1,               # MusicBrainz requiere lookup adicional para el nro de pista
        explicito=False,
        codigo_itunes=0,
        codigo_mbz=recording.id,
    )


def convertir_a_genero_mbz() -> Genero:
    """
    MusicBrainz no incluye género en el endpoint /recording.
    Se retorna un género genérico; se puede enriquecer con /release-group.
    """
    return Genero(nombre="Desconocido")


def convertir_recording(recording: RecordingMbz) -> dict:
    """
    Punto de entrada principal.
    Convierte un RecordingMbz al mismo formato de diccionario
    que usa convertir_respuesta() de dicc_a_clases.py,
    para que el resto del pipeline sea idéntico.
    """
    return {
        "genero":   convertir_a_genero_mbz(),
        "artistas": convertir_a_grupo_artistas_mbz(recording),
        "album":    convertir_a_album_mbz(recording),
        "cancion":  convertir_a_cancion_mbz(recording),
    }
