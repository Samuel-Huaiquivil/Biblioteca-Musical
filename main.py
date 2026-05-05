# main.py
# Pipeline principal: lee archivos .mp3, consulta iTunes,
# guarda en base de datos local y (próximamente) escribe tags ID3.

from pathlib import Path

from config.setup import preparar_entorno
from database.init_db import iniciar_base_datos
from database.repository import buscar_artista, buscar_cancion, guardar_cancion_completa
from api.itunes import buscar_cancion_itunes          # por implementar
from utils.obtener_datos_cancion import obtener_datos_cancion
from utils.poderador import obtener_mejor_diccionario, validar_respuesta_itunes
from utils.dicc_a_clases import convertir_respuesta
from utils.listar_mp3 import listar_elementos_ruta    # renombrar a snake_case
from utils.errores import ErrorArchivo, ErrorAPI, ErrorBaseDatos

RUTA_DEFECTO = Path("C:/Users/MSI/Music")

def _registrar_error(ruta_log: Path, mensaje: str) -> None:
    """Añade una línea al log de errores."""
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(mensaje + "\n")


def procesar_canciones(
    ruta: Path = RUTA_DEFECTO,
    cantidad: int = 1,
    base_datos: Path | None = None,
) -> None:
    """
    Procesa una cantidad limitada de canciones en la ruta indicada.
    Para cada archivo:
      1. Lee título y artista desde los tags o el nombre del archivo.
      2. Busca en la base de datos local.
      3. Si no está, consulta iTunes y guarda en la base de datos.
      4. (Pendiente) Escribe los tags ID3 al archivo.
    """
    rutas = preparar_entorno(ruta)
    log = rutas["log"]

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
            continue

        # 3. Consultar iTunes
        try:
            resultados = buscar_cancion_itunes(titulo, artista)
        except ErrorAPI as e:
            _registrar_error(log, f"[API] {e}")
            continue

        if not resultados:
            _registrar_error(log, f"[API] Sin resultados para: {titulo} - {artista}")
            continue

        # 4. Seleccionar el mejor resultado y validarlo
        mejor = obtener_mejor_diccionario(resultados)
        if not mejor:
            _registrar_error(log, f"[PONDERADOR] No se pudo seleccionar resultado para: {titulo}")
            continue

        try:
            respuesta_validada = validar_respuesta_itunes(mejor)
        except ValueError as e:
            _registrar_error(log, f"[VALIDACION] {e}")
            continue

        # 5. Convertir a modelos del dominio
        clases = convertir_respuesta(respuesta_validada)

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

        if guardado:
            print(f"  → Guardado correctamente.")
            # TODO: escribir tags ID3 al archivo


if __name__ == "__main__":
    iniciar_base_datos()
    procesar_canciones()
