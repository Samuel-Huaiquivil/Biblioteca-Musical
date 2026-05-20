# main.py
from processing.biblioteca_musical import procesar_canciones
from config.setup import PR_PATH

procesar_canciones(
    ruta_principal=PR_PATH,
    nivel_busqueda=4,
    numero_canciones=1,
    caratulas_mejoradas=True,
    descargar_caratulas=True, 
    mover_canciones=True
)