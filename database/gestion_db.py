# Funciones adicionales.

from typing import Optional
from pathlib import Path

from config.settings import get_connection
from models.schemas import Caratula, Contenedor, GrupoArtistas, Genero, Cancion, Album
from utils.errores import ErrorBaseDatos

def creacion_de_clases(id_cancion: int, base_datos: Path | None = None) -> Contenedor:
    """
    Recupera los datos de una canción mediante su ID y los estructura en modelos Pydantic.
    """
    with get_connection(base_datos=base_datos) as conn:
        cursor = conn.cursor()

        # 1. Mega-JOIN: Obtenemos toda la información de la canción, su álbum y género
        query_base = '''
            SELECT 
                c.titulo_cancion, c.numero_pista,
                a.titulo_album, a.fecha_lanzamiento,
                g.nombre_genero
            FROM Canciones c
            LEFT JOIN Albumes a ON c.id_album = a.id_album
            LEFT JOIN Generos g ON c.id_genero = g.id_genero
            WHERE c.id_cancion = ?
        '''
        datos_base = cursor.execute(query_base, (id_cancion,)).fetchone()

        if not datos_base:
            raise ErrorBaseDatos("Error al obtener los datos")

        # 2. Consultamos la tabla pivote para traer todos los artistas de esta canción
        query_artistas = '''
            SELECT a.nombre_artista, ac.rol_artista
            FROM Artistas_Canciones ac
            JOIN Artistas a ON ac.id_artista = a.id_artista
            WHERE ac.id_cancion = ?
        '''
        artistas_raw = cursor.execute(query_artistas, (id_cancion,)).fetchall()

    # Desempaquetamos los datos base extraídos
    (c_titulo, c_pista,
     a_titulo, a_lanz,
     g_nombre) = datos_base

    # Separamos los artistas según su rol iterando sobre los resultados
    principal = "Artista Desconocido"
    colaboradores = []
    feats = []

    for nombre, rol in artistas_raw:
        if rol == 'Principal':
            principal = nombre
        elif rol == 'Colaborador':
            colaboradores.append(nombre)
        elif rol == 'Feature':
            feats.append(nombre)

    # Poblamos los modelos de Pydantic asegurando los tipos correctos
    clase_cancion = Cancion(
        titulo=c_titulo,
        num_pista=c_pista
    )

    clase_album = Album(
        titulo=a_titulo,
        lanzamiento=a_lanz
    )

    clase_genero = Genero(
        nombre=g_nombre
    )

    clase_artista = GrupoArtistas(
        principal=principal,
        colaboradores=colaboradores if colaboradores else None,
        feat=feats if feats else None
    )

    # Devolvemos el Contenedor validado
    return Contenedor(
        genero=clase_genero,
        artistas=clase_artista,
        album=clase_album,
        cancion=clase_cancion,
        album_revisado=True,
        cancion_estado=True
    )

def creacion_de_caratula(album: Album, base_datos: Path | None = None) -> Caratula:
    return Caratula(
        codigo_album=album.codigo_itunes,
        url_caratula="",
        imagen=None
    )