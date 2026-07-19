

from datetime import date
from typing import List

from models.schemas import Album, Cancion, Caratula, DatosCaratula, GrupoArtistas, Genero
from models.schemas_api import RespuestaItunes
from utils.parsear_artistas import parsear_artistas


def convertir_a_genero(resp: RespuestaItunes) -> Genero:
    return Genero(nombre=resp.primaryGenreName or "Desconocido")


def convertir_a_album_mult(resp: RespuestaItunes, single: bool = False) -> Album:
    """
    Extrae los datos del álbum de la respuesta iTunes.
    El título del álbum puede contener colaboraciones en singles o múltiples artistas
    (ej: 'Canción - EP'), se toma solo la primera parte.
    """
    fecha = date.fromisoformat(resp.releaseDate[:10])
    titulo = parsear_artistas(resp.collectionName)
    titulo_limpio = titulo[0] if titulo else resp.collectionName
    if single:
        if "single" not in titulo_limpio.lower():
            titulo_limpio = titulo_limpio + " (Single)"
    return Album(
        titulo=titulo_limpio,
        lanzamiento=fecha,
        codigo_itunes=resp.collectionId,
        pistas_totales=resp.trackCount
    )


def convertir_a_album_solo(resp: RespuestaItunes) -> Album:
    """
    Extrae los datos del álbum de la respuesta iTunes.
    El título del álbum puede contener colaboraciones en singles
    (ej: 'Canción - EP'), se toma solo la primera parte.
    """
    fecha = date.fromisoformat(resp.releaseDate[:10])
    return Album(
        titulo=resp.collectionName,
        lanzamiento=fecha,
        codigo_itunes=resp.collectionId,
        pistas_totales=resp.trackCount
    )


def convertir_a_cancion(resp: RespuestaItunes, single: bool = False) -> Cancion:
    if single:
        titulo = parsear_artistas(resp.trackName)[0]
        return Cancion(
            titulo=titulo,
            num_pista=resp.trackNumber,
            codigo_itunes=resp.trackId,
        )
    else:
        return Cancion(
            titulo=resp.trackName,
            num_pista=resp.trackNumber,
            codigo_itunes=resp.trackId,
        )


def convertir_a_caratula(resp: RespuestaItunes, hd: bool = False) -> Caratula:
    if hd:
        url = resp.artworkUrl100.replace("100x100bb", "600x600bb")
    else:
        url = resp.artworkUrl100
    return Caratula(
        codigo_album=resp.collectionId,
        url_caratula=url,
        imagen=None
    )


def convertir_a_grupo_artistas(resp: RespuestaItunes, single: bool = False) -> GrupoArtistas:
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

        # Quitamos el artista principal, si es que está en la lista
        if colaboradores:
            for colab in colaboradores:
                if colab.lower() == nombre_principal.lower():
                    colaboradores.remove(colab)

    # Featurings: parsear el título del álbum (en singles suele tener "feat.")
    feat_raw = parsear_artistas(resp.collectionName)
    # El primer elemento es el título, el resto son colaboraciones del título
    feat = feat_raw[1:] if len(feat_raw) > 1 else []

    if single:
        artistas = parsear_artistas(resp.artistName)
        nombre_principal = artistas.pop(0) if artistas else resp.artistName
        colaboradores = artistas  # lo que queda después del pop ya son los colaboradores
        if len(feat) > 1 and "single" in feat[-1].lower():
            feat.pop(-1)

    return GrupoArtistas(
        principal=nombre_principal,
        codigo_itunes=codigo,
        colaboradores=colaboradores or None,
        feat=feat or None,
    )


def convertir_a_artista_solo(resp: RespuestaItunes) -> GrupoArtistas:
    "Se utiliza para NO parsear el título del album o los duetos."
    return GrupoArtistas(
        principal=resp.artistName,
        codigo_itunes=resp.artistId,
        colaboradores=None,
        feat=None
    )


def convertir_respuesta_arts(resp: RespuestaItunes) -> dict:
    """
    Punto de entrada principal. Convierte una RespuestaItunes validada
    a un diccionario con todos los modelos del dominio.
    Parsea los artistas y el nombre del Álbum
    """
    return {
        "genero": convertir_a_genero(resp),
        "artistas": convertir_a_grupo_artistas(resp),
        "album": convertir_a_album_mult(resp),
        "cancion": convertir_a_cancion(resp),
    }


def convertir_respuesta_smp(resp: RespuestaItunes) -> dict:
    """
    Punto de entrada principal. Convierte una RespuestaItunes validada
    a un diccionario con todos los modelos del dominio.

    Se utiliza para NO parsear el título del album o los duetos.
    """
    return {
        "genero": convertir_a_genero(resp),
        "artistas": convertir_a_artista_solo(resp),
        "album": convertir_a_album_solo(resp),
        "cancion": convertir_a_cancion(resp),
    }


def convertir_respuesta_album_single(resp: RespuestaItunes) -> dict:
    """
    Punto de entrada principal. Convierte una RespuestaItunes validada
    a un diccionario con todos los modelos del dominio.
     
    Se utiliza para gestionar albumes single.
    """
    return {
        "genero": convertir_a_genero(resp),
        "artistas": convertir_a_grupo_artistas(resp, True),
        "album": convertir_a_album_mult(resp, True),
        "cancion": convertir_a_cancion(resp, True),
    }




def _convertir_a_contenedor(diccionario: Dict[str, Any], estado_cancion: bool = False, album_revisado: bool = False) -> Contenedor:
    clase_gen = diccionario["genero"]
    clase_art = diccionario["artistas"]
    clase_alb = diccionario["album"]
    clase_can = diccionario["cancion"]
    return Contenedor(
        genero=clase_gen,
        artistas=clase_art,
        album=clase_alb,
        cancion=clase_can,
        album_revisado=album_revisado,
        cancion_estado=estado_cancion
    )


def resp_itunes(diccionario_itunes: Dict[str, Any], principal: bool = False, alb_rev: bool = False):
    dicc = _revisar_diccionario(diccionario=diccionario_itunes)
    con = _convertir_a_contenedor(dicc, principal, alb_rev)
    return con

