# main.py
# Pipeline principal: lee archivos .mp3, consulta iTunes,
# Guarda en base de datos local y escribe tags ID3.

from pathlib import Path
from config.setup import preparar_entorno
from config.settings import DB_PATH, RUTA_ALT, RUTA_CARATULAS, RUTA_CARPETA
from database.repository import buscar_artista, buscar_cancion, guardar_cancion_completa, guardar_caratula
from api.itunes import buscar_cancion_itunes
from api.musicbrainz import buscar_cancion_mbz, obtener_mejor_recording
from utils.caratulas import descargar_caratula
from utils.obtener_datos_cancion import obtener_datos_cancion
from utils.poderador import obtener_mejor_diccionario, validar_respuesta_itunes
from utils.dicc_a_clases import convertir_a_datos_caratula, convertir_respuesta
from utils.dicc_a_clases_mbz import convertir_recording
from utils.listar_mp3 import listar_elementos_ruta
from utils.errores import ErrorArchivo, ErrorAPI, ErrorBaseDatos
from processing.id3 import escribir_tags, insertar_caratula, modelos_a_datos_musica


def _registrar_error(ruta_log: Path, mensaje: str) -> None:
    """Añade una línea al log de errores."""
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")


def procesar_canciones(
    ruta: Path = RUTA_CARPETA,
    cantidad: int = 3,
    base_datos: Path | None = DB_PATH,
) -> None:
    """
    Procesa una cantidad limitada de canciones en la ruta indicada.
    Para cada archivo:
      1. Lee título y artista desde los tags o el nombre del archivo.
      2. Busca en la base de datos local.
      3. Si no está, consulta iTunes (o MusicBrainz como fallback) y guarda.
      4. Escribe los tags ID3 al archivo.
    """
    rutas = preparar_entorno(ruta)
    log = rutas["log"]
    dicc = rutas["dicc"]

    lista = listar_elementos_ruta(ruta=ruta, cantidad=cantidad)

    for nombre_archivo in lista:
        ruta_cancion = ruta / nombre_archivo
        print(f"Procesando: {ruta_cancion.name}")

        # 1. Leer datos del archivo
        try:
            datos = obtener_datos_cancion(ruta_cancion)
        except ErrorArchivo as e:
            _registrar_error(log, f"[ARCHIVO] {e}")
            continue

        titulo = datos["tit"]
        artista = datos["art"]

        if not titulo or not artista:
            _registrar_error(log, f"[DATOS] No se pudo obtener título/artista: {ruta_cancion.name}")
            continue

        # 2. Buscar en base de datos local
        id_cancion = buscar_cancion(titulo, base_datos)
        id_artista = buscar_artista(artista, base_datos)

        if id_cancion and id_artista:
            # Ya está en la base de datos — usar datos locales para ID3
            print(f"  → Encontrado en base de datos local (id={id_cancion})")
            # TODO: leer de la DB y escribir tags ID3
            # Obtener todos los datos y crear una clase.
            continue

        # 3. Consultar iTunes (fuente principal)
        clases = None
        try:
            resultados_itunes = buscar_cancion_itunes(titulo, artista, 3)
            if resultados_itunes:
                # Registrar todos los diccionarios
                for resultado in resultados_itunes:
                    try:
                        respuesta_validada = validar_respuesta_itunes(resultado)
                        clases_var = convertir_respuesta(respuesta_validada)
                        guardado = guardar_cancion_completa(
                            genero=clases_var["genero"],
                            artistas=clases_var["artistas"],
                            album=clases_var["album"],
                            cancion=clases_var["cancion"],
                            db=base_datos,
                        )
                        try:
                            caratula=convertir_a_datos_caratula(respuesta_validada)
                            guardar_caratula(
                                album=clases_var["album"],
                                caratula=caratula,
                                img_bytes=False,
                                db=base_datos
                            )
                        except ErrorBaseDatos as e:
                            _registrar_error(log, f"[CARATULA] Error al guardar datos de carátula: {respuesta_validada.collectionName} - {respuesta_validada.collectionId}.")
                    except ErrorBaseDatos as e:
                        _registrar_error(dicc, f"Dicc: {e} \n {resultado} \n---")

                # Elegir el mejor diccionario del grupo.
                mejor_itunes = obtener_mejor_diccionario(resultados_itunes)
                if mejor_itunes:
                    try:
                        respuesta_validada = validar_respuesta_itunes(mejor_itunes)
                        clases = convertir_respuesta(respuesta_validada)
                    except ValueError as e:
                        _registrar_error(log, f"[ITUNES-VALIDACION] {e}")
        except ErrorAPI as e:
            _registrar_error(log, f"[ITUNES] {e}")

        # 4. Fallback a MusicBrainz si iTunes no dio resultados
        if not clases:
            print(f"  → iTunes sin resultados. Consultando MusicBrainz...")
            try:
                recordings = buscar_cancion_mbz(titulo, artista)
                mejor_mbz = obtener_mejor_recording(recordings)
                if mejor_mbz:
                    clases = convertir_recording(mejor_mbz)
                else:
                    _registrar_error(log, f"[MBZ] Sin resultados para: {titulo} - {artista}")
                    continue
            except ErrorAPI as e:
                _registrar_error(log, f"[MBZ] {e}")
                continue

        # 5. En este punto clases siempre tiene datos válidos

        # 6. Guardar en la base de datos
        try:
            guardado = guardar_cancion_completa(
                genero=clases["genero"],
                artistas=clases["artistas"],
                album=clases["album"],
                cancion=clases["cancion"],
                db=base_datos,
            )
        except ErrorBaseDatos as e:
            _registrar_error(log, f"[DB] {e}")
            continue

        if not guardado:
            _registrar_error(log, f"[DB] Fallo al guardar: {titulo}")
            continue

        # 7. Escribir tags ID3
        try:
            datos_musica = modelos_a_datos_musica(clases)
            escribir_tags(ruta_cancion, datos_musica)
            print(f"  → Tags escritos correctamente.")
        except ErrorArchivo as e:
            _registrar_error(log, f"[ID3] {e}")

        # 8. Gestión de Carátulas
        try:
            caratula=convertir_a_datos_caratula(respuesta_validada)
            guardar_caratula(
                album=clases["album"],
                caratula=caratula,
                img_bytes=True,
                db=base_datos
            )
        except ErrorBaseDatos as e:
            _registrar_error(log, f"[CARATULA] Error al insertar carátula: {respuesta_validada.collectionName} - {respuesta_validada.collectionId}.")

        # Descargar Carátula en la Carpeta Local
        try:
            caratula=convertir_a_datos_caratula(respuesta_validada)
            if descargar_caratula(caratula, RUTA_CARATULAS):

                # Insertar Carátula
                ruta_img = RUTA_CARATULAS / f"{caratula.codigo_album}.jpg"
                insertar_caratula(ruta_cancion, ruta_img)
            else:
                _registrar_error(log, f"[Caratula] Error al descargar la Carátula")
        except Exception as e:
            _registrar_error(log, f"[Caratula] Error: {e}")

if __name__ == "__main__":
    ruta_alternativa = RUTA_ALT
    procesar_canciones(ruta=ruta_alternativa, cantidad=2)
