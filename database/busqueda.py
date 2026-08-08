# database/busqueda.py
"""Funciones de búsqueda de entidades locales en la base de datos."""

from pathlib import Path
from typing import List

from config.settings import get_connection
from database.ident import obtener_codigos
from models.schemas_v5 import Codigo, SalidaArtista, SalidaAlbum, SalidaCancion

from utils.errores import ErrorBusquedaLocal, ErrorCodigos

# =========================
#  BUSQUEDA LOCAL
# =========================


def buscar_artista(nombre_artista: str, db: Path | None = None) -> SalidaArtista | None:
    """Busca un artista por su nombre en la base de datos local.

    Args:
        nombre_artista: Nombre del artista a buscar.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Un objeto :class:`SalidaArtista` con el identificador local y el nombre
        del artista si existe; de lo contrario, ``None``.

    Raises:
        ErrorBusquedaLocal: Si ocurre un error al consultar la base de datos.
    """
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
    """Obtiene los álbumes asociados a un artista dado su identificador local.

    Args:
        id_artista: Identificador local del artista.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista de objetos :class:`SalidaAlbum` con los datos de los álbumes del artista.

    Raises:
        ValueError: Si el identificador del artista no es válido.
        ErrorBusquedaLocal: Si ocurre un error al consultar la base de datos.
    """
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
    """Busca las canciones que pertenecen a un álbum.

    Args:
        id_album: Identificador local del álbum.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista de objetos :class:`SalidaCancion` con la información de las canciones.

    Raises:
        ValueError: Si el identificador del álbum no es válido.
    """
    if not id_album:
        raise ValueError(f"El id del album no puede estar vacío")
    try:
        lista_canciones: List[SalidaCancion] = []
        with get_connection(db) as conn:
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
    """Obtiene las canciones asociadas a un artista.

    Args:
        id_artista: Identificador local del artista.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista de objetos :class:`SalidaCancion` con las canciones del artista.

    Raises:
        ValueError: Si el identificador del artista no es válido.
    """
    if not id_artista:
        raise ValueError(f"El id del artista no puede estar vacío")
    try:
        lista_canciones: List[SalidaCancion] = []
        with get_connection(db) as conn:
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
    """Busca el identificador de un género por su nombre.

    Args:
        nombre_genero: Nombre del género a buscar.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador del género si existe; de lo contrario, ``0``.

    Raises:
        ValueError: Si el nombre del género está vacío.
    """
    if not nombre_genero:
        raise ValueError(f"El nombre del género no puede estar vacío")
    try:
        with get_connection(db) as conn:
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
    """Busca el identificador local de un álbum por título y artista.

    Args:
        titulo_album: Título del álbum a buscar.
        id_artista: Identificador local del artista principal.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador del álbum si existe; de lo contrario, ``0``.

    Raises:
        ValueError: Si alguno de los valores obligatorios está vacío.
        ErrorBusquedaLocal: Si ocurre un error al consultar la base de datos.
    """
    if not id_artista or not titulo_album:
        raise ValueError(f"Los valores no puede estar vacíos.")
    try:
        with get_connection(db) as conn:
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
        raise ErrorBusquedaLocal("Album", titulo_album, f"{identifier}") from identifier


def buscar_cancion(titulo_cancion: str, db: Path | None = None) -> int:
    """Busca el identificador local de una canción por su título.

    Args:
        titulo_cancion: Título de la canción a buscar.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador de la canción si existe; de lo contrario, ``0``.

    Raises:
        ValueError: Si el título de la canción está vacío.
        ErrorBusquedaLocal: Si ocurre un error al consultar la base de datos.
    """
    if not titulo_cancion:
        raise ValueError(f"Los valores no puede estar vacío")
    try:
        with get_connection(db) as conn:
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
        raise ErrorBusquedaLocal("Cancion", titulo_cancion, f"{identifier}") from identifier


