from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

# ---------------------------------------------------------------------------
# Sub-modelos (partes de un resultado de MusicBrainz)
# ---------------------------------------------------------------------------


class ArtistMBZ(BaseModel):
    """Artista dentro de un artist-credit de MusicBrainz."""
    id: str
    name: str
    sort_name: str = Field(default="", alias="sort-name")

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class ArtistCreditMBZ(BaseModel):
    """
    Entrada en la lista artist-credit.
    Puede ser un artista o un separador de texto (ej: ' feat. ').
    """
    name: Optional[str] = None      # Nombre tal como aparece en el crédito
    artist: Optional[ArtistMBZ] = None
    joinphrase: str = ""


class ReleaseGroupMBZ(BaseModel):
    id: str = ""
    title: str = ""
    primary_type: Optional[str] = Field(alias="primary-type", default=None)

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class MediaMBZ(BaseModel):
    id: str = ""
    position: int = 0
    format: str = ""
    track_count: int = Field(alias="track-count", default=0)
    track_offset: int = Field(alias="track-offset", default=0)

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class ReleaseMBZ(BaseModel):
    """Álbum (release) asociado a un recording."""
    id: str = ""
    title: str = ""
    date: str = ""
    country: str = ""
    status: str = ""
    disambiguation: Optional[str] = None
    artist_credit: List[ArtistCreditMBZ] = Field(
        default_factory=list,
        alias="artist-credit"
    )
    track_count: int = Field(default=0, alias="track-count")
    release_group: Optional[ReleaseGroupMBZ] = Field(default=None, alias="release-group")
    media: List[MediaMBZ] = Field(default_factory=list)
    
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    def __str__(self):
        return f"Release[{self.title} - {self.id}]"


# ---------------------------------------------------------------------------
# Modelo principal de un resultado de MusicBrainz (recording)
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
    disambiguation: Optional[str] = None
    artist_credit: List[ArtistCreditMBZ] = Field(
        default_factory=list,
        alias="artist-credit"
    )
    releases: List[ReleaseMBZ] = Field(default_factory=list)

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    def to_dict(self):
        return {
            "id": self.id,
            "score": self.score,
            "title": self.title,
            "length": self.length or 0,
            "artist_credit": self.artist_credit,
            "releases": self.releases
        }

    def __str__(self):
        rel_str = ";".join(str(r) for r in self.releases)
        return f"Recording[{self.title} - {self.id}] ** [Rel {rel_str}]"

    