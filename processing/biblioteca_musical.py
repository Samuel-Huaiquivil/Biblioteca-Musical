# Gestión Principal

from pathlib import Path
import logging

from api import musicbrainz
from api.caratulas import obtener_caratula
from api.gestion_itunes import busqueda_itunes_por_nivel
from config.setup import preparar_entorno
from database.gestion_db import creacion_de_clases
from database.init_db import iniciar_base_datos
from processing.id3 import escribir_caratula, escribir_tags, modelos_a_datos_musica
from processing.resp_itunes import revisar_diccionario
from utils import dicc_a_clases_mbz, errores
from database import repository
from utils.caratulas import descargar_caratula, guardar_imagen_bytes
from utils.dicc_a_clases import convertir_a_datos_caratula
from utils.listar_mp3 import listar_elementos_ruta
from utils.mover_archivo import mover_y_renombrar_cancion
from utils.obtener_datos_cancion import obtener_datos_cancion
from utils.poderador import obtener_mejor_diccionario, validar_respuesta_itunes
from utils.error_analyzer import ErrorAnalyzer
from utils.pipeline_logging import PipelineLogger
from utils.validacion_datos import ValidadorDatos


def _registrar_error(ruta_log: Path, mensaje: str) -> None:
    """[Deprecated] Usa PipelineLogger en su lugar. Mantenido para compatibilidad."""
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")


