# processing/caratulas.py
from pathlib import Path
from typing import List, Tuple

from collections import Counter

from models.schemas_adapter import AdaptadorItunes, AdaptadorMBZ, NormalizadorItunes, NormalizadorMBZ
from models.schemas_itunes_v5 import RespuestaItunes
from models.schemas_mbz import RespuestaMbz
from models.schemas_motor import MotorPuntuador, DatosLote, ItemNormalizado
from models.schemas_v5 import PaqueteDatos
from utils.errores import ErrorAPI, ErrorArchivo
from utils.logging_class import PipelineLog

from api.itunes import descargar_caratula_itunes
from api.coverarchive import descargar_caratula_coverarchive, get_url
from utils.gestion_archivos import guardar_bytes_imagen
from utils.reglas_puntuador import validadores, reglas_itunes, reglas_mbz

logger = PipelineLog(__name__)

# =================================
# FUNCIONES AUXILIARES
# =================================

def _truncar_msg(msg: str, max_len=80) -> str:
    return msg if len(msg) <= max_len else msg[:max_len] + "..."


def _crear_lote(items: List[ItemNormalizado], art: str = "", tit: str = "", prioridad: int = 3) -> DatosLote:
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


def _item_to_paquete_itunes(item_norm: ItemNormalizado, modelos: List[RespuestaItunes]) -> PaqueteDatos:
    "Transforma un item normalizado a su modelo orginal y luego a un paquete datos"
    if not modelos:
        raise ValueError("No se ingresaron los modelos")
    
    codigo_alb = item_norm.codigo_album
    resp_itunes = modelos[0]

    for modelo in modelos:
        id_alb = modelo.collectionId
        if codigo_alb == id_alb:
            resp_itunes = modelo
            break

    adaptador = AdaptadorItunes()

    paq = None
    
    if resp_itunes.es_single():
        paq = adaptador.convertir_album_single(resp_itunes)

    elif resp_itunes.es_extended():
        paq = adaptador.convertir_album_extend(resp_itunes)

    elif resp_itunes.tiene_multiples_artistas():
        paq = adaptador.convertir_mult_artistas(resp_itunes)

    else:
        paq = adaptador.convertir_art_simple(resp_itunes)

    if not paq:
        raise ValueError("No se pudo transformar los datos")

    return paq


# =================================
# PIPELINES PÚBLICOS
# =================================


def pipeline_caratulas_itunes(
        lista_dicc: List[dict],
        artista: str,
        titulo: str,
        ruta_imagenes: Path
    ) -> Tuple[Path, PaqueteDatos]:
    '''
    Gestiona las carátulas
    '''
    logger.proceso("Descarga de Carátulas")

    lista_items: List[ItemNormalizado] = []
    lista_modelos: List[RespuestaItunes] = []

    normalizador = NormalizadorItunes()

    for dicc in lista_dicc:
        modelo = RespuestaItunes.model_validate(dicc)
        item = normalizador.normalizar(modelo)

        lista_modelos.append(modelo)
        lista_items.append(item)

    logger.debug(f"Elementos validados: [{len(lista_items)}]")

    motor = MotorPuntuador(
        validadores=validadores,
        reglas=reglas_itunes
    )

    lote_datos = _crear_lote(lista_items, artista, titulo)

    res, des = motor.puntuar(lista_items, lote_datos)

    count = 0

    for r in res:
        count += 1
        alb_tit = _truncar_msg(r.item.titulo_album, 40)
        try:
            logger.debug(f"Intento N° {count}. '{alb_tit}'." )
            url = r.obtener_url()
            img_bytes = descargar_caratula_itunes(url)
            img = guardar_bytes_imagen(img_bytes, r.item.codigo_album, ruta_imagenes)

            paq = _item_to_paquete_itunes(r.item, lista_modelos)
            
            return (img, paq)
        except Exception as e:
            logger.debug(
                f"No se pudo obtener la carátula. Detalles: {str(e)}.",
            )
            continue

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
    ) -> Tuple[Path, PaqueteDatos]:
    '''
    Gestiona las carátulas
    '''
    logger.proceso("Descarga de Carátulas")

    lista_items: List[ItemNormalizado] = []
    lista_paquetes: List[PaqueteDatos] = []
    
    normalizador = NormalizadorMBZ()
    adaptador = AdaptadorMBZ()

    for dicc in lista_dicc:
        modelo = RespuestaMbz.model_validate(dicc)

        paquetes = adaptador.conv_respuesta_global(modelo, False)
        l_item = normalizador.normalizar(modelo)

        lista_paquetes.extend(paquetes)
        lista_items.extend(l_item)

    logger.debug(f"Elementos validados: [{len(lista_items)}]")
    
    motor = MotorPuntuador(
        validadores=validadores,
        reglas=reglas_mbz
    )

    lote_datos = _crear_lote(lista_items, artista, titulo, 1)

    res, des = motor.puntuar(lista_items, lote_datos)

    count = 0

    for r in res:
        count += 1
        alb_tit = _truncar_msg(r.item.titulo_album, 40)
        try:
            logger.debug(f"Intento N° {count}. '{alb_tit}'." )
            url = r.obtener_url()
            resp = get_url(url)
            datos = resp.json()
            imagenes = datos.get("images", [])

            img_bytes = descargar_caratula_coverarchive(imagenes)

            ruta_salida =  guardar_bytes_imagen(img_bytes, r.item.codigo_album, ruta_imagenes)

            paquete = None
            for paq in lista_paquetes:
                if r.item.comparar_paquete(paq):
                   paquete = paq 

            if paquete:
                return (ruta_salida, paquete)
            else:
                continue

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

        

