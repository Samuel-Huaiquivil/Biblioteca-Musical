from datetime import date, datetime
from typing import List
from abc import ABC, abstractmethod

from models.schemas_mbz import RespuestaMbz
from models.schemas_v5 import Album, Cancion, Artista, GrupoArtistas, PaqueteDatos
from models.schemas_itunes_v5 import RespuestaItunes
from models.schemas_motor import ItemNormalizado

# ---------------------------------------------------------------------------
# ADAPTADORES PARA LA BASE DE DATOS
# ---------------------------------------------------------------------------


class AdaptadorBaseDatos(ABC):
    """Interfaz base para convertir respuestas externas en paquetes listos para insertar."""

    @abstractmethod
    def paquete(self) -> PaqueteDatos:
        """Debe devolver un paquete de datos con canción, álbum y artistas."""
        raise NotImplementedError


class AdaptadorItunes(AdaptadorBaseDatos):
    """Convierte respuestas de iTunes en paquetes de datos del modelo local."""

    def paquete(self) -> PaqueteDatos:
        """Devuelve un paquete por defecto para evitar errores al instanciar la clase."""
        can = Cancion(titulo="Cancion")
        alb = Album(titulo="Album")
        art = GrupoArtistas(principal=Artista(nombre="Artista"))
        return PaqueteDatos(cancion=can, album=alb, artistas=art)

    def convertir_art_simple(self, itunes: RespuestaItunes) -> PaqueteDatos:
        """Convierte una respuesta sencilla de iTunes con un solo artista principal."""
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
        """Convierte una respuesta con varios artistas y colaboradores."""
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
        """Convierte un single o álbum corto, marcando el título como single si aplica."""
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


class AdaptadorMBZ(AdaptadorBaseDatos):
    """Convierte respuestas de MusicBrainz en paquetes de datos del modelo local."""

    def paquete(self) -> PaqueteDatos:
        """Devuelve un paquete por defecto para evitar errores al instanciar la clase."""
        can = Cancion(titulo="Cancion")
        alb = Album(titulo="Album")
        art = GrupoArtistas(principal=Artista(nombre="Artista"))
        return PaqueteDatos(cancion=can, album=alb, artistas=art)

    def conv_respuesta_global(self, respuesta: RespuestaMbz, fmt: bool = True) -> List[PaqueteDatos]:
        """Convierte una respuesta completa de MusicBrainz en paquetes de álbum/canción/artistas."""
        paquetes: List[PaqueteDatos] = []
        for release in respuesta.releases:
            album = release.to_album(format=fmt)
            canciones = release.to_cancion_media()
            artistas = release.to_artistas_album()
            for cancion in canciones:
                paquetes.append(
                    PaqueteDatos(
                        cancion=cancion,
                        album=album,
                        artistas=artistas,
                    )
                )
        return paquetes

    def conv_respuesta_grupo(self, respuesta: RespuestaMbz) -> List[PaqueteDatos]:
        lista: List[PaqueteDatos] = []
        can = respuesta.to_cancion_grupo()
        alb = respuesta.to_album_grupo()
        art = respuesta.to_artistas_cancion()
        for a in alb:
            lista.append(
                PaqueteDatos(
                    cancion=can,
                    album=a,
                    artistas=art
                )
            )
        return lista

# ---------------------------------------------------------------------------
# ADAPTADORES PARA EL MOTOR DE PUNTUACION
# ---------------------------------------------------------------------------


class AdaptadorMotor(ABC):
    """Base para normalizar elementos de entrada a un formato común para el motor."""

    def normalizar(self) -> ItemNormalizado:
        """Devuelve un item normalizado vacío por defecto."""
        return ItemNormalizado()


class NormalizadorItunes(AdaptadorMotor):
    """Normaliza una respuesta de iTunes al formato usado por el motor de puntuación."""

    def normalizar(self, item: RespuestaItunes) -> ItemNormalizado:
        """Transforma una respuesta de iTunes en un item normalizado."""
        tit = item.collectionName
        lan = item.releaseDate
        art = item.collectionArtistName or item.artistName
        cod = item.collectionId
        url = item.get_url(hd=True)
        return ItemNormalizado(
            titulo_album=tit,
            lanzamiento=lan,
            artista_principal=art,
            codigo_album=str(cod),
            url_descarga=url
        )


class NormalizadorMBZ(AdaptadorMotor):
    """Normaliza una respuesta de MusicBrainz a una lista de items para el motor."""

    def url_mbz(self, codigo: str) -> str:
        return f"https://coverartarchive.org/release/{codigo}"

    def normalizar(self, item: RespuestaMbz) -> List[ItemNormalizado]:
        """Transforma los releases de MusicBrainz en un listado de items normalizados."""
        lista_items: List[ItemNormalizado] = []
        ptje = item.score // 10
        for release in item.releases:
            if release.status != "Official":
                ptje = 10
            tit = release.title
            if release.disambiguation:
                tit = tit + " " + release.disambiguation
            lan = release.date
            art = release.to_artistas_album().principal.nombre
            cod = release.id
            url = self.url_mbz(release.id)
            lista_items.append(
                ItemNormalizado(
                    titulo_album=tit,
                    lanzamiento=lan,
                    artista_principal=art,
                    codigo_album=cod,
                    ptje_referencia=ptje,
                    url_descarga=url
                )
            )
        return lista_items

