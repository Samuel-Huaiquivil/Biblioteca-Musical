# database/insert.py
from pathlib import Path
from typing import List

from config.settings import get_connection
from models.schemas_v5 import Artista, Album, Cancion, Genero

from database.busqueda import (
    buscar_album, buscar_artista, 
    buscar_cancion, buscar_genero
    )

# ========= INSERTAR ========   

def insertar_artista(artista: Artista, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            iden = conn.execute("""
            INSERT OR IGNORE INTO Artistas (nombre_artista) VALUES (?);
            """, (artista.nombre,)
            )
            conn.commit()
        if iden.lastrowid:
            return iden.lastrowid
        else:
            art = buscar_artista(artista.nombre, db)
            if art:
                return art.id_local
            else:
                raise ValueError(f"Error al insertar artsita: {artista.nombre}")
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def insertar_album(album: Album, id_artista: int, id_genero: int, revisado: bool = False, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO Albumes
                (titulo_album, pistas_totales, fecha_lanzamiento, revisado,
                 genero_principal_id, artista_principal_id)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (album.titulo, album.pistas_totales, album.lanzamiento,
                 revisado, id_genero, id_artista)
            )
            conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        else:
            return buscar_album(album.titulo, id_artista, db)
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def insertar_cancion(cancion: Cancion, revisado: bool = False, db: Path | None = None) -> int:
    if not cancion:
        raise ValueError("La canción es inválida")
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO Canciones
                (titulo_cancion, revisado)
                VALUES (?, ?);
                """, (cancion.titulo, revisado)
            )
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                return buscar_cancion(cancion.titulo, db=db)
    except Exception as e:
        raise ValueError(f"Error: {e}") from e
    
def insertar_genero(genero: Genero, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO Generos (nombre_genero, descripcion) VALUES (?, ?)",
                (genero.nombre, genero.descripcion)
            )
            conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        else:
            return buscar_genero(genero.nombre, db)
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def vincular_artista_cancion(id_artista: int, id_cancion: int, rol: str = "Principal", db: Path | None = None) -> None:
    """Inserta en la tabla pivote Artistas_Canciones."""
    roles_validos = {"Principal", "Colaborador", "Feature"}
    if rol not in roles_validos:
        raise ValueError(f"Rol inválido: '{rol}'. Opciones: {roles_validos}")
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO Artistas_Canciones (id_cancion, id_artista, rol_artista) VALUES (?, ?, ?);",
                (id_cancion, id_artista, rol)
            )
            conn.commit()
    except Exception as e:
        raise ValueError(f"Vincular Artista - Cancion {e}") from e

def vincular_cancion_album(id_cancion: int, id_album: int, nro_pista: int = 1, db: Path | None = None) -> None:
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO Canciones_Albumes (id_cancion, id_album, numero_cancion) VALUES (?, ?, ?);",
                (id_cancion, id_album, nro_pista)
            )
            conn.commit()
    except Exception as e:
        raise ValueError(f"Vincular Cancion - Album {e}") from e

def vincular_genero_cancion(id_genero: int, id_cancion: int, db: Path | None = None) -> None:
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO Generos_Canciones (id_genero, id_cancion) VALUES (?, ?);",
                (id_genero, id_cancion)
            )
            conn.commit()
    except Exception as e:
        raise ValueError(f"Genero-Cancion {e}") from e
