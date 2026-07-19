
# === Excepciones Base ===

from typing import Dict, List

from pydantic import ValidationError


# === Excepciones Generales ===

class ErrorBaseDatos(Exception):
    "Error al operar con la Base de Datos."
    pass



# === Excepciones Puntuales ===
class ErrorCodigos(ErrorBaseDatos):
    '''
    Error al busqueda de Códigos en la Base de Datos.
    '''
    def __init__(self, entidad: str, detalles: str):
        self.entidad = entidad
        super().__init__(f"Error buscando los Códigos Externos de {entidad}. Detalles {detalles}")


class ErrorBusquedaLocal(ErrorBaseDatos):
    '''
    Error al buscar un registro en la base de datos local.

    Attributes:
        tabla (str): Nombre de la tabla donde se realizó la búsqueda.
        valor (str): Valor que se buscaba.
        detalles (str): Detalles adicionales sobre el error.
    '''
    def __init__(self, tabla: str, valor: str, detalles: str):
        self.tabla = tabla
        self.valor = valor
        self.detalles = detalles
        super().__init__(f"Error buscando {valor} en {tabla}. Detalles {detalles}")


class ErrorInsercionLocal(ErrorBaseDatos):
    '''
    Error al insertar un registro en la base de datos local.
    '''
    def __init__(self, tabla: str, datos: str, detalles: str):
        self.tabla = tabla
        self.datos = datos
        self.detalles = detalles
        super().__init__(f"Error insertando {datos} en {tabla}. Detalles {detalles}")