# db/repository.py
# Única capa de acceso a datos. Reemplaza a: nombre.py, simple.py,
# conexion.py, busq_tit_art.py y get_insert.py

import sqlite3
from pathlib import Path
from typing import Dict, List

from config.settings import get_connection
from models.schemas import Album, Cancion, DatosCaratula, GrupoArtistas, Genero
from utils.errores import ErrorBaseDatos, ErrorInsercion


# ===========================================================================
# BÚSQUEDAS — retornan el id local o 0 si no existe
# ===========================================================================

def buscar_genero(nombre: str, db: Path | None = None) -> int:
    """Retorna id_genero o 0 si no existe."""
    if not nombre:
        raise ValueError("El nombre del género no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            fila = conn.execute(
                "SELECT id_genero FROM Generos WHERE nombre_genero = ?", (nombre,)
            ).fetchone()
        return fila[0] if fila else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando género '{nombre}'.") from e


def buscar_artista(nombre: str, db: Path | None = None) -> int:
    """Retorna id_artista o 0 si no existe."""
    if not nombre:
        raise ValueError("El nombre del artista no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            fila = conn.execute(
                "SELECT id_artista FROM Artistas WHERE nombre_artista = ?", (nombre,)
            ).fetchone()
        return fila[0] if fila else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando artista '{nombre}'.") from e


def buscar_album(titulo: str, db: Path | None = None) -> int:
    """Retorna id_album o 0 si no existe."""
    if not titulo:
        raise ValueError("El título del álbum no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            fila = conn.execute(
                "SELECT id_album FROM Albumes WHERE titulo_album = ?", (titulo,)
            ).fetchone()
        return fila[0] if fila else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando álbum '{titulo}'.") from e


def buscar_cancion(titulo: str, db: Path | None = None) -> int:
    """Retorna id_cancion o 0 si no existe."""
    if not titulo:
        raise ValueError("El título de la canción no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            fila = conn.execute(
                "SELECT id_cancion FROM Canciones WHERE titulo_cancion = ?", (titulo,)
            ).fetchone()
        return fila[0] if fila else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando canción '{titulo}'.") from e


def buscar_caratula(id_album: int, db: Path | None = None) -> int:
    if not id_album:
        raise ValueError("El ID del álbum no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_caratula FROM Caratulas WHERE id_album = ?;", (id_album,)
            )
            id_caratula = cursor.fetchone()
        return id_caratula[0] if id_caratula else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando la Carátula del Álbum con ID: {id_album}.") from e


def buscar_album_cod_itunes(codigo_itunes: int, db: Path | None = None) -> int:
    if not codigo_itunes:
        raise ValueError("El código iTunes del álbum no puede estar vacío.")
    try:
        with get_connection(db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id_album FROM Albumes WHERE codigo_itunes = ?;", (codigo_itunes,)
            )
            id_album = cursor.fetchone()
        return id_album[0] if id_album else 0
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando el álbum con Código iTunes: {codigo_itunes}.") from e


def busqueda_avanzada(titulo: str, artista: str, db: Path | None = None) -> Dict[str, int] | None:
    if not titulo:
        raise ValueError("El título de la canción no puede estar vacío.")
    if not artista:
        raise ValueError("El nombre del artista no puede estar vacío.")

    try:
        with get_connection(db) as conn:
            cursor = conn.cursor()

            # Consulta con JOIN: busca artista y canción en una sola pasada
            resultado = cursor.execute(
                """
                SELECT a.id_artista, c.id_cancion
                FROM Artistas a
                JOIN Canciones c ON a.id_artista = c.id_artista
                WHERE a.nombre_artista = ? AND c.titulo_cancion = ?
                """,
                (artista, titulo)
            ).fetchone()

            if resultado is None:
                return None

            id_artista, id_cancion = resultado
            return {"artista": id_artista, "cancion": id_cancion}

    except sqlite3.Error as e:
        raise ErrorBaseDatos(f"Error buscando canción '{titulo}': {e}") from e


# ===========================================================================
# INSERCIONES — retornan el id del registro insertado
# ===========================================================================

def insertar_genero(genero: Genero, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO Generos (nombre_genero) VALUES (?);",
                (genero.nombre,)
            )
            conn.commit()
            return cursor.lastrowid or buscar_genero(genero.nombre, db)
    except Exception as e:
        raise ErrorInsercion("Género", str(e)) from e


def insertar_artista(artista_nombre: str, codigo_itunes: int = 0, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO Artistas (nombre_artista, codigo_itunes) VALUES (?, ?);",
                (artista_nombre, codigo_itunes or None)
            )
            conn.commit()
            return cursor.lastrowid or buscar_artista(artista_nombre, db)
    except Exception as e:
        raise ErrorInsercion("Artista", str(e)) from e


def insertar_album(album: Album, id_genero: int, id_artista: int,
                   revisado: bool = False, db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO Albumes
                (titulo_album, codigo_itunes, codigo_mbz, numero_canciones,
                 fecha_lanzamiento, revisado, album_explicito,
                 id_genero_principal, id_artista_principal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (album.titulo, album.codigo_itunes, album.codigo_mbz,
                 album.num_pistas, album.lanzamiento, revisado,
                 album.explicito, id_genero, id_artista)
            )
            conn.commit()
            return cursor.lastrowid or buscar_album(album.titulo, db)
    except Exception as e:
        raise ErrorInsercion("Álbum", str(e)) from e


def insertar_cancion(cancion: Cancion, id_album: int, id_genero: int,
                     estado: str = "Pendiente", db: Path | None = None) -> int:
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO Canciones
                (titulo_cancion, codigo_itunes, codigo_mbz, estado,
                 numero_pista, cont_explicito, id_album, id_genero)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                (cancion.titulo, cancion.codigo_itunes, cancion.codigo_mbz,
                 estado, cancion.num_pista, cancion.explicito, id_album, id_genero)
            )
            conn.commit()
            return cursor.lastrowid or buscar_cancion(cancion.titulo, db)
    except Exception as e:
        raise ErrorInsercion("Canción", str(e)) from e


