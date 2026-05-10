# config/setup.py
# Prepara el entorno de trabajo al iniciar el programa.

from pathlib import Path
from typing import TypedDict
from database.init_db import iniciar_base_datos
from config.settings import DB_PATH

class RutasEntorno(TypedDict):
    log: Path
    dicc: Path
    base_datos: Path
    musica: Path


def preparar_entorno(ruta_principal: Path) -> RutasEntorno:
    """
    Asegura que existan las carpetas y archivos necesarios para operar.
    Retorna un diccionario con las rutas críticas del proyecto.
    """
    ruta_principal.mkdir(parents=True, exist_ok=True)

    carpeta_errores = ruta_principal / "Errores"
    carpeta_errores.mkdir(exist_ok=True)

    archivo_log = carpeta_errores / "Errores.txt"
    archivo_log.touch(exist_ok=True)

    archivo_dicc = carpeta_errores / "Diccionarios.txt"
    archivo_dicc.touch(exist_ok=True)

    ruta_musica = ruta_principal / "Música"
    ruta_musica.mkdir(exist_ok=True)

    iniciar_base_datos(DB_PATH)

    return RutasEntorno(
        log=archivo_log,
        dicc=archivo_dicc,
        base_datos=ruta_principal / "Biblioteca_Musical.sqlite3",
        musica=ruta_musica,
    )
