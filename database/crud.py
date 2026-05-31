# db/crud.py
# Operaciones de modificación y consulta sobre la base de datos.
# Complementa a repository.py (que maneja Create y Read simples).
#
# Reglas:
# - Toda función retorna datos o None. Nunca imprime nada.
# - Errores siempre con `raise ... from e` para preservar el traceback.
# - Una función, una responsabilidad.

from pathlib import Path
from typing import Any

from config.settings import get_connection
from utils.errores import ErrorBaseDatos

# Tipo de fila retornada por SQLite
Fila = dict[str, Any]

#ESTADOS_VALIDOS = {"Pendiente", "Revision", "Finalizado"}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _fila_a_dict(cursor, fila: tuple) -> Fila:
    """Convierte una tupla de SQLite a diccionario usando los nombres de columna."""
    columnas = [d[0] for d in cursor.description]
    return dict(zip(columnas, fila))


def _filas_a_dict(cursor, filas: list[tuple]) -> list[Fila]:
    return [_fila_a_dict(cursor, f) for f in filas]


# ===========================================================================
# READ — Consultas
# ===========================================================================

def listar_canciones(revisado: bool | None = None, db: Path | None = None) -> list[Fila]:
    """
    Lista canciones. Si se pasa estado, filtra por él.
    revisado: True | False | None (todas)
    """
    try:
        with get_connection(db) as conn:
            if revisado is not None:
                cursor = conn.execute(
                    """SELECT c.id_cancion, c.titulo_cancion, c.revisado,
                              a.titulo_album, ar.nombre_artista
                       FROM Canciones c
                       LEFT JOIN Canciones_Albumes ca ON c.id_cancion = ca.id_cancion
                       LEFT JOIN Albumes a  ON ca.id_album  = a.id_album
                       LEFT JOIN Artistas_Canciones ac ON c.id_cancion = ac.id_cancion
                                                      AND ac.rol_artista = 'Principal'
                       LEFT JOIN Artistas ar ON ac.id_artista = ar.id_artista
                       WHERE c.revisado = ?
                       ORDER BY ar.nombre_artista, a.titulo_album, ca.numero_cancion""",
                    (revisado,)
                )
            else:
                cursor = conn.execute(
                    """SELECT c.id_cancion, c.titulo_cancion, c.revisado,
                              a.titulo_album, ar.nombre_artista
                       FROM Canciones c
                       LEFT JOIN Canciones_Albumes ca ON c.id_cancion = ca.id_cancion
                       LEFT JOIN Albumes a  ON ca.id_album  = a.id_album
                       LEFT JOIN Artistas_Canciones ac ON c.id_cancion = ac.id_cancion
                                                      AND ac.rol_artista = 'Principal'
                       LEFT JOIN Artistas ar ON ac.id_artista = ar.id_artista
                       ORDER BY ar.nombre_artista, a.titulo_album, c.numero_cancion"""
                )
            return _filas_a_dict(cursor, cursor.fetchall())
    except Exception as e:
        raise ErrorBaseDatos("Error al listar canciones.") from e


def listar_albumes(revisado: bool | None = None, db: Path | None = None) -> list[Fila]:
    """
    Lista álbumes. Si se pasa revisado, filtra por ese estado.
    revisado: True | False | None (todos)
    """
    try:
        with get_connection(db) as conn:
            if revisado is not None:
                cursor = conn.execute(
                    """SELECT a.id_album, a.titulo_album, a.fecha_lanzamiento,
                              a.revisado, ar.nombre_artista, g.nombre_genero
                       FROM Albumes a
                       LEFT JOIN Artistas ar ON a.id_artista_principal = ar.id_artista
                       LEFT JOIN Generos  g  ON a.id_genero_principal  = g.id_genero
                       WHERE a.revisado = ?
                       ORDER BY ar.nombre_artista, a.fecha_lanzamiento""",
                    (revisado,)
                )
            else:
                cursor = conn.execute(
                    """SELECT a.id_album, a.titulo_album, a.fecha_lanzamiento,
                              a.revisado, ar.nombre_artista, g.nombre_genero
                       FROM Albumes a
                       LEFT JOIN Artistas ar ON a.id_artista_principal = ar.id_artista
                       LEFT JOIN Generos  g  ON a.id_genero_principal  = g.id_genero
                       ORDER BY ar.nombre_artista, a.fecha_lanzamiento"""
                )
            return _filas_a_dict(cursor, cursor.fetchall())
    except Exception as e:
        raise ErrorBaseDatos("Error al listar álbumes.") from e


