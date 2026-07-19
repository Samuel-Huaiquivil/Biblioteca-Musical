from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from abc import ABC, abstractmethod

from models.schemas_v5 import Album, Cancion, Artista, GrupoArtistas, PaqueteDatos
from models.schemas_itunes_v5 import RespuestaItunes
from models.schemas_mbz import ArtistCreditMBZ,MediaMBZ, ReleaseMBZ
from utils.parsear_artistas import parsear_artistas

class AdaptadorBase(ABC):
    @abstractmethod
    def paquete(self) -> PaqueteDatos:
        """Debe devolver un PaqueteDatos"""
        raise NotImplementedError


class AdaptadorItunes(AdaptadorBase):
    "Clase para convertir resultados"
    def paquete(self) -> PaqueteDatos:
        can = Cancion(titulo="Cancion")
        alb = Album(titulo="Album")
        art = GrupoArtistas(principal=Artista(nombre="Artista"))
        return PaqueteDatos(cancion=can, album=alb, artistas=art)

    def convertir_art_simple(self, itunes: RespuestaItunes) -> PaqueteDatos:
        gen = itunes.to_genero()
        alb = itunes.to_album()
        can = itunes.to_cancion()
        art = itunes.to_artista_principal(True)
        return PaqueteDatos(
            cancion=can,
            album=alb,
            artistas=GrupoArtistas(
                principal=art,
                colaboradores=[],
                feat=[]
            ),
            genero=gen
        )

    def convertir_mult_artistas(self, itunes: RespuestaItunes) -> PaqueteDatos:
        gen = itunes.to_genero()
        alb = itunes.to_album_colab()
        art = GrupoArtistas(
            principal=itunes.to_artista_principal(),
            colaboradores=itunes.art_colab() or [],
            feat=itunes.art_feat() or []
        )
        can = itunes.to_cancion()
        return PaqueteDatos(
            cancion=can,
            album= alb,
            artistas=art,
            genero=gen
        )

    def convertir_album_single(self, itunes: RespuestaItunes) -> PaqueteDatos:
        gen = itunes.to_genero()
        alb = itunes.to_album_colab(single=True)
        art = GrupoArtistas(
            principal=itunes.to_artista_principal(),
            colaboradores=itunes.art_colab() or [],
            feat=itunes.art_feat() or []
        )
        can = itunes.to_cancion()
        return PaqueteDatos(
            cancion=can,
            album= alb,
            artistas=art,
            genero=gen
        )



class AdaptadorMBZ(AdaptadorBase):
    def convertir(self, datos: dict) -> None:
        return None


class ArtistaVar(BaseModel):
    codigo: str = ""
    nombre: str = ""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

# ---------------------------------------------------------------------------
# Modelo de validación de respuesta iTunes y MBZ
# ---------------------------------------------------------------------------


class RespuestaMBZ(BaseModel):
    "Representa los datos relevantes de una respuesta de MBZ."
    #Cancion
    cancion_titulo: str = ""
    cancion_mbz: str = ""
    #Artistas
    artistas: List[Artista] = Field(default_factory=list)
    #Album
    album_mbz: str = ""
    album_titulo: str = ""
    estatus: str = ""
    pistas: int = 0
    fecha: str = ""
    # Existe un grupo al que varios albumes pertenecen
    grp_album_mbz: str = ""
    grp_album_titulo: str = ""

    def __str__(self) -> str:
        return f"RMBZ[{self.cancion_titulo} - {self.artistas[0].nombre} / GRP:= {self.grp_album_titulo}]"


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------


def _normalizar_artistas(lista_artistas: List[ArtistCreditMBZ]) -> List[Artista]:
    artistas = []
    if not lista_artistas:
        return artistas
    for ac in lista_artistas:
        if ac.artist:
            artistas.append(Artista(
                codigo=ac.artist.id,
                nombre=ac.name or ac.artist.name
            ))
        elif ac.name:
            artistas.append(Artista(
                codigo="",
                nombre=ac.name
            ))
    return artistas


def _parse_date_safe(date_str: str) -> tuple:
    """Retorna (año, mes, día) o (9999, 99, 99) si inválido."""
    try:
        dt = datetime.fromisoformat(date_str)
        return (dt.year, dt.month, dt.day)
    except (ValueError, TypeError):
        return (9999, 99, 99)


def _elegir_media(medias: List[MediaMBZ])  -> Optional[MediaMBZ]:
    if not medias:
        return None
    con_formato = [m for m in medias if m.format != ""]
    count = []
    if con_formato:
        count = [f for f in con_formato if f.track_count != 0]
    return count[0] if count else medias[0]


def _elegir_release(releases: List[ReleaseMBZ]) -> Optional[ReleaseMBZ]:
    if not releases:
        return None
    
    # Priorizar oficiales
    oficiales = [r for r in releases if r.status.lower() == "official"]
    candidatos = oficiales if oficiales else releases

    # Ordenar por fecha
    candidatos.sort(key=lambda r: _parse_date_safe(r.date))
    return candidatos[0]

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

    # Convertir al modelo Definido
    def estandarizar(self) -> RespuestaMBZ:
        if not self.title or not self.id:
            raise ValueError(f"Recording incompleto: title={self.title}, id={self.id}")
    
        release = _elegir_release(self.releases)
        if not release:
            raise ValueError(f"No se encontró release válido para '{self.title}'")
        
        titulo_final = f"{self.title} {self.disambiguation or ""}"
        artistas = _normalizar_artistas(self.artist_credit)
        
        grp_id, grp_title = "", ""
        if release and release.release_group:
            grp_id = release.release_group.id or ""
            grp_title = release.release_group.title or ""

        estatus = release.status or ""
        fecha = release.date or ""
        if release and release.media:
            media = _elegir_media(release.media)
            if media:
                pistas = media.track_count
            else:
                pistas = 0
        return RespuestaMBZ(
            cancion_titulo=titulo_final,
            cancion_mbz=self.id,
            artistas=artistas,
            album_mbz=release.id if release else "",
            album_titulo=release.title if release else "",
            estatus=estatus,
            fecha=fecha,
            pistas=pistas,
            grp_album_mbz=grp_id,
            grp_album_titulo=grp_title
        )
