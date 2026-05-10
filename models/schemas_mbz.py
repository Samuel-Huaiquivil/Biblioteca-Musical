# models/schemas_mbz.py
# Modelos Pydantic para la respuesta de la MusicBrainz API.
# Endpoint usado: /ws/2/recording/?query=...&fmt=json
#
# Diferencias clave con iTunes:
# - MusicBrainz retorna un campo "score" (0-100) por resultado.
# - Los IDs son UUIDs (str), no enteros.
# - Los artistas vienen como lista de objetos, no como string plano.
# - El álbum se llama "release" y puede haber varios por recording.

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-modelos (partes de un resultado)
# ---------------------------------------------------------------------------

class ArtistaMbz(BaseModel):
    """Artista dentro de un artist-credit de MusicBrainz."""
    id: str = ""                    # UUID del artista
    name: str = ""                  # Nombre canónico
    sort_name: str = Field(default="", alias="sort-name")

    model_config = {"populate_by_name": True}


class ArtistCreditMbz(BaseModel):
    """
    Entrada en la lista artist-credit.
    Puede ser un artista o un separador de texto (ej: ' feat. ').
    """
    name: Optional[str] = None      # Nombre tal como aparece en el crédito
    artist: Optional[ArtistaMbz] = None
    joinphrase: str = ""            # Separador: ' feat. ', ' & ', ' / ', etc.


class ReleaseMbz(BaseModel):
    """Álbum (release) asociado a un recording."""
    id: str = ""                    # UUID del álbum
    title: str = ""
    date: str = ""                  # Formato: YYYY, YYYY-MM, YYYY-MM-DD
    country: str = ""
    status: str = ""                # 'Official', 'Bootleg', 'Promotion'
    track_count: int = Field(default=0, alias="track-count")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Modelo principal de un resultado (recording)
# ---------------------------------------------------------------------------

class RecordingMbz(BaseModel):
    """
    Un resultado individual de la búsqueda de recordings en MusicBrainz.
    El campo 'score' indica la relevancia (0-100) según MusicBrainz.
    """
    id: str = ""                            # UUID de la canción
    score: int = 0                          # Relevancia MusicBrainz (0-100)
    title: str = ""
    length: Optional[int] = None            # Duración en milisegundos
    artist_credit: List[ArtistCreditMbz] = Field(
        default_factory=list,
        alias="artist-credit"
    )
    releases: List[ReleaseMbz] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Modelo de la respuesta completa
# ---------------------------------------------------------------------------

class RespuestaMbz(BaseModel):
    """Respuesta completa del endpoint /ws/2/recording/"""
    count: int = 0                          # Total de resultados en MBZ
    offset: int = 0
    recordings: List[RecordingMbz] = Field(default_factory=list)
