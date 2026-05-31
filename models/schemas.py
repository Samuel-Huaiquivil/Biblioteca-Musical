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
    pistas_totales: int = Field(default=1)
    explicito: bool = Field(default=False)
    codigo_mbz: Optional[str] = Field(default=None)

class Cancion(BaseModel):
    titulo: str = Field(default="Canción Desconocida")
    num_pista: int = Field(default=1)
    explicito: bool = Field(default=False)
    codigo_itunes: int = Field(default=0)
    codigo_mbz: Optional[str] = Field(default=None) 

class Caratula(BaseModel):
    codigo_album: int
    url_caratula: str
    imagen: Optional[bytes]

# ---------------------------------------------------------------------------
# Modelo para inserción ID3 (archivo .mp3)
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
    cod_album: int
    imagen_bytes: bytes

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

# ---------------------------------------------------------------------------
# Modelo para insertar datos. Tiene una estructura definida
# ---------------------------------------------------------------------------

class Contenedor(BaseModel):
    "Clase Contenedor"
    genero: Genero
    artistas: GrupoArtistas
    album: Album
    cancion: Cancion
    album_revisado: bool = Field(default=False)
    cancion_estado: bool = Field(default=False)

# ---------------------------------------------------------------------------
# Clases de Salida para la Base de datos datos.
# ---------------------------------------------------------------------------

class SalidaArtista(BaseModel):
    id_local: int
    nombre: str
    codigo_itunes: Optional[int]
    codigo_mbz: Optional[str]

    def coincide_con(self, artista: Artista) -> bool:
        """
        Compara los datos locales con los de entrada.
        Prioriza código iTunes sobre nombre para evitar falsos positivos.
        """
        if self.codigo_itunes and artista.codigo_itunes:
            return self.codigo_itunes == artista.codigo_itunes
        if self.codigo_mbz and artista.codigo_mbz:
            return self.codigo_mbz == artista.codigo_mbz
        # Fallback: nombre
        return (
            self.nombre.lower() == artista.nombre.lower()
        )

class SalidaCancion(BaseModel):
    """Datos de una canción tal como están en la base de datos local."""
    id_local: int
    titulo: str
    codigo_itunes: int
    numero_pista: int
    codigo_mbz: Optional[str]

    def coincide_con(self, cancion: Cancion) -> bool:
        """
        Compara los datos locales con los de entrada.
        Prioriza código iTunes sobre nombre para evitar falsos positivos.
        """
        if self.codigo_itunes and cancion.codigo_itunes:
            return self.codigo_itunes == cancion.codigo_itunes
        if self.codigo_mbz and cancion.codigo_mbz:
            return self.codigo_mbz == cancion.codigo_mbz
        # Fallback: nombre
        return (
            self.titulo.lower() == cancion.titulo.lower() and
            self.numero_pista == cancion.num_pista
        )

class SalidaAlbum(BaseModel):
    id_local: int
    titulo: str
    codigo_itunes: int
    pistas_totales: int
    lanzamiento: date
    codigo_mbz: Optional[str]

    def coincide_con(self, album: Album) -> bool:
        """
        Compara los datos locales con los de entrada.
        Prioriza código iTunes sobre nombre para evitar falsos positivos.
        """
        if self.codigo_itunes and album.codigo_itunes:
            return self.codigo_itunes == album.codigo_itunes
        if self.codigo_mbz and album.codigo_mbz:
            return self.codigo_mbz == album.codigo_mbz
        # Fallback: nombre, pistas y lanzamiento
        return (
            self.titulo.lower() == album.titulo.lower() and
            self.pistas_totales == album.pistas_totales and
            self.lanzamiento == album.lanzamiento
        )

class SalidaCaratula(BaseModel):
    id_local: int
    id_album: int
    url_caratula: str
    imagen_bytes: Optional[bytes] = None

    def tiene_url(self) -> bool:
        return True if self.url_caratula is not None else False
    
    def tiene_imagen(self) -> bool:
        if isinstance(self.imagen_bytes, bytes) and not None:
            return True 
        else:
            return False
    