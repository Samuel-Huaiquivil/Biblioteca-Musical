# Gestión Principal

from pathlib import Path

from api import musicbrainz
from api.caratulas import obtener_caratula
from api.gestion_itunes import busqueda_itunes_por_nivel
from config.setup import preparar_entorno
from database.gestion_db import creacion_de_clases
from processing.id3 import escribir_caratula, escribir_tags, modelos_a_datos_musica
from processing.resp_itunes import revisar_diccionario
from utils import dicc_a_clases_mbz, errores
from database import repository
from utils.dicc_a_clases import convertir_a_datos_caratula
from utils.listar_mp3 import listar_elementos_ruta
from utils.mover_archivo import mover_y_renombrar_cancion
from utils.obtener_datos_cancion import obtener_datos_cancion
from utils.poderador import obtener_mejor_diccionario, validar_respuesta_itunes


def _registrar_error(ruta_log: Path, mensaje: str) -> None:
    """Añade una línea al log de errores."""
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")


def procesar_canciones(
        ruta_principal: Path,
        nivel_busqueda: int = 2, 
        numero_canciones: int = 0,
        caratulas_mejoradas: bool = True,
        descargar_caratulas: bool = True,
        mover_canciones: bool = True
    ):
    "Pipeline para procesar las canciones de la biblioteca"
    rutas = preparar_entorno(ruta_principal=ruta_principal)
    log = rutas["log"]
    dicc = rutas["dicc"]
    ruta_db = rutas["base_datos"]
    rutas_caratulas = rutas["img"]
    ruta_musica = rutas["musica"]

    lista_archivos_musica = listar_elementos_ruta(ruta=ruta_principal, cantidad=numero_canciones)

    for nombre_archivo in lista_archivos_musica:
        ruta_cancion = ruta_principal / nombre_archivo

        try:
            datos = obtener_datos_cancion(ruta_cancion)
        except errores.ErrorArchivo as e:
            _registrar_error(log, f"[ARCHIVO] {e}")
            continue

        titulo = datos["tit"]
        artista = datos["art"]

        if not titulo or not artista:
            _registrar_error(log, f"[DATOS] No se pudo obtener título/artista: {ruta_cancion.name}")
            continue

        base_local = repository.busqueda_avanzada(titulo=titulo, artista=artista, db=ruta_db)

        clases = None

        if base_local:
            print(f" Encontrado en base de datos local (id={base_local["cancion"]})")
            # Crear las clases a través de los identificadores locales
            try:
                clases = creacion_de_clases(id_cancion=base_local["cancion"], base_datos=ruta_db)
            except errores.ErrorBaseDatos:
                _registrar_error(log, f"[DB] Error en la creación de clases {base_local['cancion']}")
        
        if not clases:
            # Busqueda en iTunes.
            # Guardar datos y elegir al mejor
            print("Consultando en iTunes.")
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
                    clases = revisar_diccionario(mejor_itunes)
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
                        _registrar_error(dicc, f"[Dicc]\n{resultado}\n****")

                    respuesta_validada = validar_respuesta_itunes(mejor_itunes)
                    clase_caratula = convertir_a_datos_caratula(respuesta_validada)

                # Guardar cada diccionario validado
                for resultado in resultado_busqueda.todas_las_canciones():
                    try:
                        clase_var = revisar_diccionario(resultado)
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
                            _registrar_error(dicc, f"{resultado}\n****")
                    except errores.ErrorInsercion:
                        _registrar_error(dicc, f"{resultado}\n****")
                        
            except errores.ErrorAPI:
                _registrar_error(log, f"[iTunes] Error búsqueda: {titulo}")

        if not clases:
            # Musica en MusicBrainz
            # Guardar datos y elegir al mejor
            print(f" Consultando MusicBrainz...")
            try:
                recordings = musicbrainz.buscar_cancion_mbz(titulo, artista)
                mejor_mbz = musicbrainz.obtener_mejor_recording(recordings)
                if mejor_mbz:
                    clases = dicc_a_clases_mbz.convertir_recording(mejor_mbz)
                else:
                    _registrar_error(log, f"[MBZ] Sin resultados para: {titulo} - {artista}")
                    continue
            except errores.ErrorAPI as e:
                _registrar_error(log, f"[MBZ] {e}")
                continue
        
        # El diccionario con clases ya está definido.
        try:
            datos_musica = modelos_a_datos_musica(clases)
            escribir_tags(ruta_cancion, datos_musica)
        except errores.ErrorArchivo as e:
            _registrar_error(log, f"[ID3] {e}")
        
        # Gestión de carátulas.
        try:
            if descargar_caratulas:
                repository.guardar_caratula(
                    album=clases["album"],
                    genero=clases["genero"],
                    artistas=clases["artistas"],
                    caratula=clase_caratula,
                    img_bytes=True,
                    db=ruta_db
                )
            else:
                repository.guardar_caratula(
                    album=clases["album"],
                    genero=clases["genero"],
                    artistas=clases["artistas"],
                    caratula=clase_caratula,
                    img_bytes=False,
                    db=ruta_db
                )
        except errores.ErrorBaseDatos as e:
            _registrar_error(log, f"[Carátulas] {e}")

        if caratulas_mejoradas:
            try:
                album_clase = clases["album"]
                artista_clase = clases["artistas"]
                img_bytes = obtener_caratula(album_clase.titulo, artista_clase.principal)
                if descargar_caratulas:
                    # Descarga de carátulas
                    pass
                clase_caratula.imagen = img_bytes
                escribir_caratula(ruta_cancion, clase_caratula)
            except errores.ErrorArchivo as e:
                _registrar_error(log, f"[Cover Archive] {e}")
        
        else:
            # Registrar carátulas de iTunes
            try:
                pass
            except errores.ErrorArchivo as e:
                _registrar_error(log, f"[Carátulas] {e}")

    if mover_canciones:
        for cancion in lista_archivos_musica:
            ruta_cancion = ruta_principal / cancion
            mover_y_renombrar_cancion(ruta_cancion=ruta_cancion, ruta_destino=ruta_musica)
        
    print(f"Finalizado: Se han procesado {len(lista_archivos_musica)} archivo(s)")


