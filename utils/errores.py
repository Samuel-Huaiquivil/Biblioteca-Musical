# utils/errores.py
# Excepciones personalizadas del proyecto.

class ErrorBaseDatos(Exception):
    """Error general al operar con la base de datos."""
    pass

class ErrorNoEncontrado(ErrorBaseDatos):
    """El registro buscado no existe en la base de datos."""
    def __init__(self, entidad: str, valor: str):
        super().__init__(f"{entidad} '{valor}' no encontrado en la base de datos.")
        self.entidad = entidad
        self.valor = valor

class ErrorInsercion(ErrorBaseDatos):
    """Fallo al insertar un registro en la base de datos."""
    def __init__(self, entidad: str, detalle: str):
        super().__init__(f"Error al insertar {entidad}: {detalle}")
        self.entidad = entidad

class ErrorAPI(Exception):
    """Error al comunicarse con una API externa."""
    def __init__(self, servicio: str, detalle: str):
        super().__init__(f"Error en la API de {servicio}: {detalle}")
        self.servicio = servicio

class ErrorValidacion(Exception):
    """Los datos recibidos no cumplen el formato esperado."""
    pass

class ErrorArchivo(Exception):
    """Error al leer o procesar un archivo de audio."""
    def __init__(self, ruta: str, detalle: str):
        super().__init__(f"Error procesando '{ruta}': {detalle}")
        self.ruta = ruta
