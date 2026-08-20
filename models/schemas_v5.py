# Schemas para la gestión local de datos.
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Modelos para inserción en la Base de Datos Local.
# ---------------------------------------------------------------------------


class Genero(BaseModel):
    """Representa un género musical registrado localmente.

    Attributes:
        nombre (str): Nombre del género, normalizado al formato de título.
        descripcion (Optional[str]): Descripción opcional del género.
    """
    nombre: str = ""
    descripcion: Optional[str] = None

    @field_validator('nombre', mode='before')
    @classmethod
    def normalizar_nombre(cls, v):
        """Normaliza el nombre del género para evitar espacios y mayúsculas inconsistentes."""
        if isinstance(v, str):
            return v.strip().title()
        return v


class Artista(BaseModel):
    """Representa un artista o intérprete musical.

    Attributes:
        nombre (str): Nombre del artista.
        codigo (Optional[str]): Código externo opcional.
    """
    nombre: str = Field(..., min_length=1)
    codigo: Optional[str] = None

    def __str__(self) -> str:
        """Devuelve una representación legible del artista para logs o depuración."""
        res = f"{self.nombre}"
        if self.codigo:
            res = f"{res} - Cod: {self.codigo}"
        else:
            res = f"{res} - S.C."
        return f"Artista[{res}]"


class GrupoArtistas(BaseModel):
    """Agrupa a un artista principal con sus colaboradores y featurings.

    Attributes:
        principal (Artista): Artista principal del grupo.
        colaboradores (Optional[List[Artista]]): Colaboradores del artista.
        feat (Optional[List[Artista]]): Featurings o artistas invitados.
    """
    principal: Artista
    colaboradores: Optional[List[Artista]] = Field(default_factory=list)
    feat: Optional[List[Artista]] = Field(default_factory=list)

    def __str__(self) -> str:
        """Compone una cadena resumida con el artista principal y sus colaboradores."""
        col = ""
        ft = ""
        if self.colaboradores:
            col = ", ".join(c.nombre for c in self.colaboradores)
        if self.feat:
            ft = ", ".join(f.nombre for f in self.feat)
        txt = f"{self.principal.nombre}"
        if col:
            txt += f" & {col}"
        if ft:
            txt += f"ft. ({ft})"
        txt += "."
        return txt


class Album(BaseModel):
    """Representa un álbum musical.

    Attributes:
        titulo (str): Título del álbum.
        lanzamiento (date): Fecha de lanzamiento del álbum.
        pistas_totales (int): Número total de pistas del álbum.
        codigo (Optional[str]): Código externo
    """
    titulo: str = Field(..., min_length=1)
    lanzamiento: date = Field(default=date(2000, 1, 1))
    pistas_totales: int = Field(default=1)
    codigo: Optional[str] = Field(default=None)
    url_descarga: Optional[str] = Field(default=None)

    def __str__(self) -> str:
        """Devuelve una representación textual del álbum con fecha y cantidad de pistas."""
        f = date.isoformat(self.lanzamiento)
        return f"Album[{self.titulo} ({self.pistas_totales}) {f} | id: {self.codigo}]"


class Cancion(BaseModel):
    """Representa una canción contenida en un álbum.

    Attributes:
        titulo (str): Título de la canción.
        num_pista (int): Número de pista dentro del álbum.
        codigo (Optional[str]): Código externo de la canción.
    """

    titulo: str = Field(..., min_length=1)
    num_pista: int = Field(default=1)
    codigo: Optional[str] = Field(default=None) 

    def __str__(self) -> str:
        """Representa la canción de forma breve y útil para depuración."""
        return f"Cancion[{self.titulo} ({self.num_pista}) | id: {self.codigo}]"


class Caratula(BaseModel):
    """Representa la portada asociada a un álbum.

    Attributes:
        codigo_album (int): Identificador del álbum al que pertenece.
        url_caratula (str): URL de la carátula.
        imagen (Optional[bytes]): Datos binarios de la imagen.
    """
    codigo_album: int
    url_caratula: str
    imagen: Optional[bytes]

    def tiene_imagen(self) -> bool:
        """Indica si la carátula contiene datos binarios de imagen."""
        return isinstance(self.imagen, bytes) and bool(self.imagen)


class Codigo(BaseModel):
    """Guarda los identificadores locales y externos de un registro.

    Attributes:
        tabla_id (int): Identificador local en la tabla.
        api_id (int): Identificador en la API externa.
        codigo_ext (str): Código externo asociado al registro.
    """
    tabla_id: int
    api_id: int
    codigo_ext: str


class Ident(BaseModel):
    """Representa una referencia de un recurso por API y región.

    Attributes:
        api (str): Nombre de la API de origen.
        region (str): Región o país asociado.
        id (int): Identificador del recurso.
    """
    api: str = Field(default="iTunes")
    region: str = Field(..., min_length=2, max_length=8)
    id: int


# ---------------------------------------------------------------------------
# Modelo para inserción ID3 (archivo .mp3)
# ---------------------------------------------------------------------------


class DatosMusica(BaseModel):
    """Datos listos para escribir como etiquetas ID3 en un archivo.

    Attributes:
        titulo (str): Título de la canción.
        album (str): Nombre del álbum.
        artista_principal (str): Artista principal.
        artistas_colab (List[str]): Lista de artistas colaboradores.
        anio (int): Año de publicación.
        num_pista (int): Número de pista.
        genero (str): Género musical.
        subtitulo (Optional[str]): Subtítulo opcional.
    """
    titulo: str
    album: str 
    artista_principal: str 
    artistas_colab: List[str] = Field(default_factory=list)
    anio: int 
    num_pista: int 
    genero: str 
    subtitulo: Optional[str] = Field(default=None)


