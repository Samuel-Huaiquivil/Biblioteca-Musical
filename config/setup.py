# config/setup.py
# Prepara el entorno de trabajo al iniciar el programa.

import os
import dotenv
from pathlib import Path
from typing import TypedDict

dotenv.load_dotenv()

_carpeta_principal  = os.environ.get("CARPETA_MUSICA", "")
_carpeta_errores    = os.environ.get("CARPETA_ERRORES", "")
_ruta_base_datos    = os.environ.get("RUTA_BASE_DATOS", "")
_carpeta_caratulas  = os.environ.get("CARPETA_CARATULAS", "")
_carpeta_destino    = os.environ.get("CARPETA_DESTINO", "")
_correo_personal    = os.environ.get("CORREO_PERSONAL", "example@mail.com")

CARP_PRINCIPAL = Path(_carpeta_principal)
RUTA_DATABASE = Path(_ruta_base_datos)
CORREO_PERSONAL = _correo_personal


class RutasEntorno(TypedDict):
    base_datos: Path
    errores: Path
    caratulas: Path
    destino: Path


def preparar_entorno(ruta_principal: Path = CARP_PRINCIPAL) -> RutasEntorno:
    """
    Asegura que existan las carpetas y archivos necesarios para operar.
    Retorna un diccionario con las rutas críticas del proyecto.
    """
    try:
        ruta_principal.mkdir(parents=True, exist_ok=True)

        if _carpeta_errores:
            carpeta_errores = Path(_carpeta_errores)
        else:
            carpeta_errores = ruta_principal / "Script Biblioteca Musical"
        carpeta_errores.mkdir(exist_ok=True)

        if _ruta_base_datos:
            ruta_db = Path(_ruta_base_datos)
        else:
            ruta_db = carpeta_errores / "Biblioteca Musical.sqlite3"

        if _carpeta_caratulas:
            carpeta_caratulas = Path(_carpeta_caratulas)
        else:
            carpeta_caratulas = carpeta_errores / "Caratulas"
        carpeta_caratulas.mkdir(exist_ok=True)

        if _carpeta_destino:
            carpeta_destino = Path(_carpeta_destino)
        else:
            carpeta_destino = ruta_principal
        carpeta_destino.mkdir(exist_ok=True)

        return RutasEntorno(
            base_datos=ruta_db,
            errores=carpeta_errores,
            caratulas=carpeta_caratulas,
            destino=carpeta_destino
        )
    except Exception as e:
        raise
