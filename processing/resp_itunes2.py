from sqlite3 import DatabaseError
from typing import List, Any
from pydantic import ValidationError
from pathlib import Path

from database.gestion_db import pipeline_insertar_paquete
from models.schemas_adapter import AdaptadorItunes
from models.schemas_itunes import RespuestaItunes

def procesar_respuestas_itunes(lista_respuesta: List[Any], base_datos: Path | None = None):
    "Procesa una lista de elementos en itunes"
    for respuesta in lista_respuesta:
        try:
            #Validación externa:
            clase_externa = RespuestaItunes.model_validate(respuesta)

            adaptador = AdaptadorItunes()

            paquete = None
            # Transformación
            if clase_externa.es_album_single():
                #Convertidor Singles
                paquete = adaptador.convertir_album_single(clase_externa)

            elif clase_externa.tiene_multiples_artistas():
                # Parsear Artistas
                paquete = adaptador.convertir_mult_artistas(clase_externa)

            else:
                # Conversión Regular
                paquete = adaptador.convertir_art_simple(clase_externa)

            if paquete:
                # Insertar en la base de Datos
                pipeline_insertar_paquete(
                    paquete_datos=paquete,
                    ruta_base_datos=base_datos
                    )
            else:
                # Posible error de transformación
                continue

        except ValidationError as ve:
            pass

        except DatabaseError as db:
            pass

        except Exception as e:
            pass
