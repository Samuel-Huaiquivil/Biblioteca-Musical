# processing/caratulas.py
from pathlib import Path
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from collections import Counter

from models.schemas_adapter import AdaptadorMBZ, NormalizadorItunes, NormalizadorMBZ
from models.schemas_itunes_v5 import RespuestaItunes
from models.schemas_mbz import RespuestaMbz
from models.schemas_motor import MotorPuntuador, DatosLote, ItemNormalizado

from models.schemas_v5 import PaqueteDatos
from processing.imagenes import descargar_estandar_itunes, descargar_estandar_mbz, get_url, guardar_bytes_imagen
from utils.errores import ErrorAPI, ErrorArchivo, ErrorConsulta, ErrorCoverArchive
from utils.logging_class import PipelineLog

logger = PipelineLog(__name__)

def truncar_msg(msg: str, max_len=80) -> str:
    return msg if len(msg) <= max_len else msg[:max_len] + "..."

_PALABRAS_COMPILACION = [
    "hits", "gran", "exitos", "éxitos", "colec", "definitiva",
    "edici", "mejor", "canciones", "edition", "songs",
    "best of", "collection", "definitive", "essential",
    "vol."
]

def crear_lote(items: List[ItemNormalizado], art: str = "", tit: str = "", prioridad: int = 3) -> DatosLote:
    '''
    prioridad: Valor del 1 - 10 que indica la prioridad que se le da a los parametros de artista y titulo. 1-> Máxima, 10-> Mínima.
    '''

    artistas = []
    titulos = []
    fec = []

    valor = prioridad % 10
    # Adicional para establecer referencia
    num = len(items) // valor
    if num:
        for i in range(0, num):
            artistas.append(art)
            titulos.append(tit)

    for item in items:
        artistas.append(item.artista_principal or "")
        titulos.append(item.titulo_album or "")
        fec.append(item.lanzamiento or "")
    
    moda_artista = Counter(artistas).most_common(1)[0][0]
    moda_titulo = Counter(titulos).most_common(1)[0][0]
    fecha_minima = min(f for f in fec if f)

    if not moda_artista or not moda_titulo or not fecha_minima:
        return DatosLote()
    
    return DatosLote(
        moda_tit=moda_titulo,
        moda_art=moda_artista,
        fecha_min=fecha_minima
    )


# =================================
# Validadores y Reglas 
# =================================

def _validar_datos_minimos(item: ItemNormalizado) -> bool:
    return bool(
        item.artista_principal
        and item.titulo_album
        and item.codigo_album
    )

