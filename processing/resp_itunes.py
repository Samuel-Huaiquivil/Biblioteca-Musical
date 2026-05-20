# Funciones para revisar cada diccionario
from pathlib import Path
from typing import Dict, Any

from models.schemas import DatosCaratula
from utils.dicc_a_clases import convertir_respuesta, convertir_respuesta_album_single, convertir_respuesta_simple
from utils.errores import ErrorValidacion
from utils.poderador import validar_respuesta_itunes, propiedades_minimas

def revisar_diccionario(diccionario: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Realiza todos los pasos para gestionar los diccionario tipo 'canción'. Retorna un diccionario con las clases Pydantic.
    Gestiona si un diccionario tiene un artista en solitario, multiples artistas o si es un Album tipo 'Single'
    '''
    # Propiedades Mínimas
    if not propiedades_minimas(dicc=diccionario):
        raise ErrorValidacion(f"El Diccionario no cumple con las cantidades Mínimas")
    
    # Determinar si son unos o varios artistas.
    artista_solitario: bool = True
    # Determinar si la canción es de un album "Single"
    album_single: bool = False

    if diccionario.get("collectionArtistName", None) or diccionario.get("collectionArtistId", None):
        artista_solitario = False
    if "single" in diccionario.get("collectionName", "").lower() and diccionario.get("trackCount", 1) == 1:
        album_single = True
    
    # Verificar con Pydantic y conversión a clase RespuestaItunes
    respuesta_itunes = validar_respuesta_itunes(diccionario)

    # Convertir a clases Cancion y Artista

    # Si es un album single, gestión diferente
    if album_single:
        return convertir_respuesta_album_single(respuesta_itunes)
    # Si son varios artistas, gestión diferente.
    if not artista_solitario:
        return convertir_respuesta(respuesta_itunes)    
    # Gestión simple
    return convertir_respuesta_simple(respuesta_itunes)

