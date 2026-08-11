
# === Excepciones Base ===


class ErrorBaseDatos(Exception):
    "Error al operar con la Base de Datos."
    def __init__(self, mensaje, data= None) -> None:
        super().__init__(mensaje)
        self.data = data


class ErrorAPI(Exception):
    "Error con la API externa."
    def __init__(self, mensaje, data= None) -> None:
        super().__init__(mensaje)
        self.data = data


class ErrorArchivo(Exception):
    "Error al manejar un archivo local"
    def __init__(self, mensaje, data= None) -> None:
        super().__init__(mensaje)
        self.data = data


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


class ErrorVincularDatos(ErrorBaseDatos):
    '''
    Error al vincular los datos
    '''
    def __init__(
            self, primer_nodo: str, id_origen: int, 
            segundo_nodo: str, id_destino: int, detalles: str | None = None):
        self.primer_nodo = primer_nodo
        self.segundo_nodo = segundo_nodo
        self.id_origen = id_origen
        self.id_destino = id_destino
        msg = f"Error vinculando {primer_nodo} ID:{id_origen} con {segundo_nodo} ID:{id_destino}."
        if detalles:
            msg += f" Detalles: {detalles}"
        super().__init__(msg)


class ErrorImagen(ErrorArchivo):
    '''
    Error al operar los bytes de la imagen
    '''
    def __init__(self, archivo_imagen: str, detalles: str | None = None) -> None:
        msg = f"Problemas al operar el archivo '{archivo_imagen}'."
        super().__init__(msg, detalles)


class ErrorConsulta(ErrorAPI):
    '''
    Error genérico de una consulta
    '''
    def __init__(self, mensaje, data=None) -> None:
        super().__init__(mensaje, data)


class ErrorCoverArchive(ErrorAPI):
    '''
    Error al obtener la carátula
    '''
    def __init__(self, info: str, detalles: str | None = None):
        msg = f"[CoverArtArchive]: {info}."
        super().__init__(msg, detalles)


class ErrorItunes(ErrorAPI):
    def __init__(self, mensaje, data=None) -> None:
        msg = f"[iTunes]: {mensaje}"
        super().__init__(msg, data)


class ErrorMusicBrainz(ErrorAPI):
    def __init__(self, mensaje, data=None) -> None:
        msg = f"[MBZ]: {mensaje}"
        super().__init__(msg, data)
