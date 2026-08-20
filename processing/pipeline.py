from pathlib import Path

from database.init_db import iniciar_base_datos
from database.busqueda import busqueda_paquete_local
from processing.local import busqueda_datos_locales
from processing.mutagen import pipeline_mutagen
from processing.resp_mbz import procesar_respuesta_mbz
from utils.logging_class import PipelineLog

from config.setup import preparar_entorno
from utils.gestion_archivos import listar_imagenes, listar_mp3, mover_y_renombrar_cancion, obtener_datos_cancion
from api.itunes import busqueda_itunes_por_nivel
from api.musicbrainz import buscar_cancion_mbz
from processing.resp_itunes import procesar_respuestas_itunes
from processing.caratulas import pipeline_caratulas_itunes, pipeline_caratulas_mbz

def pipeline_principal(
        ruta_carpeta: Path,
        cantidad_busq: int = 1,
        nivel_busqueda: int = 2,
        mover_archivos: bool = True
):
    "Pipeline script"
    archivos_entorno = preparar_entorno(ruta_carpeta)

    ruta_base_datos = archivos_entorno["base_datos"]
    car_errores = archivos_entorno["errores"]
    car_caratulas = archivos_entorno["caratulas"]
    car_destino = archivos_entorno["destino"]

    iniciar_base_datos(ruta_base_datos)

    PipelineLog.setup(car_errores)

    logger = PipelineLog(__name__)
    logger.etapa_inicio("Búsqueda de Archivos Musicales")
    errores_totales = 0

    lista_archivos_mp3 = listar_mp3(ruta=ruta_carpeta, cantidad=cantidad_busq)
    lista_imagenes_caratula = listar_imagenes(ruta=car_caratulas, recursivo=True)

    for archivo_mp3 in lista_archivos_mp3:

        logger.info(f"Procesando: {archivo_mp3}")

        ruta_mp3 = archivo_mp3
        datos_cancion = obtener_datos_cancion(ruta=ruta_mp3)
        titulo_cancion = datos_cancion["tit"]
        artista_cancion = datos_cancion["art"]

        if not titulo_cancion or not artista_cancion:
            logger.error(
                "No se pudo obtener los datos de la canción.",
                extra={
                    "archivo": archivo_mp3,
                    "ruta absoluta": str(ruta_mp3),
                    "artista": artista_cancion,
                    "titulo": titulo_cancion
                }
            )
            errores_totales += 1
            continue

        logger.proceso("Búsqueda en Base Datos Local.")

        paquete, ruta_caratula = busqueda_datos_locales(
            artista=artista_cancion,
            titulo=titulo_cancion,
            lista_caratulas=lista_imagenes_caratula,
            base_datos=ruta_base_datos
        )

        if not paquete:
            logger.etapa_inicio("Busqueda iTunes")
            try:
                res_busq = busqueda_itunes_por_nivel(
                    nombre_artista=artista_cancion,
                    titulo_cancion=titulo_cancion,
                    nivel=nivel_busqueda,
                    region="Estados Unidos"
                )

                procesar_respuestas_itunes(
                    lista_respuesta=res_busq.todas_las_canciones(),
                    base_datos=ruta_base_datos
                )

                ruta_caratula, paquete = pipeline_caratulas_itunes(
                    lista_dicc=res_busq.cancion_principal,
                    artista=artista_cancion,
                    titulo=titulo_cancion,
                    ruta_imagenes=car_caratulas
                )

            except Exception as e:
                logger.error(
                    "Error durante el proceso iTunes.",
                    extra={
                        "Detalles": {e}
                    }
                )
                errores_totales += 1
                pass

        if not ruta_caratula:
            limite_busq: int = 5
            if not paquete:
                limite_busq += 10
            logger.etapa_inicio("Búsqueda MusicBrainz")
            try:
                res_busq = buscar_cancion_mbz(
                    titulo=titulo_cancion,
                    artista=artista_cancion,
                    limite=limite_busq
                )

                procesar_respuesta_mbz(
                    lista_respuesta=res_busq,
                    base_datos=ruta_base_datos
                )

                ruta_caratula, paquete = pipeline_caratulas_mbz(
                    lista_dicc=res_busq,
                    artista=artista_cancion,
                    titulo=titulo_cancion,
                    ruta_imagenes=car_caratulas
                )

            except Exception as e:
                logger.error(
                    "Error durante el proceso MusicBrainz.",
                    extra={
                        "Detalles": {e}
                    }
                )
                errores_totales += 1
                pass

        logger.etapa_final("Busqueda en APIs")

        if not ruta_caratula:
            logger.error(
                "No se pudo obtener la carátula del álbum."
            )
            errores_totales += 1
            pass

        if not paquete:
            logger.error(
                "No se pudo obtener propiedades de la canción."
            )
            errores_totales += 1
            continue

        try:
            ruta = pipeline_mutagen(
                ruta_mp3=ruta_mp3,
                paquete=paquete,
                ruta_img=ruta_caratula
            )

        except Exception as e:
            logger.error(
                "No se pudo insertar los metadatos al archivo.",
                extra={
                    "Detalles": str(e)
                }
            )
            errores_totales += 1
            continue

        mover_y_renombrar_cancion(
            ruta_cancion=ruta,
            ruta_destino=car_destino if mover_archivos else None,
            renombrar=True
        )

    logger.etapa_final("Etapa Script")
