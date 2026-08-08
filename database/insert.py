# database/insert.py
"""Funciones de inserción y vinculación de entidades en la base de datos local."""

from pathlib import Path
import sqlite3

from config.settings import get_connection
from models.schemas_v5 import Artista, Album, Cancion, Genero

from database.busqueda import buscar_artista, buscar_genero
from utils.errores import ErrorInsercionLocal, ErrorVincularDatos

# ========= INSERTAR ========


def insertar_artista(artista: Artista, db: Path | None = None) -> int:
    """Inserta un artista en la base de datos o devuelve el existente.

    Args:
        artista: Objeto con los datos del artista a insertar.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador local del artista insertado o recuperado.

    Raises:
        ValueError: Si el artista ya existe pero no se puede recuperar su ID.
        ErrorInsercionLocal: Si ocurre un error durante la inserción.
    """
    try:
        with get_connection(db) as conn:
            cursor = conn.execute("""
                INSERT INTO Artistas (nombre_artista) VALUES (?);
            """, (artista.nombre,))
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                return 0

    except sqlite3.IntegrityError:
        art = buscar_artista(artista.nombre, db)
        if art:
            return art.id_local
        else:
            raise ValueError(f"El artista '{artista}' ya existe, pero no se pudo recuperar su ID.")

    except Exception as e:
        raise ErrorInsercionLocal("Artista", f"{artista.nombre}", f"{str(e)}") from e


def insertar_album(album: Album, id_artista: int, revisado: bool = False, db: Path | None = None) -> int:
    """Inserta un álbum asociado a un artista.

    Args:
        album: Objeto con los datos del álbum a insertar.
        id_artista: Identificador local del artista principal.
        revisado: Indica si el álbum ya fue revisado.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador local del álbum insertado.

    Raises:
        ErrorInsercionLocal: Si ocurre un error durante la inserción.
    """
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT INTO Albumes
                (titulo_album, pistas_totales, fecha_lanzamiento, revisado,
                 artista_principal_id)
                VALUES (?, ?, ?, ?, ?);
                """,
                (album.titulo, album.pistas_totales, album.lanzamiento,
                 revisado, id_artista)
            )
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                return 0

    except Exception as e:
        raise ErrorInsercionLocal("Album", f"{album.titulo}, ID Artista:{id_artista}", f"{str(e)}") from e


def insertar_cancion(cancion: Cancion, revisado: bool = False, db: Path | None = None) -> int:
    """Inserta una canción en la base de datos.

    Args:
        cancion: Objeto con los datos de la canción a insertar.
        revisado: Indica si la canción ya fue revisada.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador local de la canción insertada.

    Raises:
        ValueError: Si el objeto de canción es inválido.
        ErrorInsercionLocal: Si ocurre un error durante la inserción.
    """
    if not cancion:
        raise ValueError("La canción es inválida")
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT INTO Canciones
                (titulo_cancion, revisado)
                VALUES (?, ?);
                """, (cancion.titulo, revisado)
            )
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                return 0

    except Exception as e:
        raise ErrorInsercionLocal("Album", f"{cancion.titulo}", f"{str(e)}") from e


def insertar_genero(genero: Genero, db: Path | None = None) -> int:
    """Inserta un género o devuelve el identificador existente.

    Args:
        genero: Objeto con los datos del género a insertar.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador local del género insertado o recuperado.

    Raises:
        ErrorInsercionLocal: Si ocurre un error durante la inserción.
    """
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT INTO Generos (nombre_genero, descripcion) VALUES (?, ?)",
                (genero.nombre, genero.descripcion)
            )
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                return 0
    except sqlite3.IntegrityError:
        return buscar_genero(
            nombre_genero=genero.nombre,
            db=db
        )

    except Exception as e:
        raise ErrorInsercionLocal("Género", f"{genero.nombre}", f"{str(e)}") from e


def vincular_artista_cancion(id_artista: int, id_cancion: int, rol: str = "Principal", db: Path | None = None) -> None:
    """Vincula un artista con una canción mediante la tabla pivote.

    Args:
        id_artista: Identificador local del artista.
        id_cancion: Identificador local de la canción.
        rol: Rol del artista en la canción.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Raises:
        ValueError: Si el rol proporcionado no es válido.
        ErrorVincularDatos: Si ocurre un error al crear el vínculo.
    """
    roles_validos = {"Principal", "Colaborador", "Feature"}
    if rol not in roles_validos:
        raise ValueError(f"Rol inválido: '{rol}'. Opciones: {roles_validos}")
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO Artistas_Canciones (id_cancion, id_artista, rol_artista) VALUES (?, ?, ?);",
                (id_cancion, id_artista, rol)
            )
            conn.commit()
    except Exception as e:
        raise ErrorVincularDatos("Artista", id_artista, "Cancion", id_cancion, f"{str(e)}") from e


def vincular_cancion_album(id_cancion: int, id_album: int, nro_pista: int = 1, db: Path | None = None) -> None:
    """Vincula una canción con un álbum mediante la tabla pivote.

    Args:
        id_cancion: Identificador local de la canción.
        id_album: Identificador local del álbum.
        nro_pista: Número de pista de la canción en el álbum.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Raises:
        ErrorVincularDatos: Si ocurre un error al crear el vínculo.
    """
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO Canciones_Albumes (id_cancion, id_album, numero_cancion) VALUES (?, ?, ?);",
                (id_cancion, id_album, nro_pista)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise
    except Exception as e:
        raise ErrorVincularDatos("Cancion", id_cancion, "Album", id_album, f"{str(e)}") from e


def vincular_genero_cancion(id_genero: int, id_cancion: int, db: Path | None = None) -> None:
    """Vincula un género con una canción mediante la tabla pivote.

    Args:
        id_genero: Identificador local del género.
        id_cancion: Identificador local de la canción.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Raises:
        ErrorVincularDatos: Si ocurre un error al crear el vínculo.
    """
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO Generos_Canciones (id_genero, id_cancion) VALUES (?, ?);",
                (id_genero, id_cancion)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise
    except Exception as e:
        raise ErrorVincularDatos("Genero", id_genero, "Cancion", id_cancion, f"{str(e)}") from e
