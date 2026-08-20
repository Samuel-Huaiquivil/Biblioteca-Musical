from datetime import date
from typing import List

from pydantic import BaseModel

from models.schemas_v5 import Album, Artista, Cancion, Genero, Ident
from utils.parsear_artistas import parsear_artistas, parsear_track

class RespuestaItunes(BaseModel):
    """Representa un ítem de respuesta de la iTunes Search API.

    Esta clase sirve como puente entre los datos crudos retornados por
    iTunes y los modelos de dominio utilizados por el proyecto.
    Proporciona métodos para convertir la respuesta en álbumes, canciones,
    artistas y géneros con un formato más útil para el procesamiento local.
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

    def _fecha_lanzamiento(self) -> date:
        """Devuelve la fecha de lanzamiento como un objeto date.

        Si el valor de entrada no es una fecha ISO válida, se devuelve la
        fecha por defecto usada por los modelos del proyecto.
        """
        texto = (self.releaseDate or "").strip()
        if not texto:
            return date(2000, 1, 1)

        for valor in (texto[:10], texto):
            if not valor:
                continue
            try:
                return date.fromisoformat(valor)
            except ValueError:
                continue

        return date(2000, 1, 1)

    def ident(self) -> Ident:
        """Crea el identificador de la respuesta para el almacenamiento local."""
        return Ident(
            api="iTunes",
            region=self.country or "USA",
            id=0
        )

    def es_single(self) -> bool:
        """Indica si la respuesta corresponde a un single o álbum corto."""
        return "single" in self.collectionName.lower() and self.trackCount <= 3

    def es_extended(self) -> bool:
        return "- ep" in self.collectionArtistName.lower() and self.trackCount <= 7 and self.trackCount >=3

    def tiene_multiples_artistas(self) -> bool:
        """Determina si la colección está asociada a varios artistas."""
        return self.collectionArtistName != "" or self.collectionArtistId != 0

    def to_genero(self) -> Genero:
        """Convierte el género de la respuesta en un modelo de dominio."""
        return Genero(nombre=self.primaryGenreName or "Desconocido")

    def to_album(self, fmt: bool = True) -> Album:
        """Convierte la respuesta en un álbum con título y fecha normalizados."""
        clase = parsear_track(self.collectionName)
        return Album(
            titulo=clase.titulo if fmt else self.collectionName,
            lanzamiento=self._fecha_lanzamiento(),
            codigo=str(self.collectionId),
            pistas_totales=self.trackCount,
            url_descarga=self.get_url()
        )

    def to_cancion(self) -> Cancion:
        """Convierte la respuesta en una canción con el título limpio."""
        clase = parsear_track(self.trackName)
        return Cancion(
            titulo=clase.titulo,
            num_pista=self.trackNumber,
            codigo=str(self.trackId)
        )

    def to_artista_principal(self, simple: bool = False) -> Artista:
        """Devuelve el artista principal de la respuesta.

        Args:
            simple: Si es True, usa el nombre del artista de la pista sin
                resolver colaboraciones adicionales.
        """
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

    def to_album_sgle(self, fmt: bool = True) -> Album:
        """Retorna un álbum con título limpio. fmt:= (Single)."""
        clase = parsear_track(self.collectionName)
        tit = clase.titulo
        if fmt and "single" not in tit.lower():
            tit_fmt = tit + " (Single)"
        return Album(
            titulo=tit_fmt if fmt else tit,
            lanzamiento=self._fecha_lanzamiento(),
            pistas_totales=self.trackCount,
            codigo=str(self.collectionId),
            url_descarga=self.get_url()
        )

    def to_album_exte(self, fmt: bool = True) -> Album:
        clase = parsear_track(self.collectionName)
        tit = clase.titulo
        tit_fmt = tit
        if clase.version:
            tit_fmt = tit + f" ({clase.version})"
        return Album(
            titulo=tit_fmt if fmt else tit,
            lanzamiento=self._fecha_lanzamiento(),
            pistas_totales=self.trackCount,
            codigo=str(self.collectionId),
            url_descarga=self.get_url()
        )

    def art_principal_str(self) -> str:
        """Retorna el nombre del artista principal del álbum."""
        if self.collectionArtistName:
            return parsear_artistas(self.collectionArtistName)[0]
        else:
            return parsear_artistas(self.artistName)[0]

    def art_colab(self) -> List[Artista]:
        """Devuelve la lista de colaboradores del álbum."""
        colab: List[Artista] = []
        p = self.art_principal_str()
        if self.artistName.lower() != p.lower():
            lista = parsear_artistas(self.artistName)
            for el in lista:
                if el.lower() != p.lower():
                    colab.append(Artista(nombre=el))
        else:
            lista = parsear_track(self.collectionArtistName)
            for el in lista.artistas:
                if el.lower() != p.lower():
                    colab.append(Artista(nombre=el))
        return colab

    def art_feat(self) -> List[Artista]:
        """Devuelve la lista de artistas invitados o featurings del álbum."""
        clase = parsear_track(self.collectionName)
        elemento_principal = self.art_principal_str().lower()
        feat = [
            Artista(nombre=el)
            for el in clase.artistas
            if el.lower() != elemento_principal and "single" not in el.lower()
        ]
        return feat

    def get_url(self, hd: bool = False) -> str:
        """Devuelve la URL de portada, priorizando la resolución más alta disponible."""
        url = ""
        for u in [
            self.artworkUrl100,
            self.artworkUrl60,
            self.artworkUrl30
        ]:
            if u:
                url = u
                break
        if not url:
            return url
        url = url.replace("30x30bb", "60x60bb")
        url = url.replace("60x60bb", "100x100bb")
        url_hd = url.replace("100x100bb", "600x600bb")
        return url_hd if hd else url
