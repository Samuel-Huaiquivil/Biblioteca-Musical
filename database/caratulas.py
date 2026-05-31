# database/caratulas.py
# Gestión de las carátulas en la base de datos Local

from pathlib import Path

from config.settings import get_connection
from models.schemas import Caratula, SalidaCaratula
from utils.errores import ErrorBaseDatos

# ===========================================================================
# BÚSQUEDAS + INSERCIÓN — retornan una clase de Salida predeterminada.
# ===========================================================================


def buscar_caratula(id_album: int, db: Path | None = None) -> SalidaCaratula | None:
    """Busca la carátula por id_album."""
    if not id_album:
        raise ValueError("El id_album es inválido.")
    try:
        with get_connection(db) as conn:
            fila = conn.execute(
                """
                SELECT id_caratula, url_caratula, imagen_bytes, id_album
                FROM Caratulas
                WHERE id_album = ?
                """,
                (id_album,)
            ).fetchone()
        if fila is None:
            return None
        return SalidaCaratula(
            id_local=fila[0],
            url_caratula=fila[1],
            imagen_bytes=fila[2] or None,
            id_album=fila[3]
        )
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando carátula del álbum {id_album}.") from e


def _actualizar_bytes_caratula(id_caratula: int, imagen: bytes, db: Path | None = None) -> None:
    """Actualiza los bytes de una carátula existente."""
    try:
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE Caratulas SET imagen_bytes = ? WHERE id_caratula = ?",
                (imagen, id_caratula)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error actualizando bytes de carátula {id_caratula}.") from e


def insertar_caratula(caratula: Caratula, id_album: int, db: Path | None = None) -> SalidaCaratula:
    if not caratula:
        raise ValueError("Datos de la Carátula inválidos.")
    if not id_album:
        raise ValueError("El id_album es inválido.")
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO Caratulas (url_caratula, imagen_bytes, id_album) VALUES (?, ?, ?);",
                (caratula.url_caratula, caratula.imagen or None, id_album)
            )
            conn.commit()
        if cursor.lastrowid:
            return SalidaCaratula(
                id_local=cursor.lastrowid,
                id_album=id_album,
                url_caratula=caratula.url_caratula,
                imagen_bytes=caratula.imagen or None
            )
        raise ErrorBaseDatos(f"Error al insertar carátula del álbum {id_album}.")
    except Exception as e:
        raise ErrorBaseDatos(f"Error al insertar carátula del álbum {id_album}.") from e


def pipeline_caratula(caratula: Caratula, id_album: int, db: Path | None = None) -> SalidaCaratula:
    """
    Busca la carátula del álbum. Si no existe, la inserta.
    Si existe pero no tiene bytes y ahora llegaron, los actualiza.
    """
    existente = buscar_caratula(id_album, db)

    if existente is None:
        return insertar_caratula(caratula, id_album, db)

    # Existe pero llegaron bytes nuevos → actualizar
    if caratula.imagen and not existente.imagen_bytes:
        _actualizar_bytes_caratula(existente.id_local, caratula.imagen, db)
        existente.imagen_bytes = caratula.imagen

    return existente