class DatosCaratula(BaseModel):
    """Bytes de la carátula asociada a un álbum.

    Attributes:
        cod_album (int): Identificador del álbum.
        imagen_bytes (bytes): Contenido binario de la imagen.
    """
    cod_album: int
    imagen_bytes: bytes


# ---------------------------------------------------------------------------
# Modelo para la Base de datos. Se utiliza para gestionar los datos de ingreso
# ---------------------------------------------------------------------------

@dataclass
class PaqueteDatos:
    """Paquete de información para insertar un álbum completo.

    Attributes:
        cancion (Cancion): Datos de la canción.
        album (Album): Datos del álbum.
        artistas (GrupoArtistas): Grupo de artistas asociados.
        genero (Optional[Genero]): Género opcional.
    """
    cancion: Cancion
    album: Album
    artistas: GrupoArtistas
    genero: Optional[Genero] = None

    def __str__(self) -> str:
        """Genera un resumen legible del paquete con canción, álbum y artistas."""
        can = self.cancion.titulo
        num = self.cancion.num_pista
        fec = self.album.lanzamiento
        art = self.artistas.principal
        alb = self.album.titulo
        (col, fea) = ("", "")
        if self.artistas.colaboradores:
            col = ",".join(c.nombre for c in self.artistas.colaboradores)
        if self.artistas.feat:
            fea = ",".join(f.nombre for f in self.artistas.feat)
        resp =  f"Album: {alb} {fec.year} ({self.album.pistas_totales})|| Art: {art.nombre} || Cancion: {can} N° {num}"
        if col:
            resp = f"{resp} & {col}"
        if fea:
            resp = f"{resp} (ft. {fea})"
        resp += "."
        return resp

    def tiene_el_codigo_album(self, codigo: str) -> bool:
        "Funciona para determinar si el paquete tiene el código del album."
        clase_album = self.album
        if clase_album.codigo == codigo:
            return True
        else:
            return False
    
# ---------------------------------------------------------------------------
# Clases de Salida para la Base de datos datos.
# ---------------------------------------------------------------------------

class SalidaArtista(BaseModel):
    """Representa un artista tal como está almacenado localmente.

    Attributes:
        id_local (int): Identificador local del artista.
        nombre (str): Nombre del artista.
        codigos (Optional[List[str]]): Códigos externos asociados.
    """
    id_local: int
    nombre: str
    codigos: Optional[List[str]] = None

    def coincide_con(self, artista: Artista) -> bool:
        """Compara los datos locales con un artista de entrada por nombre o código."""
        if self.codigos:
            for c in self.codigos:
                if c == artista.codigo:
                    return True
        return self.nombre.lower() == artista.nombre.lower()

    def revisar_codigo(self, codigo: str) -> bool:
        """Revisa si el código proporcionado está registrado en la salida local."""
        if self.codigos:
            for cod in self.codigos:
                if cod == codigo:
                    return True
            return False
        else:
            return False


class SalidaCancion(BaseModel):
    """Datos de una canción tal como están en la base de datos local.

    Attributes:
        id_local (int): Identificador local de la canción.
        titulo (str): Título de la canción.
        album_id (int): Identificador del álbum asociado.
        numero_cancion (int): Número de pista de la canción.
        codigos (Optional[List[str]]): Códigos externos asociados.
    """
    id_local: int
    titulo: str
    album_id: int
    numero_cancion: int
    codigos: Optional[List[str]] = None

    def coincide_con(self, cancion: Cancion) -> bool:
        """
        Compara los datos locales con los de entrada; compara tanto nombres como códigos.
        """
        if self.codigos:
            for c in self.codigos:
                if c == cancion.codigo:
                    return True
        # Fallback: nombre
        return (self.titulo.lower() == cancion.titulo.lower())

    def __str__(self) -> str:
        """Devuelve un resumen textual de la canción almacenada localmente."""
        return f"Cancion[ID:{self.id_local} - {self.titulo} || N°{self.numero_cancion} en album {self.album_id}]"


class SalidaAlbum(BaseModel):
    """Clase para gestionar los datos de un álbum tal como están en la base de datos local.

    Attributes:
        id_local (int): Identificador local del álbum.
        titulo (str): Título del álbum.
        pistas_totales (int): Número total de pistas.
        lanzamiento (date): Fecha de lanzamiento.
        codigos (Optional[List[str]]): Códigos externos asociados.
    """
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
        # Fallback: nombre, pistas y año lanzamiento
        return (
            self.titulo.lower() == album.titulo.lower() and
            self.pistas_totales == album.pistas_totales and
            self.lanzamiento.year == album.lanzamiento.year
        )

    def __str__(self) -> str:
        """Genera una representación legible del álbum almacenado."""
        return f"Album[ID:{self.id_local} - {self.titulo} : N°{self.pistas_totales} canciones || {date.isoformat(self.lanzamiento)}]"


class SalidaCaratula(BaseModel):
    """Representa la carátula de un álbum almacenada localmente.

    Attributes:
        id_local (int): Identificador local de la carátula.
        id_album (int): Identificador del álbum asociado.
        url_caratula (str): URL de la carátula.
        imagen_bytes (Optional[bytes]): Contenido binario de la imagen.
    """
    id_local: int
    id_album: int
    url_caratula: str
    imagen_bytes: Optional[bytes] = None

    def tiene_imagen(self) -> bool:
        """Indica si la carátula local tiene contenido binario cargado."""
        return isinstance(self.imagen_bytes, bytes) and bool(self.imagen_bytes)
