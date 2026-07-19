from datetime import date
from typing import List

from pydantic import BaseModel

from models.schemas_v5 import Album, Artista, Cancion, Genero, Ident
from utils.parsear_artistas import parsear_artistas, parsear_track

class RespuestaItunes(BaseModel):
    """
    Representa un ítem de respuesta de la iTunes Search API
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
    artworkUrl100: str

    # Opcionales (compilaciones / varios artistas)
    collectionArtistName: str = ""
    collectionArtistId: int = 0

    # Opcionales (miniaturas adicionales)
    artworkUrl60: str = ""
    artworkUrl30: str = ""

    # Opcionales varios
    country: str = ""
    discCount: int = 1
    discNumber: int = 1
    trackTimeMillis: int = 0
    isStreamable: bool = False
    collectionExplicitness: str = ""
    trackExplicitness: str = ""

    def ident(self) -> Ident:
        "Gestiona el Identificador de Códigos"
        return Ident(
            api="iTunes",
            region=self.country or "USA",
            id=0
        )

    def es_album_single(self):
        if "single" in self.collectionName.lower() and self.trackCount <= 3:
            return True
        else:
            return False

    def tiene_multiples_artistas(self):
        if self.collectionArtistName != "" or self.collectionArtistId != 0:
            return True
        else:
            return False

    def to_genero(self) -> Genero:
        "Retorna el genero de la canción"
        return Genero(nombre=self.primaryGenreName or "Desconocido")

    def to_album(self) -> Album:
        "Retorna Clase Album con los datos"
        clase = parsear_track(self.collectionName)
        return Album(
            titulo=clase.titulo,
            lanzamiento=date.fromisoformat(self.releaseDate[:10]),
            codigo=str(self.collectionId),
            pistas_totales=self.trackCount
        )

    def to_cancion(self) -> Cancion:
        "Clase Cancion con el título limpio"
        clase = parsear_track(self.trackName)
        return Cancion(
            titulo=clase.titulo,
            num_pista=self.trackNumber,
            codigo=str(self.trackId)
        )

    def to_artista_principal(self, simple: bool = False) -> Artista:
        if simple:
            return Artista(
                nombre=self.artistName,
                codigo=str(self.collectionArtistId)
            )
        if self.collectionArtistName != "" and self.collectionArtistId != 0:
            return Artista(
                nombre=self.collectionArtistName,
                codigo=str(self.collectionArtistId)
            )
        else:
            art = parsear_artistas(self.artistName)
            return Artista(
                nombre=art[0],
                codigo=str(self.artistId)
            )

    def to_album_colab(self, single: bool = False) -> Album:
        "Retorna un Álbum con título limpio"
        clase = parsear_track(self.collectionName)
        tit = clase.titulo
        if single:
            if "single" not in tit.lower():
                tit = tit + " (Single)"
            else:
                pass
        return Album(
            titulo=tit,
            lanzamiento=date.fromisoformat(self.releaseDate[:10]),
            pistas_totales=self.trackCount,
            codigo=str(self.collectionId)
        )

    def art_principal(self) -> str:
        "Retorna el Artista Principal del Álbum"
        if self.collectionArtistName:
            return parsear_artistas(self.collectionArtistName)[0]
        else:
            return parsear_artistas(self.artistName)[0]

    def art_colab(self) -> List[str]:
        "Lista de colaboradores del Álbum"
        colab: List[str] = []
        p = self.art_principal()
        if self.artistName.lower() != p.lower():
            lista = parsear_artistas(self.artistName)
            for el in lista:
                if el.lower() != p.lower():
                    colab.append(el)
        else:
            lista = parsear_artistas(self.collectionArtistName)
            for el in lista:
                if el.lower() != p.lower():
                    colab.append(el)
        return colab

    def art_feat(self) -> List[str]:
        "List de feature del Álbum"
        feat: List[str] = []
        clase = parsear_track(self.collectionName)
        elem = clase.artistas
        p = self.art_principal()
        for el in elem:
            if el.lower() != p.lower():
                feat.append(el)
        for f in feat:
            if "single" in f.lower():
                feat.remove(f)
        return feat


