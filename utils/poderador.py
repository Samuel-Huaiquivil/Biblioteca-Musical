# utils/ponderador.py
# Evalúa y selecciona el mejor diccionario iTunes de una lista de resultados.
from difflib import SequenceMatcher
from collections import Counter
from typing import List
from models.schemas import RespuestaItunes

# ---------------------------------------------------------------------------
# Pesos para evaluar qué tan completo es un resultado
# ---------------------------------------------------------------------------

_PESOS_COMPLETITUD = {
    "artistName": 5,
    "collectionName": 10,
    "trackName": 4,
    "releaseDate": 15,
    "primaryGenreName": 15,
    "artworkUrl100": 30,
    "artworkUrl60": 5,
    "artworkUrl30": 1,
}
_PESO_TOTAL = sum(_PESOS_COMPLETITUD.values())

_PALABRAS_COMPILACION = [
    "hits", "gran", "exitos", "éxitos", "colec", "definitiva",
    "edici", "mejor", "canciones", "edition", "songs",
    "best of", "collection", "definitive", "essential",
]

def _puntaje_completitud(dicc: dict) -> float:
    """Puntaje 0-1 según qué campos importantes están presentes."""
    suma = sum(peso for clave, peso in _PESOS_COMPLETITUD.items() if dicc.get(clave))
    return round(suma / _PESO_TOTAL, 2)

def _puntaje_similitud(palabra_referencia: str, palabra: str) -> float:
    """Puntaje 0-1 (ratio) dependiendo de la similitud"""
    return SequenceMatcher(None, palabra_referencia, palabra).ratio()

def es_compilacion(dicc: dict) -> bool:
    """
    Retorna True si el nombre del álbum sugiere que es una compilación
    (greatest hits, colección, etc.). Estas versiones son menos preferidas
    porque no representan el lanzamiento original de la canción.
    """
    nombre = dicc.get("collectionName", "").lower()
    artista = dicc.get("artistName", "").lower()
    palabras = _PALABRAS_COMPILACION + [artista]
    return any(p in nombre for p in palabras)

def propiedades_minimas(dicc: dict) -> bool:
    """
    Verifica que el diccionario tenga los campos mínimos obligatorios
    para ser procesado por el pipeline.
    """
    try:
        return (
            dicc.get("wrapperType") == "track"
            and dicc.get("kind") == "song"
            and dicc.get("artistId") is not None
            and dicc.get("collectionId") is not None
            and dicc.get("trackId") is not None
        )
    except (KeyError, TypeError):
        return False


def validar_respuesta_itunes(dicc: dict) -> RespuestaItunes:
    """
    Valida un diccionario de iTunes usando Pydantic.
    Lanza ValueError con detalle si el formato es incorrecto.
    """
    from pydantic import ValidationError
    try:
        return RespuestaItunes(**dicc)
    except ValidationError as e:
        raise ValueError(f"Respuesta iTunes inválida: {e}") from e


def obtener_mejor_diccionario(lista: List[dict], titulo_referencia: str, artista_referencia: str) -> dict:
    """
    Evalúa una lista de resultados iTunes y retorna el más adecuado.

    Criterios (suma de puntos):
    - Artista más frecuente en la lista: +5
    - Título de canción más frecuente: +10
    - Fecha de lanzamiento más antigua (original): +40
    - Completitud de campos: +0 a +85 (según _puntaje_completitud)
    - Similitud con la referencia: +0 a +50
    - Penalización si es compilación: -30
    """
    if not lista:
        return {}

    # Filtrar los que no cumplen mínimos
    candidatos = [d for d in lista if propiedades_minimas(d)]
    if not candidatos:
        return {}

    artistas = [d.get("artistName", "") for d in candidatos]
    canciones = [d.get("trackName", "") for d in candidatos]
    fechas = [d.get("releaseDate", "") for d in candidatos]

    moda_artista = Counter(artistas + [artista_referencia]).most_common(1)[0][0]
    moda_cancion = Counter(canciones).most_common(1)[0][0]
    fecha_minima = min(f for f in fechas if f)

    puntajes: dict[int, float] = {}

    for dicc in candidatos:
        cid = dicc["collectionId"]
        puntaje = 0.0

        if dicc.get("artistName") == moda_artista:
            puntaje += 5
        if dicc.get("trackName") == moda_cancion:
            puntaje += 10
        if dicc.get("releaseDate") == fecha_minima:
            puntaje += 40

        # Sumar completitud
        puntaje += _puntaje_completitud(dicc) * 85

        # Similitudes del titulo
        titulo_cancion = dicc.get("trackName")
        if titulo_cancion:
            puntaje += _puntaje_similitud(
                palabra_referencia=titulo_referencia, 
                palabra=titulo_cancion
                ) * 50

        # Penalizar compilaciones
        if es_compilacion(dicc):
            puntaje -= 30

        puntajes[cid] = puntaje

    mejor_id = max(puntajes, key=lambda k: puntajes[k])
    return next(d for d in candidatos if d["collectionId"] == mejor_id)
