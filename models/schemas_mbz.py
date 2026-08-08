from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Tuple
from datetime import date

from models.schemas_v5 import Album, Artista, Cancion, GrupoArtistas, PaqueteDatos

# ---------------------------------------------------------------------------
# Funciones Auxiliares
# ---------------------------------------------------------------------------

def _parsear_fecha(fecha_str: str) -> date:
    """Convierte una fecha recibida de MusicBrainz a un objeto date.

    Acepta formatos como YYYY, YYYY-MM o YYYY-MM-DD. Si la entrada no es
    válida o está vacía, devuelve una fecha por defecto consistente con el
    resto del proyecto.
    """
    if not fecha_str:
        return date(2000, 1, 1)

    try:
        return date.fromisoformat(fecha_str)
    except ValueError:
        pass

    partes = fecha_str.split("-")
    if not partes or not partes[0].isdigit():
        return date(2000, 1, 1)

    anio = int(partes[0])
    mes = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 1
    dia = int(partes[2]) if len(partes) > 2 and partes[2].isdigit() else 1

    try:
        return date(anio, mes, dia)
    except ValueError:
        return date(2000, 1, 1)

# ---------------------------------------------------------------------------
# Sub-modelos (partes de un resultado de MusicBrainz)
# ---------------------------------------------------------------------------


class ArtistMBZ(BaseModel):
    """Artista dentro de un artist-credit de MusicBrainz."""
    id: str
    name: str
    sort_name: str = Field(default="", alias="sort-name")

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    def to_artista(self) -> Artista:
        """Convierte el artista de MusicBrainz a un modelo local de artista."""
        return Artista(
            nombre=self.name,
            codigo=self.id
        )


class ArtistCreditMBZ(BaseModel):
    """
    Entrada en la lista artist-credit.
    Puede ser un artista o un separador de texto (ej: ' feat. ').
    """
    name: Optional[str] = None      # Nombre tal como aparece en el crédito
    artist: Optional[ArtistMBZ] = None
    joinphrase: str = ""

    def to_artista(self) -> Artista:
        """Convierte un crédito de artista a un artista local, si está disponible."""
        if self.artist:
            return self.artist.to_artista()
        return Artista(
            nombre=self.name or "",
            codigo=""
        )


class ReleaseGroupMBZ(BaseModel):
    id: str = ""
    title: str = ""
    primary_type: Optional[str] = Field(alias="primary-type", default=None)
    secondary_types: Optional[List[str]] = Field(alias="secondary-types", default=None)

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class TrackMBZ(BaseModel):
    id: str = ""
    number: str = ""
    title: str = ""
    length: int = 0

    def obtener_numero(self) -> int:
        """Intenta extraer el número de pista como entero de forma segura."""
        try:
            return int(self.number)
        except ValueError:
            try:
                return int(self.number[1:])
            except ValueError:
                return 1


class MediaMBZ(BaseModel):
    id: str = ""
    position: int = 0
    format: str = ""
    track: List[TrackMBZ] = Field(default_factory=list)
    track_count: int = Field(alias="track-count", default=0)
    track_offset: int = Field(alias="track-offset", default=0)

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    def _formatear_track(self, track: TrackMBZ) -> TrackMBZ:
        """Replica el track con un identificador más informativo para la conversión."""
        track_id: str = f"{self.format}: {track.id}"
        track_titulo: str = track.title
        track_num = track.obtener_numero()
        return TrackMBZ(
            id=track_id,
            number=str(track_num),
            title=track_titulo
        )

    def _obtener_track(self) -> TrackMBZ:
        """Selecciona el track principal de la media para construir la canción."""
        if not self.track:
            return TrackMBZ()

        if len(self.track) > 1:
            tracks: List[TrackMBZ] = []
            for t in self.track:
                track = self._formatear_track(t)
                tracks.append(track)
            return tracks[0]
        else:
            return self._formatear_track(self.track[0])

    def to_cancion(self, val: int = 1) -> Cancion:
        """Convierte una media de MusicBrainz en una canción con número de pista calculado."""
        t = self._obtener_track()
        if not val:
            val = 1

        numero = t.obtener_numero()
        if self.position:
            pista = (val * (self.position - 1)) + numero
        else:
            pista = numero

        titulo = t.title.strip() or "Sin título"
        return Cancion(
            titulo=titulo,
            num_pista=pista,
            codigo=t.id
        )


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
    count: int = Field(default=0, alias="count")
    track_count: int = Field(default=0, alias="track-count")
    release_group: Optional[ReleaseGroupMBZ] = Field(default=None, alias="release-group")
    media: List[MediaMBZ] = Field(default_factory=list)
    
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    def __str__(self) -> str:
        return f"Release[{self.title} - {self.id}]"

    def es_oficial(self) -> bool:
        """Indica si el release está marcado como oficial en MusicBrainz."""
        if "official" in self.status.lower():
            return True
        else:
            return False

    def to_artistas_album(self) -> GrupoArtistas:
        """Construye el grupo de artistas asociado al álbum."""
        princ = self.artist_credit[0].to_artista()
        if len(self.artist_credit) > 1:
            artistas: List[Artista] = []
            for art in self.artist_credit[1:]:
                artistas.append(art.to_artista())
            return GrupoArtistas(
                principal=princ,
                colaboradores=artistas
                )
        else:           
            return GrupoArtistas(
                principal=princ
            )

    def to_cancion_media(self) -> List[Cancion]:
        """Convierte las pistas del release en una lista de canciones."""
        res: List[Cancion] = []
        val: int = self.track_count // self.count if self.count else 1
        if len(self.media) > 1:
            for m in self.media:
                res.append(m.to_cancion(val))
            return res
        else:
            return [self.media[0].to_cancion()]

    def to_album(self, format: bool = True) -> Album:
        """Convierte el release a un álbum del modelo local."""
        tit = self.title
        if self.disambiguation:
            txt = f"{tit} ({self.disambiguation})"
        else:
            txt = tit
        if not self.country:
            cod = f"ZZ: {self.id}"
        else:
            cod = f"{self.country}: {self.id}"
        return Album(
            titulo=txt,
            lanzamiento=_parsear_fecha(self.date),
            pistas_totales=self.track_count or 1,
            codigo=cod if format else self.id
        )

    def to_album_grupo(self) -> Album | None:
        """Convierte el grupo de lanzamiento a un álbum cuando exista información disponible."""
        if not self.release_group:
            return None
        else:
            grp = self.release_group
            return Album(
                titulo=grp.title,
                lanzamiento=_parsear_fecha(self.date),
                pistas_totales=self.track_count,
                codigo=grp.id
            )


