from pathlib import Path
from typing import Any, List

from pydantic import ValidationError

from database.ident import obtener_ident_mbz
from database.repository_v5 import pipeline_insertar_paquete
from models.schemas_adapter import AdaptadorMBZ
from models.schemas_mbz import RespuestaMbz
from utils.errores import ErrorBaseDatos
from utils.logging_class import PipelineLog

logger = PipelineLog(__name__)

def procesar_respuesta_mbz(lista_respuesta: List[Any], base_datos: Path | None = None):
    "Procesa las respuestas de MusicBrainz"
    logger.proceso("Respuesta Itunes")
    logger.info(f"Procesando {len(lista_respuesta)} elemento(s).")
    count, errores = 0, 0
    id_glb, id_grp = obtener_ident_mbz(base_datos=base_datos)
    
    for respuesta in lista_respuesta:
        try:
            clase_externa = RespuestaMbz.model_validate(respuesta)

            adaptador = AdaptadorMBZ()

            lista_paq_global = adaptador.conv_respuesta_global(clase_externa)
            lista_paq_grupo = adaptador.conv_respuesta_grupo(clase_externa)

            for paq in lista_paq_global:
                pipeline_insertar_paquete(
                    paquete_datos=paq,
                    codigo_ident=id_glb,
                    ruta_base_datos=base_datos
                )
                count += 1

            for paq in lista_paq_grupo:
                pipeline_insertar_paquete(
                    paquete_datos=paq,
                    codigo_ident=id_grp,
                    ruta_base_datos=base_datos
                )
                count += 1

        except ValidationError as ve:
            logger.error(
                "Error al validar elemento",
                extra={
                    "elemento_id": respuesta.get("id", "SN"),
                    "errores_validacion": ve.errors(),
                }
            )
        except ErrorBaseDatos as db:
            logger.error(
                "Error en la base de datos",
                extra={
                    "detalles": db
                }
            )
            errores += 1
        except Exception as identifier:
            raise ValueError(f"{identifier}")
    msg_final = f"Proceso terminado. Elementos Procesados: [{count}]"
    if errores:
        msg_final += f". N° Errores: [{errores}]"
    msg_final += "."
    logger.info(msg_final)
    return