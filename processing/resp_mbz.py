from pathlib import Path
from typing import Any, List

from pydantic import ValidationError

from database.ident import obt_ins_identificador
from database.repository_v5 import pipeline_insertar_paquete, pipeline_insertar_paquete_lista
from models.schemas_adapter import AdaptadorMBZ
from models.schemas_mbz import RespuestaMbz
from models.schemas_v5 import Ident
from utils.errores import ErrorBaseDatos
from utils.logging_class import PipelineLog

logger = PipelineLog(__name__)

def procesar_respuesta_mbz(lista_respuesta: List[Any], base_datos: Path | None = None):
    "Procesa las respuestas de MusicBrainz"
    logger.proceso("Respuesta Itunes")
    logger.info(f"Procesando {len(lista_respuesta)} elemento(s).")
    count = 0
    errores = 0
    glb = Ident(api="MusicBrainz", region="Global", id=0)
    grp = Ident(api="MusicBrainz", region="Groups", id=0)
    id_grp = obt_ins_identificador(grp, base_datos)
    id_glb = obt_ins_identificador(glb, base_datos)
    for respuesta in lista_respuesta:
        try:
            clase_externa = RespuestaMbz.model_validate(respuesta)

            adaptador = AdaptadorMBZ()

            lista_paq_1 = adaptador.conv_respuesta_global(clase_externa)
            lista_paq_2 = adaptador.conv_respuesta_grupo(clase_externa)

            for paq in lista_paq_1:
                pipeline_insertar_paquete(
                    paquete_datos=paq,
                    codigo_ident=id_glb,
                    ruta_base_datos=base_datos
                )
                count += 1
            pipeline_insertar_paquete_lista(
                lista_paquetes=lista_paq_2,
                codigo_ident=id_grp,
                ruta_base_datos=base_datos,
                vincular=False
            )
            count += len(lista_paq_2)
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