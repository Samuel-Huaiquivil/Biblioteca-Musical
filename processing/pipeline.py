import logging
import json
from pathlib import Path
from processing.resp_mbz import procesar_respuesta_mbz
from utils.logging_class import PipelineLog
from processing.resp_itunes import procesar_respuestas_itunes
from test.API.info_cancion import resultados_mixtos_error
from processing.caratulas import pipeline_caratulas_mbz

logger = PipelineLog.get_logger(__name__)

r_img = Path("C:\\Users\\MSI\\Proyectos Personales\\Nueva carpeta\\control\\Caratulas")

def pipeline_modelo():
    "Pipeline script"
    logger.info("Iniciando pipeline")
    with open("archivo.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
    procesar_respuesta_mbz(datos["recordings"])
    try:
        img = pipeline_caratulas_mbz(
        datos["recordings"],
        "Queen",
        "Under Pressure",
        r_img
        )
        print(img)
    except Exception as e:
        logger.error(
            str(e)
        )
    

    