def _es_compilacion(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    nombre = item.titulo_album.lower()
    artista = item.artista_principal.lower()
    palabras = _PALABRAS_COMPILACION + [artista]
    if any(p in nombre for p in palabras):
        return "Es compilación", 0
    else:
        return "No es Compilacion", 0.2

def _artista_moda(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    art_ref = dts_lote.moda_art
    artista = item.artista_principal
    ptje = SequenceMatcher(None, art_ref, artista).quick_ratio()
    return "Artista Moda", ptje * 0.3 

def _titulo_moda(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    tit_ref = dts_lote.moda_tit
    titulo = item.titulo_album
    ptje = SequenceMatcher(None, tit_ref, titulo).quick_ratio()
    return "Titulo Moda", ptje * 0.3

def _fecha_lanzamiento(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    f_min = dts_lote.fecha_min
    if not f_min:
        return "Sin Fecha", 0
    lanz = item.lanzamiento or "9999-99-99"
    if f_min[:4] == lanz[:4]:
        return f"Primer Lanzamiento ({f_min[:4]})", 0.1
    else:
        return "Lanzamiento Posterior", 0

def _puntaje_referencia(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    ptje = item.ptje_referencia
    return f"Puntaje Referencia {ptje}", ptje * 0.09

def _varios_artistas(item:ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    art_album = item.artista_principal
    if "various artists" in art_album.lower():
        return f"Compilacion Varios Artistas", 0.0
    else:
        return "Album de Artista", 0.05

def _artista_moda_mbz(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    art_ref = dts_lote.moda_art
    artista = item.artista_principal
    ptje = SequenceMatcher(None, art_ref, artista).quick_ratio()
    return "Artista Moda", ptje * 0.3

def _titulo_moda_mbz(item: ItemNormalizado, dts_lote: DatosLote) -> Tuple[str, float]:
    tit_ref = dts_lote.moda_tit
    titulo = item.titulo_album
    ptje = SequenceMatcher(None, tit_ref, titulo).quick_ratio()
    return "Titulo Moda", ptje * 0.2


Validadores = [
    _validar_datos_minimos
]

reglas_itunes = [
    _es_compilacion,
    _artista_moda,
    _titulo_moda,
    _fecha_lanzamiento
]

reglas_mbz = [
    _fecha_lanzamiento,
    _puntaje_referencia,
    _varios_artistas,
    _titulo_moda_mbz,
    _artista_moda_mbz
]



# =================================
# Normalizar
# =================================


def normalizar_item_itunes(item: dict) -> ItemNormalizado:
    titulo = item.get("collectionName") or item.get("trackName") or ""
    lanzamiento = item.get("releaseDate", "")
    artista = item.get("collectionArtistName") or item.get("artistName") or ""
    codigo = item.get("collectionId") or item.get("trackId") or ""
    url = (
        item.get("artworkUrl100")
        or item.get("artworkUrl60")
        or item.get("artworkUrl30")
        or ""
    )
    return ItemNormalizado(
        titulo_album=titulo,
        lanzamiento=lanzamiento,
        artista_principal=artista,
        codigo_album=str(codigo),
        url_descarga=url
    )


def normalizar_item_mbz(item: dict) -> ItemNormalizado:
    titulo = item.get("title", "")
    if item.get("disambiguation"):
        titulo = f"{titulo} {item.get('disambiguation')}".strip()
    lanzamiento = item.get("date") or item.get("release_date", "")
    artista = ""
    artist_credit = item.get("artist-credit") or item.get("artist_credit")
    if isinstance(artist_credit, list) and artist_credit:
        primer = artist_credit[0]
        if isinstance(primer, dict):
            artista = primer.get("name") or primer.get("artist", {}).get("name", "")
    artista = artista or item.get("artist") or item.get("artistName") or ""
    codigo = item.get("id", "")
    url = item.get("url", "") or ""
    return ItemNormalizado(
        titulo_album=titulo,
        lanzamiento=lanzamiento,
        artista_principal=artista,
        codigo_album=str(codigo),
        url_descarga=url
    )


# =================================
# PIPELINES PÚBLICOS
# =================================


def pipeline_caratulas_itunes(
        lista_dicc: List[dict],
        artista: str,
        titulo: str,
        ruta_imagenes: Path
    ) -> Tuple[Path, ItemNormalizado]:
    '''
    Gestiona las carátulas
    '''
    logger.proceso("Descarga de Carátulas")

    lista_items = []
    lista_tuplas = []

    normalizador = NormalizadorItunes()

    for dicc in lista_dicc:
        modelo = RespuestaItunes.model_validate(dicc)
        item = normalizador.normalizar(modelo)
        lista_items.append(item)
        lista_tuplas.append((item, modelo))

    logger.debug(f"Elementos validados: [{len(lista_items)}]")

    motor = MotorPuntuador(
        validadores=Validadores,
        reglas=reglas_itunes
    )

    lote_datos = crear_lote(lista_items, artista, titulo)

    res, des = motor.puntuar(lista_items, lote_datos)

    count = 0

    for r in res:
        count += 1
        alb_tit = truncar_msg(r.item.titulo_album, 40)
        try:
            logger.debug(f"Intento N° {count}. '{alb_tit}'." )
            url = r.obtener_url()
            img_bytes = descargar_estandar_itunes(url)
            img = guardar_bytes_imagen(img_bytes, r.item.codigo_album, ruta_imagenes)
            return (img, r.item)
        except Exception as e:
            logger.debug(
                f"No se pudo obtener la carátula. Detalles: {str(e)}.",
            )


    logger.warning(
        "No se obtuvo una carátula válida desde iTunes.",
        extra={
            "Diccionarios Entrada": len(lista_dicc),
            "Elementos Validados": len(lista_items),
            "Descartados": [d.to_dict() for d in des],
            "Validados": [r.to_dict() for r in res]
        }
    )

    raise ErrorAPI(
        "No se pudo obtener una carátula válida desde iTunes."
    )

def pipeline_caratulas_mbz(
        lista_dicc: List[dict],
        artista: str,
        titulo: str,
        ruta_imagenes: Path
    ) -> Tuple[Path, ItemNormalizado]:
    '''
    Gestiona las carátulas
    '''
    logger.proceso("Descarga de Carátulas")

    lista_items: List[ItemNormalizado] = []

    normalizador = NormalizadorMBZ()

    for dicc in lista_dicc:
        modelo = RespuestaMbz.model_validate(dicc)
        l_item = normalizador.normalizar(modelo)
        lista_items.extend(l_item)

    logger.debug(f"Elementos validados: [{len(lista_items)}]")
    
    motor = MotorPuntuador(
        validadores=Validadores,
        reglas=reglas_mbz
    )

    lote_datos = crear_lote(lista_items, artista, titulo, 1)

    res, des = motor.puntuar(lista_items, lote_datos)

    count = 0

    for r in res:
        count += 1
        alb_tit = truncar_msg(r.item.titulo_album, 40)
        try:
            logger.debug(f"Intento N° {count}. '{alb_tit}'." )
            url = r.obtener_url()
            resp = get_url(url)
            datos = resp.json()
            imagenes = datos.get("images", [])

            img_bytes = descargar_estandar_mbz(imagenes)

            ruta_salida =  guardar_bytes_imagen(img_bytes, r.item.codigo_album, ruta_imagenes)

            return (ruta_salida, r.item)

        except ErrorAPI as eap:
            logger.debug(
                str(eap) + " Detalles: " + str(eap.data),
            )

        except ErrorArchivo as ea:
            logger.debug(
                str(ea) + " Detalles: " + str(ea.data)
            )

        except Exception as e:
            logger.debug(
                f"Error no registrado: {str(e)}"
            )

    logger.warning(
        "No se obtuvo una carátula válida desde Cover Archive.",
        extra={
            "Diccionarios Entrada": len(lista_dicc),
            "Elementos Validados": len(lista_items),
            "Descartados": [d.to_dict() for d in des],
            "Validados": [r.to_dict() for r in res]
        }
    )

    raise ErrorAPI(
        "No se pudo obtener una carátula válida desde Cover Archive."
    )

        