# ---------------------------------------------------------------------------
# Modelo principal de un resultado de MusicBrainz (recording)
# ---------------------------------------------------------------------------

class RespuestaMbz(BaseModel):
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

    def __str__(self) -> str:
        rel_str = ";".join(str(r) for r in self.releases)
        return f"RespMBZ[{self.title} - {self.id}] ** [Rel {rel_str}]"

    def to_artistas_cancion(self) -> GrupoArtistas:
        """Construye el grupo de artistas asociado a la canción."""
        princ = self.artist_credit[0].to_artista()
        if len(self.artist_credit) > 1:
            artistas: List[Artista] = []
            for art in self.artist_credit[1:]:
                artistas.append(art.to_artista())

            if "feat" in self.artist_credit[0].joinphrase.lower():
                return GrupoArtistas(
                    principal=princ,
                    feat=artistas)
            else:
                return GrupoArtistas(
                    principal=princ,
                    colaboradores=artistas)
        else:           
            return GrupoArtistas(
                principal=princ
            )

    def to_cancion_grupo(self) -> Cancion:
        """Convierte la respuesta a una canción básica con identificador local."""
        tit = self.title
        if self.disambiguation:
            tit += self.disambiguation
        return Cancion(
            titulo=tit,
            num_pista=0,
            codigo=self.id
        )

    def to_album_grupo(self) -> List[Album]:
        """Devuelve los álbumes derivados de los releases asociados."""
        albumes: List[Album] = []
        for r in self.releases:
            alb = r.to_album_grupo()
            if alb:
                albumes.append(alb)
        return albumes

    # Datos más detallados
    def to_cancion_global(self) -> List[Cancion]:
        """Consolida todas las canciones de los releases en una lista única."""
        canciones: List[Cancion] = []
        for r in self.releases:
            c = r.to_cancion_media()
            canciones.extend(c)
        return canciones

    def to_album_global(self) -> List[Album]:
        """Consolida todos los álbumes de los releases en una lista única."""
        albumes: List[Album] = []
        for r in self.releases:
            alb = r.to_album()
            albumes.append(alb)
        return albumes

    def to_paquete_album(self) -> List[PaqueteDatos]:
        """Construye paquetes completos de álbum, canciones y artistas para inserción local."""
        paq: List[PaqueteDatos] = []
        for r in self.releases:
            # Album asociado
            alb = r.to_album()
            can = r.to_cancion_media()
            art = r.to_artistas_album()
            for c in can:
                paq.append(
                    PaqueteDatos(
                        cancion = c,
                        album = alb,
                        artistas = art
                    )
                )
        return paq

    # Formato Analisis
    def formatear(self) -> List[Tuple[Album, Artista]]:
        """Devuelve una lista de pares álbum-artista para procesamiento adicional."""
        respta: List[Tuple[Album, Artista]] = []
        for rel in self.releases:
            alb = rel.to_album(format=False)
            art = rel.to_artistas_album()
            respta.append(
                (alb, art.principal)
            )
        return respta

