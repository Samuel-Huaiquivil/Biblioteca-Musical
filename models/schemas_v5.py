# Schemas para la gestión local de datos.

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Modelos para inserción en la Base de Datos Local.
# ---------------------------------------------------------------------------


class Genero(BaseModel):
    nombre: str = ""
    descripcion: Optional[str] = None

    @field_validator('nombre', mode='before')
    @classmethod
    def normalizar_nombre(cls, v):
        if isinstance(v, str):
            return v.strip().title() 
        return v

class Artista(BaseModel):
    nombre: str = Field(..., min_length=1)
    codigo: Optional[str] = None


class GrupoArtistas(BaseModel):
    """
    Agrupa al artista principal con sus colaboradores y featurings.
    Es el modelo que se usa al insertar una canción completa.
    """
    principal: Artista
    colaboradores: Optional[List[str]] = Field(default=None)
    feat: Optional[List[str]] = Field(default=None)


class Album(BaseModel):
    titulo: str = Field(..., min_length=1)
    lanzamiento: date = Field(default=date(2000, 1, 1))
    pistas_totales: int = Field(default=1)
    codigo: Optional[str] = Field(default=None)


class Cancion(BaseModel):
    titulo: str = Field(..., min_length=1)
    num_pista: int = Field(default=1)
    codigo: Optional[str] = Field(default=None) 

    
class Caratula(BaseModel):
    codigo_album: int
    url_caratula: str
    imagen: Optional[bytes]

    def tiene_imagen(self):
        return True if self.imagen else False

class Codigo(BaseModel):
    "ID Local, ID API y un código externo"
    tabla_id: int
    api_id: int
    codigo_ext: str

class Ident(BaseModel):
    "Una API-Región y un ID local"
    api: str = Field(default="iTunes")
    region: str = Field(..., min_length=2, max_length=8)
    id: int


# ---------------------------------------------------------------------------
# Modelos para la inserción en la Base de Datos MBZ
# ---------------------------------------------------------------------------


class GrupoAlbumMBZ (BaseModel):
    codigo_mbz: str = ""
    nombre_grupo: str = ""
    tipo_grupo: str = ""

class AlbumMBZ (BaseModel):
    codigo_mbz: str = ""
    titulo_album: str = ""
    estatus: str = ""
    fecha: str = ""
    pistas: int = Field(default=0)

class ArtistaMBZ (BaseModel):
    codigo_mbz: str = ""
    nombre_artista: str = ""

class CancionMBZ (BaseModel):
    codigo_mbz: str = ""
    nombre_cancion: str = ""


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

class ContenedorMBZ(BaseModel):
    grupo: GrupoAlbumMBZ
    album: AlbumMBZ
    cancion: CancionMBZ
    artista: List[ArtistaMBZ] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Modelo para la Base de datos. Se utiliza para gestionar los datos de ingreso
# ---------------------------------------------------------------------------

class PaqueteDatos(BaseModel):
    "Contenedor para gestionar los datos."
    cancion: Cancion
    album: Album
    artistas: GrupoArtistas
    genero: Optional[Genero] = None

    def __str__(self) -> str:
        can = self.cancion.titulo
        art = self.artistas.principal
        alb = self.album.titulo
        (col, fea) = (None, None)
        if self.artistas.colaboradores:
            col = ",".join(c for c in self.artistas.colaboradores)
        if self.artistas.feat:
            fea = ",".join(f for f in self.artistas.feat)
        return f"PCK-Class [{art.nombre} - {can} | {alb}] *** {col} +++ {fea} ***"


# ---------------------------------------------------------------------------
# Clases de Salida para la Base de datos datos.
# ---------------------------------------------------------------------------

class SalidaArtista(BaseModel):
    id_local: int
    nombre: str
    codigos: Optional[List[str]] = None

    def coincide_con(self, artista: Artista) -> bool:
        "Compara datos con la clase"
        if self.codigos:
            for c in self.codigos:
                if c == artista.codigo:
                    return True
                else:
                    pass
            return False
        else:
            return self.nombre.lower() == artista.nombre.lower()


class SalidaCancion(BaseModel):
    """Datos de una canción tal como están en la base de datos local."""
    id_local: int
    titulo: str
    album_id: int
    numero_cancion: int
    codigos: Optional[List[str]] = None

    def coincide_con(self, cancion: Cancion) -> bool:
        """
        Compara los datos locales con los de entrada.
        Prioriza código iTunes sobre nombre para evitar falsos positivos.
        """
        if self.codigos:
            for c in self.codigos:
                if c == cancion.codigo:
                    return True
                else:
                    pass
            return False
        # Fallback: nombre
        else:
            return (self.titulo.lower() == cancion.titulo.lower())

    def __str__(self) -> str:
        return f"Cancion[ID:{self.id_local} - {self.titulo} || N°{self.numero_cancion} en album {self.album_id}]"

class SalidaAlbum(BaseModel):
    '''
    Clase para gestionar los datos de un álbum tal como están en la base de datos local.

    Attributes:
        id_local (int): ID local del álbum en la base de datos.
        titulo (str): Título del álbum.
        pistas_totales (int): Número total de pistas en el álbum.
        lanzamiento (date): Fecha de lanzamiento del álbum.
        codigos (Optional[List[str]]): Lista de códigos asociados al álbum (opcional).
    '''
    id_local: int
    titulo: str
    pistas_totales: int
    lanzamiento: date
    codigos: Optional[List[str]] = None

    def coincide_con(self, album: Album) -> bool:
        """
        Compara los datos locales con un álbum de entrada.
        Prioriza los códigos sobre el nombre para evitar falsos positivos.
        """
        if self.codigos:
            for c in self.codigos:
                if c == album.codigo:
                    return True
                else:
                    pass
            return False
        # Fallback: nombre, pistas y año lanzamiento
        return (
            self.titulo.lower() == album.titulo.lower() and
            self.pistas_totales == album.pistas_totales and
            self.lanzamiento.year == album.lanzamiento.year
        )

    def __str__(self) -> str:
        return f"Album[ID:{self.id_local} - {self.titulo} : N°{self.pistas_totales} canciones || {date.isoformat(self.lanzamiento)}]"

class SalidaCaratula(BaseModel):
    id_local: int
    id_album: int
    url_caratula: str
    imagen_bytes: Optional[bytes] = None

    def tiene_imagen(self) -> bool:
        if isinstance(self.imagen_bytes, bytes) and not None:
            return True 
        else:
            return False
    