def listar_artistas(db: Path | None = None) -> list[Fila]:
    """Lista todos los artistas ordenados alfabéticamente."""
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """SELECT id_artista, nombre_artista, codigo_itunes, codigo_mbz
                   FROM Artistas ORDER BY nombre_artista"""
            )
            return _filas_a_dict(cursor, cursor.fetchall())
    except Exception as e:
        raise ErrorBaseDatos("Error al listar artistas.") from e


def listar_canciones_por_artista(nombre_artista: str, db: Path | None = None) -> list[Fila]:
    """Lista todas las canciones asociadas a un artista (cualquier rol)."""
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """SELECT c.id_cancion, c.titulo_cancion, c.revisado,
                          ac.rol_artista, a.titulo_album
                   FROM Canciones c
                   JOIN Artistas_Canciones ac ON c.id_cancion  = ac.id_cancion
                   JOIN Artistas ar           ON ac.id_artista = ar.id_artista
                   LEFT JOIN Canciones_Artistas ON c.id_cancion = ca.id_cancion 
                   LEFT JOIN Albumes a        ON ca.id_album    = a.id_album
                   WHERE ar.nombre_artista = ?
                   ORDER BY a.titulo_album, c.numero_pista""",
                (nombre_artista,)
            )
            return _filas_a_dict(cursor, cursor.fetchall())
    except Exception as e:
        raise ErrorBaseDatos(f"Error al listar canciones de '{nombre_artista}'.") from e


def listar_albumes_sin_caratula(db: Path | None = None) -> list[Fila]:
    """Lista álbumes que no tienen carátula guardada en la base de datos."""
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """SELECT a.id_album, a.titulo_album, ar.nombre_artista
                   FROM Albumes a
                   LEFT JOIN Caratulas  c  ON a.id_album   = c.id_album
                   LEFT JOIN Artistas  ar  ON a.id_artista_principal = ar.id_artista
                   WHERE c.id_album IS NULL
                   ORDER BY ar.nombre_artista"""
            )
            return _filas_a_dict(cursor, cursor.fetchall())
    except Exception as e:
        raise ErrorBaseDatos("Error al listar álbumes sin carátula.") from e


def obtener_cancion(id_cancion: int, db: Path | None = None) -> Fila | None:
    """Retorna todos los datos de una canción por su id local."""
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """SELECT c.*, a.titulo_album, g.nombre_genero
                   FROM Canciones c
                   LEFT JOIN Canciones_Albumes ca ON c.id_cancion = ca.id_cancion
                   LEFT JOIN Albumes a ON ca.id_album  = a.id_album
                   LEFT JOIN Generos_Canciones gc ON c.id_cancion = gc.id_cancion
                   LEFT JOIN Generos g ON gc.id_genero = g.id_genero
                   WHERE c.id_cancion = ?""",
                (id_cancion,)
            )
            fila = cursor.fetchone()
            return _fila_a_dict(cursor, fila) if fila else None
    except Exception as e:
        raise ErrorBaseDatos(f"Error al obtener canción id={id_cancion}.") from e


# ===========================================================================
# UPDATE — Actualizaciones
# ===========================================================================

def actualizar_estado_cancion(id_cancion: int, revisado: bool = True, db: Path | None = None) -> None:
    """
    Cambia el estado de una canción.
    revisado: True | False 
    """
    try:
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE Canciones SET revisado = ? WHERE id_cancion = ?",
                (revisado, id_cancion)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al actualizar estado de canción id={id_cancion}.") from e


def marcar_album_revisado(id_album: int, revisado: bool = True, db: Path | None = None) -> None:
    """Marca o desmarca un álbum como revisado."""
    try:
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE Albumes SET revisado = ? WHERE id_album = ?",
                (revisado, id_album)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al actualizar álbum id={id_album}.") from e


