import os
from pathlib import Path
import random

def listar_elementos_ruta(ruta: Path, cantidad: int = 0):
    '''
    Devuelve una lista de los elementos mp3 en la ruta ingresada.\n
    Si la cantidad es 0, devuelve todos los elementos.
    '''
    lista_mp3 = [archivo for archivo in os.listdir(ruta) if archivo.endswith('.mp3')]
    if cantidad >= len(lista_mp3) or cantidad <= 0:
        return lista_mp3
    else:
        return random.sample(lista_mp3, cantidad)