# utils/dicc_a_clases.py
# Convierte un objeto RespuestaItunes (ya validado) a modelos del dominio.
# Recibe RespuestaItunes, no diccionarios crudos.

from datetime import date
from typing import List

from models.schemas import Album, Cancion, GrupoArtistas, Genero, RespuestaItunes
from utils.parsear_artistas import parsear_artistas


def _explicito(valor: str) -> bool:
    """Convierte el string de iTunes a booleano."""
    return valor.lower() != "notexplicit"


def convertir_a_genero(resp: RespuestaItunes) -> Genero:
    return Genero(nombre=resp.primaryGenreName or "Desconocido")


def convertir_a_album(resp: RespuestaItunes) -> Album:
    """
    Extrae los datos del álbum de la respuesta iTunes.
    El título del álbum puede contener colaboraciones en singles
    (ej: 'Canción - EP'), se toma solo la primera parte.
    """
    fecha = date.fromisoformat(resp.releaseDate[:10])
    titulo = parsear_artistas(resp.collectionName)
    titulo_limpio = titulo[0] if titulo else resp.collectionName

    return Album(
        titulo=titulo_limpio,
        lanzamiento=fecha,
        codigo_itunes=resp.collectionId,
        num_pistas=resp.trackCount,
        explicito=_explicito(resp.collectionExplicitness),
    )


def convertir_a_cancion(resp: RespuestaItunes) -> Cancion:
    return Cancion(
        titulo=resp.trackName,
        num_pista=resp.trackNumber,
        explicito=_explicito(resp.trackExplicitness),
        codigo_itunes=resp.trackId,
    )


def convertir_a_grupo_artistas(resp: RespuestaItunes) -> GrupoArtistas:
    """
    Determina artista principal, colaboradores y featurings.

    Lógica iTunes:
    - collectionArtistName → artista del álbum (existe en compilaciones)
    - artistName           → artista principal de la canción/single
    - trackName            → puede contener "feat. X" o "(with X)"

    Los featurings suelen estar en el título de la canción o del álbum
    en el caso de singles. Se parsean desde collectionName si aplica.
    """
    # Artista principal: preferir artista del álbum si existe (compilaciones)
    nombre_principal = resp.collectionArtistName or resp.artistName
    codigo = resp.collectionArtistId or resp.artistId

    # Colaboradores: parsear artistName si difiere del principal
    colaboradores: List[str] = []
    if resp.artistName and resp.artistName != nombre_principal:
        colaboradores = parsear_artistas(resp.artistName)
        # El primero suele ser el mismo artista principal, lo quitamos
        if colaboradores and colaboradores[0].lower() == nombre_principal.lower():
            colaboradores.pop(0)

    # Featurings: parsear el título del álbum (en singles suele tener "feat.")
    feat_raw = parsear_artistas(resp.collectionName)
    # El primer elemento es el título, el resto son colaboraciones del título
    feat = feat_raw[1:] if len(feat_raw) > 1 else []

    return GrupoArtistas(
        principal=nombre_principal,
        codigo_itunes=codigo,
        colaboradores=colaboradores or None,
        feat=feat or None,
    )


def convertir_respuesta(resp: RespuestaItunes) -> dict:
    """
    Punto de entrada principal. Convierte una RespuestaItunes validada
    a un diccionario con todos los modelos del dominio.
    """
    return {
        "genero": convertir_a_genero(resp),
        "artistas": convertir_a_grupo_artistas(resp),
        "album": convertir_a_album(resp),
        "cancion": convertir_a_cancion(resp),
    }
