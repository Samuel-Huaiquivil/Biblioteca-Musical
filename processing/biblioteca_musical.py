# Gestión Principal

from pathlib import Path
import logging

from api import musicbrainz
from api.caratulas import obtener_caratula
from api.gestion_itunes import busqueda_itunes_por_nivel
from config.setup import preparar_entorno
from database.gestion_db import creacion_de_caratula, creacion_de_clases
from database.init_db import iniciar_base_datos
from processing.id3 import contenedor_a_datos_musica, escribir_tags
from processing.resp_itunes import resp_itunes
from utils import dicc_a_clases_mbz
from utils.caratulas import escribir_caratula, gestion_caratulas
from utils.dicc_a_clases import convertir_a_caratula
from utils.gestion_archivos import listar_elementos_ruta, obtener_datos_cancion, mover_y_renombrar_cancion
from database.repository import busqueda_avanzada, guardar_cancion_pipeline
from utils.errores import ErrorAPI, ErrorArchivo, ErrorBaseDatos, ErrorInsercion, ErrorValidacion
from utils.error_analyzer import ErrorAnalyzer
from utils.pipeline_logging import PipelineLogger
from utils.poderador import obtener_mejor_diccionario, validar_respuesta_itunes
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
        except ErrorArchivo as e:
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
            base_local = busqueda_avanzada(titulo=titulo, artista=artista, db=ruta_db)
        except ErrorBaseDatos as e:
            logger.error(
                f"Error en la busqueda de artista/cancion {titulo}",
                archivo=nombre_archivo,
                excepcion=e
            )
            total_errores += 1
        contenedor = None
        caratula = None 
        
        if base_local:
            logger.cancion_encontrada_localmente(nombre_archivo, base_local["cancion"])
            # Crear las clases a través de los identificadores locales
            try:
                contenedor = creacion_de_clases(id_cancion=base_local["cancion"], base_datos=ruta_db)
                caratula = creacion_de_caratula(contenedor.album, ruta_db)
            except ErrorBaseDatos as e:
                logger.error(
                    f"Error en la creación de clases {base_local['cancion']}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
        
        if not contenedor:
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
                    try:
                        contenedor = resp_itunes(mejor_itunes, True, nivel_busqueda >=2 )
                        
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
                        
                        guardado = guardar_cancion_pipeline(contenedor, ruta_db)
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
                        
                        val = validar_respuesta_itunes(mejor_itunes)
                        caratula = convertir_a_caratula(val)
                        resultado_busqueda.cancion_principal.remove(mejor_itunes)
                    
                    except ErrorValidacion as e:
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
                        contenedor_aux = resp_itunes(resultado, False, False)
                        
                        guardado = guardar_cancion_pipeline(contenedor_aux, ruta_db)
                        if guardado:
                            val_aux = validar_respuesta_itunes(resultado)
                            caratula_aux = convertir_a_caratula(val_aux)
                            sal = gestion_caratulas(caratula_aux, rutas_caratulas, ruta_db)
                            if not sal:
                                logger.error(
                                    f"No se guardo la carátula"
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
                    except ErrorInsercion as e:
                        logger.debug(
                            f"Error inserción respaldo iTunes: {e}",
                            archivo=nombre_archivo
                        )
                        error_analyzer.registrar_error_validacion(
                            diccionario=resultado,
                            detalle=str(e),
                            nombre_archivo=nombre_archivo
                        )
                        
            except ErrorAPI as e:
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
            except ErrorAPI as e:
                logger.error(
                    f"[MBZ] {e}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
                continue
        
        # El diccionario con contenedor ya está definido.
        if contenedor:
            try:
                datos_musica = contenedor_a_datos_musica(contenedor)
                escribir_tags(ruta_cancion, datos_musica)
                logger.debug(f"Tags ID3 escritos correctamente", archivo=nombre_archivo)
            except ErrorArchivo as e:
                logger.error(
                    f"[ID3] {e}",
                    archivo=nombre_archivo,
                    excepcion=e
                )
                total_errores += 1
            
            # Gestión de carátulas.
            if caratula and not caratulas_mejoradas:  # Ahora es seguro comprobar
                try:   
                    sal = gestion_caratulas(caratula, rutas_caratulas, ruta_db)
                    escribir_caratula(ruta_cancion, sal)
                except ErrorBaseDatos as e:
                    logger.error(
                        f"[Carátulas] {e}",
                        archivo=nombre_archivo,
                        excepcion=e
                    )
                    total_errores += 1
            
            if caratulas_mejoradas:
                try:
                    img_bytes = obtener_caratula(contenedor.album.titulo, contenedor.artistas.principal)
                    
                    caratula = creacion_de_caratula(contenedor.album, ruta_db)
                    caratula.imagen = img_bytes
                    datos_caratula = gestion_caratulas(
                        caratula, rutas_caratulas, ruta_db
                    )
                    escribir_caratula(ruta_cancion, datos_caratula)
                except ErrorArchivo as e:
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

