# database/busqueda.py
from pathlib import Path
from typing import List

from config.settings import get_connection
from database.ident import obtener_codigos
from models.schemas_v5 import Codigo, Ident, SalidaArtista, SalidaAlbum, SalidaCancion

from utils.errores import ErrorBusquedaLocal
# =========================
#  BUSQUEDA LOCAL
# =========================


def buscar_artista(nombre_artista: str, db: Path | None = None) -> SalidaArtista | None:
    '''
    Busca el artista en la base de datos a través de su nombre.\n
    Retorna una clase SalidaArtista con ID Local y su nombre.

    Args:
        nombre_artista (str): Nombre del artista a buscar.
        db (Path | None): Ruta de la base de datos. Si es None, se usará la ruta por defecto.

    Returns:
        SalidaArtista: Clase con el ID local y nombre del artista si se encuentra, None si no se encuentra.
    
    '''
    try:
        with get_connection(db) as conn:
            art = conn.execute('''
                SELECT id_artista, nombre_artista
                FROM Artistas
                WHERE nombre_artista = ?;
                ''', (nombre_artista,)
            ).fetchone()
        if not art:
            return None
        else:
            return SalidaArtista(
                id_local=art[0],
                nombre=art[1]
            )
    except Exception as identifier:
        raise ErrorBusquedaLocal("Artista", f"{nombre_artista}", f"{identifier}") from identifier


def buscar_albumes_artista(id_artista: int, db: Path | None = None) -> List[SalidaAlbum]:
    '''
    Busca los álbumes de un artista en la base de datos a través de su ID.\n
    Retorna una lista de clases SalidaAlbum con ID Local, título, pistas totales
    y fecha de lanzamiento.

    Args:
        id_artista (int): ID del artista a buscar.
        db (Path | None): Ruta de la base de datos. Si es None, se usará la ruta por defecto.   

    Returns:
        List[SalidaAlbum]: Lista de clases con los datos de los álbumes del artista.
    '''
    if not id_artista:
        raise ValueError(f"El id del artista no puede estar vacío")
    try:
        lista_albumes: List[SalidaAlbum] = []
        with get_connection(db) as conn:
            alb = conn.execute('''
                SELECT id_album, titulo_album, 
                    pistas_totales, fecha_lanzamiento 
                FROM Albumes
                WHERE artista_principal_id = ?;
                ''', (id_artista,)
            ).fetchall()
        if not alb:
            return lista_albumes
        else:
            for a in alb:
                lista_albumes.append(
                    SalidaAlbum(
                        id_local=a[0],
                        titulo=a[1],
                        pistas_totales=a[2],
                        lanzamiento=a[3]
                    )
                )
        return lista_albumes
    except Exception as identifier:
        raise ErrorBusquedaLocal("Albumes", f"Artista con ID: {str(id_artista)}", f"{identifier}")


def buscar_canciones_album(id_album: int, db: Path | None = None) -> List[SalidaCancion]:
    if not id_album:
        raise ValueError(f"El id del album no puede estar vacío")
    try:
        lista_canciones: List[SalidaCancion] = []
        with get_connection(db) as conn:
            # Obtenemos los datos del artista
            can = conn.execute('''
                SELECT c.id_cancion, c.titulo_cancion,
                    ca.numero_cancion
                FROM Canciones_Albumes ca
                JOIN Canciones c ON ca.id_cancion = c.id_cancion
                WHERE ca.id_album = ?;
                ''', (id_album,)
            ).fetchall()
        if not can:
            return lista_canciones
        else:
            for c in can:
                lista_canciones.append(
                    SalidaCancion(
                        id_local=c[0],
                        titulo=c[1],
                        album_id=id_album,
                        numero_cancion=c[2]
                    )
                )
        return lista_canciones
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")


def buscar_canciones_artista(id_artista: int, db: Path | None = None) -> List[SalidaCancion]:
    if not id_artista:
        raise ValueError(f"El id del artista no puede estar vacío")
    try:
        lista_canciones: List[SalidaCancion] = []
        with get_connection(db) as conn:
            # Obtenemos los datos del artista
            can = conn.execute('''
                SELECT ac.id_cancion,
                    c.titulo_cancion,
                    ca.id_album, ca.numero_cancion
                FROM Artistas_Canciones ac
                JOIN Canciones c ON ac.id_cancion = c.id_cancion
                JOIN Canciones_Albumes ca ON ac.id_cancion = ca.id_cancion
                WHERE ac.id_artista = ?;
                ''', (id_artista,)
            ).fetchall()
        if not can:
            return lista_canciones
        else:
            for c in can:
                lista_canciones.append(
                    SalidaCancion(
                        id_local=c[0],
                        titulo=c[1],
                        album_id=c[2],
                        numero_cancion=c[3]
                    )
                )
        return lista_canciones
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")


# ------------------------


def buscar_genero(nombre_genero: str, db: Path | None = None) -> int:
    if not nombre_genero:
        raise ValueError(f"El nombre del género no puede estar vacío")
    try:
        with get_connection(db) as conn:
            # Obtenemos los datos del artista
            gen = conn.execute('''
                SELECT id_genero FROM Generos
                WHERE nombre_genero = ?;
                ''', (nombre_genero,)
            ).fetchone()
        if not gen:
            return 0
        else:
            return gen[0]
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def buscar_album(titulo_album: str, id_artista: int, db: Path | None = None) -> int:
    if not id_artista or not titulo_album:
        raise ValueError(f"Los valores no puede estar vacío")
    try:
        with get_connection(db) as conn:
            # Obtenemos los datos del artista
            alb = conn.execute('''
                SELECT id_album
                FROM Albumes
                WHERE artista_principal_id = ? AND titulo_album = ?;
                ''', (id_artista, titulo_album)
            ).fetchone()
        if not alb:
            return 0
        else:
            return alb[0]
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")

def buscar_cancion(titulo_cancion: str, db: Path | None = None) -> int:
    if not titulo_cancion:
        raise ValueError(f"Los valores no puede estar vacío")
    try:
        with get_connection(db) as conn:
            # Obtenemos los datos del artista
            can = conn.execute('''
                SELECT id_cancion
                FROM Canciones
                WHERE titulo_cancion = ?;
                ''', (titulo_cancion,)
            ).fetchone()
        if not can:
            return 0
        else:
            return can[0]
    except Exception as identifier:
        raise ValueError(f"Error: {identifier}")


# =========================
# FUNCIONES COMPUESTAS
# =========================

def buscar_artista_cod(nombre: str, ident: Ident, db: Path | None = None) -> SalidaArtista | None:
    try:
        sal_art = buscar_artista(nombre_artista=nombre, db=db)
        if not sal_art:
            return None
        else:
            cod = Codigo(
                tabla_id=sal_art.id_local,
                api_id=ident.id,
                codigo_ext=""
            )
            lista_cod = obtener_codigos(
                codigo=cod,
                tipo="artista",
                db=db
            )
            sal_art.codigos = lista_cod
            return sal_art
        
    except ErrorBusquedaLocal:
        raise
    
    except Exception as identifier:
        raise ValueError(f"Error no registrado: {identifier}")

def buscar_albumes_artista_cod() -> None:
    return None