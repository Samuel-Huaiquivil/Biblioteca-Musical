from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class Genero(BaseModel):
    nombre: str = Field(default="Desconocido")

class Artista(BaseModel):
    """Entidad individual de artista, tal como viene de iTunes."""
    nombre: str = Field(default="Artista Desconocido")
    codigo_itunes: int = Field(default=0)
    codigo_mbz: Optional[str] = Field(default=None)

class GrupoArtistas(BaseModel):
    """
    Agrupa al artista principal con sus colaboradores y featurings.
    Es el modelo que se usa al insertar una canción completa.
    """
    principal: str = Field(default="Artista Desconocido")
    codigo_itunes: int = Field(default=0)
    colaboradores: Optional[List[str]] = Field(default=None)
    feat: Optional[List[str]] = Field(default=None)

class Album(BaseModel):
    titulo: str = Field(default="Álbum Desconocido")
    lanzamiento: date = Field(default=date(2000, 1, 1))
    codigo_itunes: int = Field(default=0)
    num_pistas: int = Field(default=1)
    explicito: bool = Field(default=False)
    codigo_mbz: Optional[str] = Field(default=None)

class Cancion(BaseModel):
    titulo: str = Field(default="Canción Desconocida")
    num_pista: int = Field(default=1)
    explicito: bool = Field(default=False)
    codigo_itunes: int = Field(default=0)
    codigo_mbz: Optional[str] = Field(default=None) 


# ---------------------------------------------------------------------------
# Modelo para inserción ID3 (lo que va al archivo .mp3)
# ---------------------------------------------------------------------------

class DatosMusica(BaseModel):
    """Datos listos para escribir como tags ID3 en el archivo de audio."""
    titulo: str = Field(default="Título Desconocido")
    album: str = Field(default="Álbum Desconocido")
    artista_principal: str = Field(default="Artista Desconocido")
    artistas_colab: List[str] = Field(default_factory=list)
    anio: int = Field(default=2000)
    num_pista: int = Field(default=1)
    genero: str = Field(default="Desconocido")
    subtitulo: Optional[str] = Field(default=None)

class DatosCaratula(BaseModel):
    """Bytes de la carátula asociada a un álbum."""
    codigo_album: int
    imagen: bytes

# ---------------------------------------------------------------------------
# Modelo de validación de respuesta iTunes
# Úsalo con RespuestaItunes(**diccionario) para validar la API.
# ---------------------------------------------------------------------------

class RespuestaItunes(BaseModel):
    """
    Representa un ítem de respuesta de la iTunes Search API.
    Los campos opcionales existen solo en algunos tipos de respuesta
    (por ejemplo, collectionArtistName solo aparece en compilaciones).
    """
    # Obligatorios
    artistId: int
    collectionId: int
    trackId: int
    artistName: str
    collectionName: str
    trackName: str
    primaryGenreName: str
    releaseDate: str
    trackCount: int
    trackNumber: int
    collectionExplicitness: str
    trackExplicitness: str
    artworkUrl100: str

    # Opcionales (compilaciones / varios artistas)
    collectionArtistName: str = ""
    collectionArtistId: int = 0

    # Opcionales (miniaturas adicionales)
    artworkUrl60: str = ""
    artworkUrl30: str = ""

    # Opcionales varios
    discCount: int = 1
    discNumber: int = 1
    trackTimeMillis: int = 0
    isStreamable: bool = False