def actualizar_codigo_mbz(entidad: str, id_local: int, codigo_mbz: str,
                           db: Path | None = None) -> None:
    """
    Asigna o corrige el código MusicBrainz de un registro.
    entidad: 'cancion' | 'album' | 'artista'
    """
    tablas = {
        "cancion": ("Canciones", "id_cancion"),
        "album":   ("Albumes",   "id_album"),
        "artista": ("Artistas",  "id_artista"),
    }
    if entidad not in tablas:
        raise ValueError(f"Entidad inválida: '{entidad}'. Opciones: {list(tablas)}")
    tabla, col_id = tablas[entidad]
    try:
        with get_connection(db) as conn:
            conn.execute(
                f"UPDATE {tabla} SET codigo_mbz = ? WHERE {col_id} = ?",
                (codigo_mbz, id_local)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al actualizar código MBZ de {entidad} id={id_local}.") from e


def renombrar_artista(id_artista: int, nuevo_nombre: str,
                      db: Path | None = None) -> None:
    """Corrige el nombre de un artista existente."""
    if not nuevo_nombre.strip():
        raise ValueError("El nuevo nombre no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE Artistas SET nombre_artista = ? WHERE id_artista = ?",
                (nuevo_nombre.strip(), id_artista)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al renombrar artista id={id_artista}.") from e


# ===========================================================================
# DELETE — Eliminaciones
# ===========================================================================

def eliminar_cancion(id_cancion: int, db: Path | None = None) -> None:
    """
    Elimina una canción y sus vínculos con artistas.
    No elimina el álbum ni el artista — pueden tener otras canciones.
    """
    try:
        with get_connection(db) as conn:
            conn.execute(
                "DELETE FROM Artistas_Canciones WHERE id_cancion = ?", (id_cancion,)
            )
            conn.execute(
                "DELETE FROM Canciones_Playlist WHERE id_cancion = ?", (id_cancion,)
            )
            conn.execute(
                "DELETE FROM Canciones WHERE id_cancion = ?", (id_cancion,)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al eliminar canción id={id_cancion}.") from e


def eliminar_album_completo(id_album: int, db: Path | None = None) -> None:
    """
    Elimina un álbum y todas sus canciones en cascada.
    Úsalo con cuidado — no se puede deshacer.
    """
    try:
        with get_connection(db) as conn:
            # 1. Obtener IDs de canciones del álbum
            filas = conn.execute(
                "SELECT id_cancion FROM Canciones_Albumes WHERE id_album = ?", (id_album,)
            ).fetchall()
            ids_canciones = [f[0] for f in filas]

            # 2. Eliminar vínculos de cada canción
            for id_c in ids_canciones:
                conn.execute(
                    "DELETE FROM Artistas_Canciones WHERE id_cancion = ?", (id_c,)
                )
                conn.execute(
                    "DELETE FROM Canciones_Playlist WHERE id_cancion = ?", (id_c,)
                )

            # 3. Eliminar canciones relacionadas
            conn.execute("DELETE FROM Canciones_Albumes WHERE id_album = ?", (id_album,))

            # 4. Eliminar carátula si existe
            conn.execute("DELETE FROM Caratulas WHERE id_album = ?", (id_album,))

            # 5. Eliminar álbum
            conn.execute("DELETE FROM Albumes WHERE id_album = ?", (id_album,))

            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error al eliminar álbum id={id_album}.") from e


def eliminar_artista(id_artista: int, db: Path | None = None) -> None:
    """
    Elimina un artista solo si no tiene canciones asociadas.
    Si tiene canciones, lanza un error en vez de eliminar en cascada.
    """
    try:
        with get_connection(db) as conn:
            vinculado = conn.execute(
                "SELECT COUNT(*) FROM Artistas_Canciones WHERE id_artista = ?",
                (id_artista,)
            ).fetchone()[0]

            if vinculado > 0:
                raise ValueError(
                    f"El artista id={id_artista} tiene {vinculado} canción(es) asociada(s). "
                    "Elimínalas primero."
                )

            conn.execute(
                "DELETE FROM Artistas WHERE id_artista = ?", (id_artista,)
            )
            conn.commit()
    except ValueError:
        raise
    except Exception as e:
        raise ErrorBaseDatos(f"Error al eliminar artista id={id_artista}.") from e