def buscar_col_ft_cancion(id_cancion: int, db: Path | None = None) -> List[int]:
    """Obtiene los artistas colaboradores de una canción.

    Args:
        id_cancion: Identificador local de la canción.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista con los identificadores de los artistas colaboradores.

    Raises:
        ValueError: Si el identificador de la canción no es válido.
        ErrorBusquedaLocal: Si ocurre un error al consultar la base de datos.
    """
    if not id_cancion:
        raise ValueError(f"El id de la Canción no puede estar vacíos.")
    try:
        lista_arts: List[int] = []
        with get_connection(db) as conn:
            arts = conn.execute('''
                SELECT id_artista, rol_artista
                FROM Artistas_Canciones
                WHERE id_cancion = ?;
                ''', (id_cancion,)
            ).fetchall()
        if not arts:
            return lista_arts
        for id_a, rol in arts:
            if rol != "Principal":
                lista_arts.append(id_a)
        return lista_arts

    except Exception as identifier:
        raise ErrorBusquedaLocal("Artista * Cancion", f"ID Cancion {id_cancion}", f"{identifier}") from identifier


# =========================
# FUNCIONES COMPUESTAS
# =========================


def buscar_artista_cod(nombre: str, codigo_ident: int, db: Path | None = None) -> SalidaArtista | None:
    """Busca un artista y añade los códigos externos asociados.

    Args:
        nombre: Nombre del artista a buscar.
        codigo_ident: Identificador externo de la API.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Un objeto :class:`SalidaArtista` con los códigos externos asociados si
        existe; de lo contrario, ``None``.

    Raises:
        ErrorBusquedaLocal: Si falla la búsqueda inicial del artista.
        ValueError: Si ocurre un error no registrado durante el proceso.
    """
    try:
        sal_art = buscar_artista(nombre_artista=nombre, db=db)
        if not sal_art:
            return None
        else:
            cod = Codigo(
                tabla_id=sal_art.id_local,
                api_id=codigo_ident,
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


def buscar_albumes_artista_cod(id_artista: int, codigo_ident: int, db: Path | None = None) -> List[SalidaAlbum]:
    """Busca los álbumes de un artista y añade sus códigos externos.

    Args:
        id_artista: Identificador local del artista.
        codigo_ident: Identificador externo de la API.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista de objetos :class:`SalidaAlbum` con los códigos externos asociados.

    Raises:
        Exception: Si ocurre un error al completar la búsqueda.
    """
    try:
        res: List[SalidaAlbum] = []
        lista_albumes = buscar_albumes_artista(id_artista=id_artista, db=db)
        if not lista_albumes:
            return res
        else:
            for album in lista_albumes:
                try:
                    cod = Codigo(
                        tabla_id=album.id_local,
                        api_id=codigo_ident,
                        codigo_ext=""
                    )
                    lista_cod = obtener_codigos(
                        codigo=cod,
                        tipo="album",
                        db=db
                    )
                    album.codigos = lista_cod
                    res.append(album)
                except ErrorCodigos:
                    album.codigos = []
                    res.append(album)
            return res
    except Exception as identifier:
        raise


def buscar_canciones_artista_cod(id_artista: int, codigo_ident: int, db: Path | None = None) -> List[SalidaCancion]:
    """Busca las canciones de un artista y añade sus códigos externos.

    Args:
        id_artista: Identificador local del artista.
        codigo_ident: Identificador externo de la API.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Lista de objetos :class:`SalidaCancion` con los códigos externos asociados.

    Raises:
        Exception: Si ocurre un error al completar la búsqueda.
    """
    try:
        res: List[SalidaCancion] = []
        lista_canciones = buscar_canciones_artista(id_artista=id_artista, db=db)
        if not lista_canciones:
            return res
        else:
            for cancion in lista_canciones:
                try:
                    cod = Codigo(
                        tabla_id=cancion.id_local,
                        api_id=codigo_ident,
                        codigo_ext=""
                    )
                    l_codigos = obtener_codigos(
                        codigo=cod,
                        tipo="cancion",
                        db=db
                    )
                    cancion.codigos = l_codigos
                    res.append(cancion)
                except ErrorCodigos:
                    cancion.codigos = []
                    res.append(cancion)
            return res
    except Exception as identifier:
        raise
