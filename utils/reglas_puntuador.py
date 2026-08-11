from typing import Tuple
from difflib import SequenceMatcher

from models.schemas_adapter import ItemNormalizado
from models.schemas_motor import DatosLote

_PESOS_REFERENCE = {
    "artista": 4,
    "titulo": 2,
    "fecha": 3,
    "otros": 1
}

_SUMA_PESO = sum(_PESOS_REFERENCE.values())

_PESO_TYPE: dict[str, float] = {
    "ART": _PESOS_REFERENCE["artista"] / _SUMA_PESO,
    "TIT": _PESOS_REFERENCE["titulo"] / _SUMA_PESO,
    "FEC": _PESOS_REFERENCE["fecha"] / _SUMA_PESO,
    "OTR": _PESOS_REFERENCE["otros"] / _SUMA_PESO
}

_PALABRAS_COMPILACION = [
    "hits", "gran", "exitos", "éxitos", "colec", "definitiva",
    "edici", "mejor", "canciones", "edition", "songs",
    "best of", "collection", "definitive", "essential",
    "vol."
]

_PENALIZACIONES = {
    "compilation": -0.30,
    "greatest_hits": -0.30,
    "live": -0.40,
    "remaster": -0.15,
    "deluxe": -0.15,
    "anniversary": -0.15,
    "expanded": -0.10,
}

_PUNTAJE = Tuple[str, float]

# ============
# VALIDADORES
# ============

def _validar_datos_minimos(item: ItemNormalizado) -> bool:
    return bool(
        item.artista_principal
        and item.titulo_album
        and item.codigo_album
    )

# ============
# REGLAS
# ============

def _tiene_al_artista(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    if item.artista_principal in dts_lote.moda_art:
        return "Tiene el artista", 1 * _PESO_TYPE["ART"]
    else:
        return "No tiene al artista", 0

def _es_compilacion_itunes(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    nombre = item.titulo_album.lower()
    artista = item.artista_principal.lower()
    palabras = _PALABRAS_COMPILACION + [artista]
    if any(p in nombre for p in palabras):
        return "Es compilación", 0
    else:
        return "No es Compilacion", 1 * _PESO_TYPE["TIT"]

def _artista_moda(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    art_ref = dts_lote.moda_art
    artista = item.artista_principal
    ptje = SequenceMatcher(None, art_ref, artista).quick_ratio()
    return "Artista Moda", ptje * _PESO_TYPE["ART"]

def _titulo_moda(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    tit_ref = dts_lote.moda_tit
    titulo = item.titulo_album
    ptje = SequenceMatcher(None, tit_ref, titulo).quick_ratio()
    return "Titulo Moda", ptje * _PESO_TYPE["TIT"]

def _fecha_lanzamiento(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    try:
        f_min = int(dts_lote.fecha_min[:4])
        lanz = int(item.lanzamiento[:4] or 9999)
        diff = lanz - f_min
        ptje = 1 / (1 + diff)
        return f"Fecha. Año: {lanz}", ptje * _PESO_TYPE["FEC"]
    except ValueError:
        return "Sin Fecha", 0

def _puntaje_referencia(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    ptje = item.ptje_referencia
    return f"Puntaje Referencia {ptje}", ptje * _PESO_TYPE["ART"]

def _varios_artistas(item:ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    art_album = item.artista_principal
    if "various artists" in art_album.lower():
        return f"Compilacion Varios Artistas", 0.0
    else:
        return "Album de Artista", 1 * _PESO_TYPE["ART"]

def _penalizacion_version(item: ItemNormalizado, dts_lote: DatosLote) -> _PUNTAJE:
    ver = item.titulo_version
    if not ver:
        return "Sin Version.", 0
    for k, v in _PENALIZACIONES.items():
        if k in ver:
            return f"Castigo: {k}", v * _PESO_TYPE["OTR"]
    return "Sin Penalizacion", 0


validadores = [
    _validar_datos_minimos
]

reglas_itunes = [
    _artista_moda,
    _titulo_moda,
    _fecha_lanzamiento,
    _penalizacion_version,
    _tiene_al_artista,
    _es_compilacion_itunes
]

reglas_mbz = [
    _fecha_lanzamiento,
    _titulo_moda,
    _artista_moda,
    _puntaje_referencia,
    _tiene_al_artista,
    _varios_artistas
]