def vincular_artista_cancion(id_artista: int, id_cancion: int,
                              rol: str = "Principal", db: Path | None = None) -> None:
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
        raise ErrorBaseDatos(f"Error vinculando artista {id_artista} con canción {id_cancion}.") from e


def insertar_caratula(caratula: DatosCaratula, id_album: int, img_bytes: bool = False, db: Path | None = None) -> None:
    "Inserta la url de la carátula"
    try:
        imagen_bytes=None
        if img_bytes:
            import requests
            url = caratula.url_caratula
            respuesta = requests.get(url, timeout=10)
            respuesta.raise_for_status() 
            imagen_bytes = respuesta.content
        with get_connection(db) as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO Caratulas
                (url_caratula, imagen_bytes, id_album)
                VALUES (?, ?, ?);""",
                (caratula.url_caratula, imagen_bytes, id_album)
            )
            conn.commit()
    except Exception as e:
        raise ErrorInsercion("Carátula", str(e)) from e


# ===========================================================================
# OPERACIÓN COMPUESTA — obtener o insertar (patrón principal del pipeline)
# ===========================================================================

def _obtener_o_insertar(buscar_fn, insertar_fn, entidad: str) -> int:
    """
    Patrón genérico: busca primero, inserta solo si no existe.
    Retorna siempre el id del registro.
    """
    resultado = buscar_fn()
    if not resultado:
        resultado = insertar_fn()
    if not resultado:
        raise ErrorInsercion(entidad, "La función de inserción no retornó un id válido.")
    return resultado


def guardar_caratula(album: Album, genero: Genero, artistas: GrupoArtistas, caratula: DatosCaratula, img_bytes: bool = False, db: Path | None = None) -> None:
    try:
        id_album = buscar_album(album.titulo, db)
        
        if not id_album:
            id_genero = _obtener_o_insertar(
                buscar_fn=lambda: buscar_genero(genero.nombre, db),
                insertar_fn=lambda: insertar_genero(genero, db),
                entidad="Género"
            )
            id_artista_principal = _obtener_o_insertar(
                buscar_fn=lambda: buscar_artista(artistas.principal, db),
                insertar_fn=lambda: insertar_artista(artistas.principal, artistas.codigo_itunes, db),
                entidad="Artista principal"
            )
            id_album = insertar_album(album, id_genero, id_artista_principal, False, db)
        
        insertar_caratula(caratula, id_album, img_bytes, db)
    except ErrorInsercion as e:
        raise ErrorInsercion("Caratula", f"Error: {e}")


def guardar_cancion_completa(
    genero: Genero,
    artistas: GrupoArtistas,
    album: Album,
    cancion: Cancion,
    estado: str = "Pendiente",
    alb_rev: bool = False,
    db: Path | None = None
) -> bool:
    """
    Operación principal del pipeline:
    inserta todos los datos de una canción y vincula los artistas.
    Retorna True si todo fue exitoso.
    """
    id_genero = _obtener_o_insertar(
        buscar_fn=lambda: buscar_genero(genero.nombre, db),
        insertar_fn=lambda: insertar_genero(genero, db),
        entidad="Género"
    )
    id_artista_principal = _obtener_o_insertar(
        buscar_fn=lambda: buscar_artista(artistas.principal, db),
        insertar_fn=lambda: insertar_artista(artistas.principal, artistas.codigo_itunes, db),
        entidad="Artista principal"
    )
    id_album = _obtener_o_insertar(
        buscar_fn=lambda: buscar_album(album.titulo, db),
        insertar_fn=lambda: insertar_album(album, id_genero, id_artista_principal, alb_rev, db),
        entidad="Álbum"
    )
    id_cancion = _obtener_o_insertar(
        buscar_fn=lambda: buscar_cancion(cancion.titulo, db),
        insertar_fn=lambda: insertar_cancion(cancion, id_album, id_genero, estado, db),
        entidad="Canción"
    )

    # Vincular artista principal
    vincular_artista_cancion(id_artista_principal, id_cancion, "Principal", db)

    # Vincular colaboradores
    ids_colab: List[int] = []
    for nombre_colab in (artistas.colaboradores or []):
        id_c = _obtener_o_insertar(
            buscar_fn=lambda n=nombre_colab: buscar_artista(n, db),
            insertar_fn=lambda n=nombre_colab: insertar_artista(n, db=db),
            entidad=f"Colaborador '{nombre_colab}'"
        )
        ids_colab.append(id_c)
        vincular_artista_cancion(id_c, id_cancion, "Colaborador", db)

    # Vincular featurings
    for nombre_feat in (artistas.feat or []):
        id_f = _obtener_o_insertar(
            buscar_fn=lambda n=nombre_feat: buscar_artista(n, db),
            insertar_fn=lambda n=nombre_feat: insertar_artista(n, db=db),
            entidad=f"Featuring '{nombre_feat}'"
        )
        vincular_artista_cancion(id_f, id_cancion, "Feature", db)

    return True
