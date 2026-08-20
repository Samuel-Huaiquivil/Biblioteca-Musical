from pathlib import Path
import sqlite3
from typing import List

from config.settings import get_connection
from models.schemas_v5 import Ident, Codigo
from utils.errores import ErrorCodigos

# ==========================
# Gestión identificadores
# ==========================

tipos_validos = {
    "artista": "Artistas_Identificadores",
    "cancion": "Canciones_Identificadores",
    "album": "Albumes_Identificadores"
}

def _obtener_todos_identificadores(db: Path | None = None) -> List[Ident]:
    "Obtiene todos los identificadores de las APIs"
    try:
        lista_ident: List[Ident] = []
        with get_connection(db) as conn:
            cursor = conn.cursor()
            res = cursor.execute(
                "SELECT * FROM Apis;",
            ).fetchall()
        for r in res:
            lista_ident.append(
                Ident(
                    id=r[0],
                    api=r[1],
                    region=r[2]
                )
            )
        return lista_ident
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def _insertar_identificador(ident: Ident, db: Path | None = None) -> int:
    "Inserta un Identificador en la tabla APIs"
    try:
        with get_connection(db) as conn:
            res = conn.execute(
                """INSERT INTO Apis 
                (nombre_api, region_api) 
                VALUES (?, ?)""", (ident.api, ident.region)
            )
            conn.commit()
        if res.lastrowid:
            return res.lastrowid
        else:
            raise ValueError(f"Error al insertar Identificador '{ident.api}-{ident.region}'")
    except Exception as identifier:
        raise ValueError(f"Error al insertar Identificador '{ident.api}-{ident.region}'. Detalles: {identifier}")

def obt_ins_identificador(ident: Ident, db: Path | None = None) -> int:
    "Obtiene el ID del identificador, si no existe lo inserta."
    lista_ident = _obtener_todos_identificadores(db)
    for identif in lista_ident:
        if (identif.api == ident.api 
            and
            identif.region == ident.region):
            return identif.id
    return _insertar_identificador(ident, db)


def _insertar_registro_codigo(codigo: Codigo, tipo: str, db: Path | None = None) -> int:
    """
    Inserta un nuevo Codigo Referencial, requiere una clase y el tipo correspondiente
    
    Retorna 0, si no se inserta. 1, si se insertó. 2 si ya estaba.
    """
    if tipo not in tipos_validos.keys():
        raise ValueError(f"Tipo '{tipo}' NO Válido. Opciones: {tipos_validos.keys()}")
    tabla = tipos_validos.get(tipo)
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                f"INSERT INTO {tabla} (api_id, {tipo}_id, codigo_ext) VALUES (?, ?, ?);",
                (codigo.api_id, codigo.tabla_id, codigo.codigo_ext)
            )
            conn.commit()
            if cursor.lastrowid:
                return 1
            else:
                raise ErrorCodigos(f"Error al insertar el Código", f"{tipo} - Cod:{codigo.codigo_ext}")
    except sqlite3.IntegrityError:
        return 2
    except Exception as identifier:
        raise ErrorCodigos(f"{tipo} ID: {codigo.tabla_id}", f"{identifier}") from identifier

def obtener_codigos_api(codigo: Codigo, tipo: str, db: Path | None = None) -> List[str]:
    "Obtiene todos los códigos de la entidad con la api asociada"
    try:
        if tipo not in tipos_validos.keys():
            raise ValueError(f"Tipo '{tipo}' NO Válido. Opciones: {tipos_validos.keys()}")
        tabla = tipos_validos.get(tipo)
        lista_codigos: List[str] = []
        with get_connection(db) as conn:
            query = f"SELECT codigo_ext FROM {tabla} WHERE {tipo}_id = ? AND api_id = ?;"
            filas = conn.execute(query, (codigo.tabla_id, codigo.api_id)).fetchall()
            if not filas:
                return lista_codigos
            else:
                for f in filas:
                    lista_codigos.append(f[0])
            return lista_codigos
    except Exception as e:
        raise ValueError(f"Error: {e}") from e

def obtener_codigos_entidad(id_tabla: int, tipo: str, db: Path | None = None) -> List[str]:
    try:
        if tipo not in tipos_validos.keys():
            raise ValueError(f"Tipo '{tipo}' NO Válido. Opciones: {tipos_validos.keys()}")
        tabla = tipos_validos.get(tipo)
        lista_codigos: List[str] = []
        with get_connection(db) as conn:
            query = f"SELECT codigo_ext FROM {tabla} WHERE {tipo}_id = ?;"
            filas = conn.execute(query, (id_tabla,)).fetchall()
            if not filas:
                return lista_codigos
            else:
                for f in filas:
                    lista_codigos.append(f[0])
            return lista_codigos
    except Exception as e:
        raise ValueError(f"Error: {e}") from e

def insertar_codigo(
        id_entidad: int, ident: int, tipo: str,
        codigo: str, db: Path | None = None
    ) -> int:
    '''
    Inserta el código de la entidad en la base de datos

    Args:
        id_entidad (int): ID del registro con el código.
        ident (int): ID de la API a vincular.
        tipo (str): Tipo de registro (Cancion, Album, Artista).
        codigo (str): El Código que se va insertar.
        db (Path|None): La ruta a la Base de Datos. None para una ruta predefinida.
    
    Returns:
        int: Si se inserta, 1. Si ya estaba, 2
    '''
    try:
        cod_aux = Codigo(
            tabla_id=id_entidad,
            api_id=ident,
            codigo_ext=codigo
        )
        num = _insertar_registro_codigo(
            codigo=cod_aux,
            tipo=tipo,
            db=db
        )
        return num
    except Exception as identifier:
        raise ErrorCodigos(tipo, f"{str(identifier)}")