def procesar_canciones(
        ruta_principal: Path,
        nivel_busqueda: int = 2, 
        numero_canciones: int = 0,
        caratulas_mejoradas: bool = False,
        descargar_caratulas: bool = False,
        mover_canciones: bool = False
    ):
    "Pipeline mejorado para procesar las canciones de la biblioteca"
    rutas = preparar_entorno(ruta_principal=ruta_principal)
    log = rutas["log"]
    ruta_db = rutas["base_datos"]
    rutas_caratulas = rutas["img"]
    ruta_musica = rutas["musica"]
    carpeta_errores = rutas["error"]
    
    # Inicializar logging mejorado
    logger = PipelineLogger(log)
    error_analyzer = ErrorAnalyzer(carpeta_errores / "errores_detallados.json")
    validador = ValidadorDatos()

    iniciar_base_datos(ruta_db)
    
    lista_archivos_musica = listar_elementos_ruta(ruta=ruta_principal, cantidad=numero_canciones)
    
    logger.inicio_procesamiento(len(lista_archivos_musica))
    
    total_errores = 0
    
    for nombre_archivo in lista_archivos_musica:
        ruta_cancion = ruta_principal / nombre_archivo
        
        try:
            datos = obtener_datos_cancion(ruta_cancion)
        except errores.ErrorArchivo as e:
            logger.error(f"[ARCHIVO] {e}", archivo=nombre_archivo, excepcion=e)
            total_errores += 1
            continue
        
        titulo = datos["tit"]
        artista = datos["art"]
        
        if not titulo or not artista:
            logger.error(
                f"No se pudo obtener título/artista",
                archivo=nombre_archivo
            )
            total_errores += 1
            continue

        base_local = None
        try:
            base_local = repository.busqueda_avanzada(titulo=titulo, artista=artista, db=ruta_db)
        except errores.ErrorBaseDatos as e:
            logger.error(
                f"Error en la busqueda de artista/cancion {titulo}",
                archivo=nombre_archivo,
                excepcion=e
            )
            total_errores += 1
        clases = None
        clase_caratula = None  # INICIALIZACIÓN: Evita variable indefinida
        
        if base_local:
            logger.cancion_encontrada_localmente(nombre_archivo, base_local["cancion"])
            # Crear las clases a través de los identificadores locales
            try:
                clases = creacion_de_clases(id_cancion=base_local["cancion"], base_datos=ruta_db)
            except errores.ErrorBaseDatos as e:
                logger.error(
                    f"Error en la creación de clases {base_local['cancion']}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
        
        if not clases:
            # Búsqueda en iTunes
            logger.cancion_consultada_itunes(nombre_archivo)
            try:
                resultado_busqueda = busqueda_itunes_por_nivel(
                    nombre_artista=artista, 
                    titulo_cancion=titulo, 
                    nivel=nivel_busqueda
                )
                mejor_itunes = obtener_mejor_diccionario(
                    lista=resultado_busqueda.cancion_principal, 
                    titulo_referencia=titulo, 
                    artista_referencia=artista
                )
                if mejor_itunes:
                    resultado_busqueda.cancion_principal.remove(mejor_itunes)
                    
                    try:
                        clases = revisar_diccionario(mejor_itunes)
                        
                        # VALIDACIÓN PREVENTIVA: Verificar antes de guardar
                        es_valido, error_validacion = validador.validar_clases_completas(clases)
                        if not es_valido:
                            logger.error(
                                f"Validación fallida (mejor_itunes): {error_validacion}",
                                archivo=nombre_archivo
                            )
                            error_analyzer.registrar_error_validacion(
                                diccionario=mejor_itunes,
                                detalle=error_validacion or "",
                                nombre_archivo=nombre_archivo
                            )
                            total_errores += 1
                            continue
                        
                        guardado = repository.guardar_cancion_completa(
                            genero=clases["genero"],
                            artistas=clases["artistas"],
                            album=clases["album"],
                            cancion=clases["cancion"],
                            estado="Finalizado",
                            alb_rev=False,
                            db=ruta_db
                        )
                        if not guardado:
                            # FIX: Era 'resultado' (undefined), ahora 'mejor_itunes'
                            logger.error(
                                f"Error al guardar canción (mejor_itunes)",
                                archivo=nombre_archivo
                            )
                            error_analyzer.registrar_error_itunes(
                                diccionario=mejor_itunes,
                                detalle="Falló guardar_cancion_completa",
                                nombre_archivo=nombre_archivo
                            )
                            total_errores += 1
                            continue
                        
                        respuesta_validada = validar_respuesta_itunes(mejor_itunes)
                        clase_caratula = convertir_a_datos_caratula(respuesta_validada)
                        
                    except errores.ErrorValidacion as e:
                        logger.error(
                            f"Error validación iTunes: {e}",
                            archivo=nombre_archivo,
                            excepcion=e
                        )
                        error_analyzer.registrar_error_validacion(
                            diccionario=mejor_itunes,
                            detalle=str(e),
                            nombre_archivo=nombre_archivo
                        )
                        total_errores += 1
                        continue
                
                # Guardar cada diccionario validado como respaldo
                for resultado in resultado_busqueda.todas_las_canciones():
                    try:
                        clase_var = revisar_diccionario(resultado)
                        
                        # VALIDACIÓN PREVENTIVA: Verificar antes de guardar
                        es_valido, error_validacion = validador.validar_clases_completas(clase_var)
                        if not es_valido:
                            logger.warning(
                                f"Validación fallida (respaldo iTunes): {error_validacion}",
                                archivo=nombre_archivo
                            )
                            error_analyzer.registrar_error_validacion(
                                diccionario=resultado,
                                detalle=error_validacion or "",
                                nombre_archivo=nombre_archivo
                            )
                            continue
                        
                        guardado = repository.guardar_cancion_completa(
                            genero=clase_var["genero"],
                            artistas=clase_var["artistas"],
                            album=clase_var["album"],
                            cancion=clase_var["cancion"],
                            estado="Pendiente",
                            alb_rev=False,
                            db=ruta_db
                        )
                        if guardado:
                            respuesta_itunes = validar_respuesta_itunes(resultado)
                            clase_caratula_var = convertir_a_datos_caratula(respuesta_itunes)
                            repository.guardar_caratula(
                                album=clase_var["album"],
                                genero=clase_var["genero"],
                                artistas=clase_var["artistas"],
                                caratula=clase_caratula_var,
                                img_bytes=False,
                                db=ruta_db
                            )
                        else:
                            logger.debug(
                                f"No se guardó respaldo de iTunes",
                                archivo=nombre_archivo
                            )
                            error_analyzer.registrar_error_itunes(
                                diccionario=resultado,
                                detalle="Falló guardar como respaldo",
                                nombre_archivo=nombre_archivo
                            )
                    except errores.ErrorInsercion as e:
                        logger.debug(
                            f"Error inserción respaldo iTunes: {e}",
                            archivo=nombre_archivo
                        )
                        error_analyzer.registrar_error_validacion(
                            diccionario=resultado,
                            detalle=str(e),
                            nombre_archivo=nombre_archivo
                        )
                        
            except errores.ErrorAPI as e:
                logger.error(
                    f"[iTunes] Error búsqueda: {e}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
        
        if not clases:
            # Búsqueda en MusicBrainz
            logger.cancion_consultada_mbz(nombre_archivo)
            try:
                recordings = musicbrainz.buscar_cancion_mbz(titulo, artista)
                mejor_mbz = musicbrainz.obtener_mejor_recording(recordings)
                if mejor_mbz:
                    clases = dicc_a_clases_mbz.convertir_recording(mejor_mbz)
                    
                    # VALIDACIÓN PREVENTIVA
                    es_valido, error_validacion = validador.validar_clases_completas(clases)
                    if not es_valido:
                        logger.error(
                            f"Validación fallida (MBZ): {error_validacion}",
                            archivo=nombre_archivo
                        )
                        error_analyzer.registrar_error_validacion(
                            diccionario=mejor_mbz.to_dict(),
                            detalle=error_validacion or "",
                            nombre_archivo=nombre_archivo
                        )
                        total_errores += 1
                        continue
                else:
                    logger.warning(
                        f"[MBZ] Sin resultados para: {titulo} - {artista}",
                        archivo=nombre_archivo
                    )
                    total_errores += 1
                    continue
            except errores.ErrorAPI as e:
                logger.error(
                    f"[MBZ] {e}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
                continue
        
        # El diccionario con clases ya está definido.
        if clases:
            try:
                datos_musica = modelos_a_datos_musica(clases)
                escribir_tags(ruta_cancion, datos_musica)
                logger.debug(f"Tags ID3 escritos correctamente", archivo=nombre_archivo)
            except errores.ErrorArchivo as e:
                logger.error(
                    f"[ID3] {e}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
            
            # Gestión de carátulas.
            if clase_caratula:  # Ahora es seguro comprobar
                try:   
                    repository.guardar_caratula(
                        album=clases["album"],
                        genero=clases["genero"],
                        artistas=clases["artistas"],
                        caratula=clase_caratula,
                        img_bytes=descargar_caratulas,
                        db=ruta_db
                    )
                    if descargar_caratulas:
                        try:
                            descargar_caratula(clase_caratula, rutas_caratulas)
                        except errores.ErrorBaseDatos as e:
                            logger.error(
                                f"[Carátulas] {e}",
                                archivo=nombre_archivo,
                                excepcion=e
                            )
                    total_errores += 1
                    logger.debug(f"Carátula guardada", archivo=nombre_archivo)
                except errores.ErrorBaseDatos as e:
                    logger.error(
                        f"[Carátulas] {e}",
                        archivo=nombre_archivo,
                        excepcion=e
                    )
                    total_errores += 1
            
            if caratulas_mejoradas and clase_caratula:
                try:
                    album_clase = clases["album"]
                    artista_clase = clases["artistas"]
                    img_bytes = obtener_caratula(album_clase.titulo, artista_clase.principal)
                    if img_bytes:
                        clase_caratula.imagen = img_bytes
                        escribir_caratula(ruta_cancion, clase_caratula)
                        logger.debug(f"Carátula mejorada (Cover Archive)", archivo=nombre_archivo)
                        if descargar_caratulas:
                            guardar_imagen_bytes(clase_caratula, rutas_caratulas)
                except errores.ErrorArchivo as e:
                    logger.warning(
                        f"[Cover Archive] {e}",
                        archivo=nombre_archivo
                    )
    
    # Procesar movimiento de canciones
    if mover_canciones:
        for cancion in lista_archivos_musica:
            ruta_cancion = ruta_principal / cancion
            try:
                mover_y_renombrar_cancion(ruta_cancion=ruta_cancion, ruta_destino=ruta_musica)
            except Exception as e:
                logger.warning(f"No se pudo mover canción: {e}", archivo=cancion)
    
    # Resumen final
    logger.fin_procesamiento(len(lista_archivos_musica), total_errores)
    
    # Registrar resumen de errores detallados
    resumen = error_analyzer.obtener_resumen()
    if resumen["total_errores"] > 0:
        logger.info(f"Errores detallados guardados en: {error_analyzer.ruta_log_errores}")
        logger.info(f"Resumen: {resumen['total_errores']} errores totales")
        for tipo, count in resumen.get("por_tipo", {}).items():
            logger.info(f"  - {tipo}: {count}")

