# config/setup.py
# Prepara el entorno de trabajo al iniciar el programa.

import os
import dotenv
from pathlib import Path
from typing import TypedDict

from database.init_db import iniciar_base_datos

dotenv.load_dotenv()

_ruta_principal = os.environ.get("RUTA_DEFECTO", "")
_ruta_caratulas = os.environ.get("RUTA_CARATULAS", "")
_ruta_base_datos = os.environ.get("DB_PATH_ABS", "")
_ruta_prueba = os.environ.get("RUTA_ALT", "")

DB_PATH = Path(_ruta_base_datos)
PR_PATH = Path(_ruta_principal)

class RutasEntorno(TypedDict):
    log: Path
    dicc: Path
    base_datos: Path
    musica: Path
    img: Path


def preparar_entorno(ruta_principal: Path = Path(_ruta_principal)) -> RutasEntorno:
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

    if _ruta_caratulas:
        ruta_caratulas = Path(_ruta_caratulas)
    else:
        ruta_caratulas = ruta_principal / "Caratulas"
    ruta_caratulas.mkdir(exist_ok=True)

    if _ruta_base_datos:
        ruta_base_datos = Path(_ruta_base_datos)
    else:
        ruta_base_datos = ruta_principal / "Biblioteca_Musical.sqlite3"
    iniciar_base_datos(ruta_base_datos)

    return RutasEntorno(
        log=archivo_log,
        dicc=archivo_dicc,
        base_datos=ruta_base_datos,
        musica=ruta_musica,
        img=ruta_caratulas
    )
