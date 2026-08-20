from typing import List, Any
from pathlib import Path

from pydantic import ValidationError

from database.repository_v5 import pipeline_insertar_paquete
from database.ident import obt_ins_identificador
from models.schemas_adapter import AdaptadorItunes
from models.schemas_itunes_v5 import RespuestaItunes
from utils.errores import ErrorBaseDatos
from utils.logging_class import PipelineLog

logger = PipelineLog(__name__)

def procesar_respuestas_itunes(lista_respuesta: List[Any], base_datos: Path | None = None):
    "Procesa una lista de elementos en itunes"

    logger.proceso("Respuesta Itunes")

    logger.info(f"Procesando {len(lista_respuesta)} elemento(s).")

    errores = 0
    cont = 0

    for respuesta in lista_respuesta:
        try:
            #Validación externa:
            clase_externa = RespuestaItunes.model_validate(respuesta)

            adaptador = AdaptadorItunes()

            paquete = None

            info_extra = ""
            # Transformación
            if clase_externa.es_single():
                #Convertidor Singles
                info_extra = "Transformación Álbum Single"
                paquete = adaptador.convertir_album_single(clase_externa)

            elif clase_externa.es_extended():
                #Convertir Respectivamente
                info_extra = "Tranformación Album Extended"
                paquete = adaptador.convertir_album_extend(clase_externa)

            elif clase_externa.tiene_multiples_artistas():
                # Parsear Artistas
                info_extra = "Transformación Canción Multiples Artistas."
                paquete = adaptador.convertir_mult_artistas(clase_externa)

            else:
                # Conversión Regular
                info_extra = "Transformación Canción Regular"
                paquete = adaptador.convertir_art_simple(clase_externa)

            if paquete:
                cont += 1
                # Insertar en la base de Datos
                ident = clase_externa.ident()
                ident_id = obt_ins_identificador(ident, base_datos)
                logger.debug(f"Insertando Paquete N° {cont} | {info_extra}")
                pipeline_insertar_paquete(
                    paquete_datos=paquete,
                    codigo_ident=ident_id,
                    ruta_base_datos=base_datos
                    )
            else:
                # Posible error de transformación
                raise ValueError("Error con la transformación")

        except ValidationError as ve:
            logger.warning(
                "Error al validar elemento",
                extra={
                    "elemento_id": respuesta.get("trackId", "SN"),
                    "errores_validacion": ve.errors(),
                }
            )
            errores += 1
            continue
        except ErrorBaseDatos as db:
            logger.error(
                "Error con la Base de Datos",
                extra={
                    "Detalles": str(db)
                }
            )
        except Exception as e:
            logger.error(
                "Error no Registrado.",
                extra={
                    "Detalles": str(e)
                }
            )
            errores += 1
            continue

    msg_final = f"Proceso terminado. Elementos Procesados: [{cont}]"
    if errores:
        msg_final += f". N° Errores: [{errores}]"
    msg_final += "."
    logger.info(msg_final)
