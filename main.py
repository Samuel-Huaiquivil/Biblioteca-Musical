# main.py
from processing.biblioteca_musical import procesar_canciones
from config.setup import PR_PATH

d = procesar_canciones(
    ruta_principal=PR_PATH,
    nivel_busqueda=4,
    numero_canciones=1,
    caratulas_mejoradas=False,
    descargar_caratulas=False, 
    mover_canciones=True
)