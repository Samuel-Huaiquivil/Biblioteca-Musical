# database/respository

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from config.settings import get_connection
from models.schemas import Album, Artista, Cancion, GrupoArtistas, Contenedor, Genero, SalidaAlbum, SalidaArtista, SalidaCancion
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


def buscar_artista(artista: Artista, db: Path | None = None) -> SalidaArtista | None:
    """
    Retorna un Artista(Clase Salida) o None si no existen coincidencias.\n
    Params
    - artista: Clase Artista para buscar
    - plus: Query avanzada. Búsqueda con codigos itunes/mbz si es que están en la Clase
    """
    if not artista:
        raise ValueError("Clase Artista inválida.")
    try:
        query = """
            SELECT id_artista, nombre_artista, codigo_itunes, codigo_mbz
            FROM Artistas
            WHERE nombre_artista = ?
        """

        parametros: List[Any] = [artista.nombre]

        if artista.codigo_itunes:
            query += " AND codigo_itunes = ?"
            parametros.append(artista.codigo_itunes)

        if artista.codigo_mbz:
            query += " AND codigo_mbz = ?"
            parametros.append(artista.codigo_mbz)

        with get_connection(db) as conn:
            fila = conn.execute(query, parametros).fetchone()
            if fila is None:
                return None
            return SalidaArtista(
                id_local = fila[0],
                nombre = fila[1],
                codigo_itunes = fila[2],
                codigo_mbz = fila[3]
            )
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando cancion '{artista.nombre}'.") from e


def buscar_cancion(cancion: Cancion, db: Path | None = None) -> SalidaCancion | None:
    """Retorna una Cancion(Clase Salida) o None si no existen coincidencias."""
    if not cancion:
        raise ValueError("Clase Cancion inválida.")
    try:
        query = """
            SELECT c.id_cancion, c.titulo_cancion , a.numero_pista,
                    c.codigo_itunes, c.codigo_mbz
            FROM Canciones c
            JOIN Canciones_Albumes a ON c.id_cancion = a.id_cancion
            WHERE c.titulo_cancion = ?
        """

        parametros: List[Any] = [cancion.titulo]

        if cancion.codigo_itunes:
            query += " AND c.codigo_itunes = ?"
            parametros.append(cancion.codigo_itunes)

        if cancion.codigo_mbz:
            query += " AND c.codigo_mbz = ?"
            parametros.append(cancion.codigo_mbz)

        with get_connection(db) as conn:
            fila = conn.execute(query, parametros).fetchone()
            if fila is None:
                return None
            return SalidaCancion(
                id_local=fila[0],
                titulo=fila[1],
                numero_pista=fila[2],
                codigo_itunes=fila[3],
                codigo_mbz=fila[4]
            )
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando cancion '{cancion.titulo}'.") from e


def buscar_album(album: Album, db: Path | None = None) -> SalidaAlbum | None:
    """Retorna una Album(Clase Salida) o None si no existen coincidencias."""
    if not album:
        raise ValueError("Clase Album inválida.")
    try:
        query = """
            SELECT id_album, titulo_album, fecha_lanzamiento,
                    pistas_totales, codigo_itunes, codigo_mbz
            FROM Albumes
            WHERE titulo_album = ?
        """

        parametros: List[Any] = [album.titulo]
        if album.codigo_itunes:
            query += " AND codigo_itunes = ?"
            parametros.append(album.codigo_itunes)

        if album.codigo_mbz:
            query += " AND codigo_mbz = ?"
            parametros.append(album.codigo_mbz)

        with get_connection(db) as conn:
            fila = conn.execute(query, parametros).fetchone()
            if fila is None:
                return None
            return SalidaAlbum(
                id_local = fila[0],
                titulo = fila[1],
                lanzamiento = fila[2],
                pistas_totales = fila[3],
                codigo_itunes = fila[4],
                codigo_mbz = fila[5]
            )
    except Exception as e:
        raise ErrorBaseDatos(f"Error buscando cancion '{album.titulo}'.") from e


# ---------------------------------------------------------------------------
# Busqueda Elaborada - Funciones de búsqueda auxiliares para el pipeline
# ---------------------------------------------------------------------------


def busqueda_avanzada(titulo: str, artista: str, db: Path | None = None) -> Dict[str, int] | None:
    '''
    Búsqueda auxiliar en la base de datos. Consulta un titulo de la canción y su artista
    para obtener los datos locales, si es que existen.
    '''
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
                JOIN Artistas_Canciones ac ON a.id_artista = ac.id_artista
                JOIN Canciones c ON ac.id_cancion = c.id_cancion
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


def creacion_de_contenedor(id_cancion: int, db: Path | None = None) -> Contenedor:
    """
    Recupera los datos de una canción mediante su ID y los estructura en modelos Pydantic en un Contenedor.
    """
    if not id_cancion:
        raise ValueError("ID de la Canción no válido")
    with get_connection(db) as conn:
        cursor = conn.cursor()

        # 1. Mega-JOIN: Obtenemos toda la información de la canción, su álbum y género
        query_base = '''
            SELECT 
                c.titulo_cancion,
                ca.numero_cancion,
                a.titulo_album,
                a.fecha_lanzamiento,
                a.pistas_totales,
                g.nombre_genero
            FROM Canciones c
            LEFT JOIN Canciones_Albumes ca ON c.id_cancion = ca.id_cancion
            LEFT JOIN Albumes a ON ca.id_album = a.id_album
            LEFT JOIN Generos_Canciones gc ON c.id_cancion = gc.id_cancion
            LEFT JOIN Generos g ON gc.id_genero = g.id_genero
            WHERE c.id_cancion = ?
            ORDER BY a.fecha_lanzamiento DESC
        '''
        datos_base = cursor.execute(query_base, (id_cancion,)).fetchone()

        if not datos_base:
            raise ErrorBaseDatos("Error en la busqueda de datos para el Contenedor")

        # 2. Consultamos la tabla pivote para traer todos los artistas de esta canción
        query_artistas = '''
            SELECT a.nombre_artista, ac.rol_artista
            FROM Artistas_Canciones ac
            JOIN Artistas a ON ac.id_artista = a.id_artista
            WHERE ac.id_cancion = ?
        '''
        artistas_raw = cursor.execute(query_artistas, (id_cancion,)).fetchall()

    # Desempaquetamos los datos base extraídos
    (c_titulo, 
     ca_nro,
     a_titulo, a_lanz, ps_t,
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

    # Modelos Pydantic
    clase_cancion = Cancion(
        titulo=c_titulo,
        num_pista=ca_nro
    )

    clase_album = Album(
        titulo=a_titulo,
        lanzamiento=a_lanz,
        pistas_totales=ps_t
    )

    clase_genero = Genero(
        nombre=g_nombre
    )

    clase_artista = GrupoArtistas(
        principal=principal,
        colaboradores=colaboradores if colaboradores else None,
        feat=feats if feats else None
    )

    # Devolvemos el contenedor
    return Contenedor(
        genero=clase_genero,
        artistas=clase_artista,
        album=clase_album,
        cancion=clase_cancion,
        album_revisado=True,
        cancion_estado=True
    )


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


def insertar_artista(artista: Artista, db: Path | None = None) -> SalidaArtista:
    try:
        if not artista.nombre:
            raise ValueError("El nombre del artista es inválido")
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO Artistas (nombre_artista, codigo_itunes, codigo_mbz) VALUES (?, ?, ?);",
                (artista.nombre, artista.codigo_itunes or None, artista.codigo_mbz or None)
            )
            conn.commit()
            if cursor.lastrowid:
                return SalidaArtista(
                    id_local=cursor.lastrowid,
                    nombre=artista.nombre,
                    codigo_itunes=artista.codigo_itunes or None,
                    codigo_mbz=artista.codigo_mbz or None
                )
            else:
                busqueda = buscar_artista(artista=artista, db=db)
                if busqueda:
                    return busqueda
                else:
                    raise ErrorInsercion("Artista", "Error al insertar Artista")
    except Exception as e:
        raise ErrorInsercion("Artista", str(e)) from e


def insertar_album(album: Album, id_genero: int, id_artista: int, revisado: bool = False, db: Path | None = None) -> SalidaAlbum:
    if not album:
        raise ValueError("El Álbum es inválido")
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO Albumes
                (titulo_album, codigo_itunes, codigo_mbz, pistas_totales,
                 fecha_lanzamiento, revisado, album_explicito,
                 id_genero_principal, id_artista_principal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (album.titulo, album.codigo_itunes, album.codigo_mbz,
                 album.pistas_totales, album.lanzamiento, revisado,
                 album.explicito, id_genero, id_artista)
            )
            conn.commit()
            if cursor.lastrowid:
                return SalidaAlbum(
                    id_local=cursor.lastrowid,
                    titulo=album.titulo,
                    lanzamiento=album.lanzamiento,
                    pistas_totales=album.pistas_totales,
                    codigo_itunes=album.codigo_itunes,
                    codigo_mbz=album.codigo_mbz
                )
            else:
                busqueda = buscar_album(album=album, db=db)
                if busqueda:
                    return busqueda
                else:
                    raise ErrorInsercion("Álbum", "Error al insertar Álbum")
    except Exception as e:
        raise ErrorInsercion("Álbum", str(e)) from e


def insertar_cancion(cancion: Cancion, revisado: bool = False, db: Path | None = None) -> SalidaCancion:
    if not cancion:
        raise ValueError("La canción es inválida")
    try:
        with get_connection(db) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO Canciones
                (titulo_cancion, codigo_itunes, codigo_mbz, 
                revisado, cont_explicito)
                VALUES (?, ?, ?, ?, ?);
                """,
                (cancion.titulo, cancion.codigo_itunes, cancion.codigo_mbz,
                 revisado, cancion.explicito)
            )
            conn.commit()
            if cursor.lastrowid:
                return SalidaCancion(
                    id_local=cursor.lastrowid,
                    titulo=cancion.titulo,
                    numero_pista=1,
                    codigo_itunes=cancion.codigo_itunes,
                    codigo_mbz=cancion.codigo_mbz
                )
            else:
                busqueda = buscar_cancion(cancion=cancion, db=db)
                if busqueda:
                    return busqueda
                else:
                    raise ErrorInsercion("Canción", "Error al insertar Canción")
    except Exception as e:
        raise ErrorInsercion("Canción", str(e)) from e


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
        raise ErrorBaseDatos(f"Error vinculando artista {id_artista} con canción {id_cancion}.") from e


def vincular_cancion_album(id_cancion: int, id_album: int, nro_pista: int = 1, db: Path | None = None) -> None:
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO Canciones_Albumes (id_cancion, id_album, numero_cancion) VALUES (?, ?, ?);",
                (id_cancion, id_album, nro_pista)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error vinculando canción {id_cancion} con álbum {id_album}.") from e
    

def vincular_genero_cancion(id_genero: int, id_cancion: int, db: Path | None = None) -> None:
    try:
        with get_connection(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO Generos_Canciones (id_genero, id_cancion) VALUES (?, ?);",
                (id_genero, id_cancion)
            )
            conn.commit()
    except Exception as e:
        raise ErrorBaseDatos(f"Error vinculando canción {id_cancion} con género {id_genero}.") from e
    

# ===========================================================================
# OPERACIÓN COMPUESTA — obtener o insertar. Retorna resultado válido
# ===========================================================================


def _obtener_o_insertar_artista(clase_artista: Artista, entidad: str, db: Path | None = None) -> SalidaArtista:
    """
    Patrón: busca primero, inserta solo si no existe.
    Retorna clase predefinida.
    """
    resultado = buscar_artista(clase_artista, db)
    if not resultado:
        resultado = insertar_artista(clase_artista, db)
    if not resultado:
        raise ErrorInsercion(entidad, "La función de inserción no retornó una salida válida.")

    return resultado


# ===========================================================================
# PIPELINE PRINCIPAL — busca o inserta y conecta los datos.
# ===========================================================================

# Pipeline Guía
# Buscar o insertar Genero - Artista - Album - Cancion
# Conectar todo

def guardar_cancion_pipeline(
    clase_contenedor: Contenedor,
    ruta_base_datos: Path | None = None
) -> bool:
    '''
    Operación principal del pipeline:
    inserta todos los datos de un Contenedor y vincula sus datos.
    Retorna True si todo fue exitoso.
    '''
    clase_genero = clase_contenedor.genero
    clase_artistas = clase_contenedor.artistas
    clase_album = clase_contenedor.album
    clase_cancion = clase_contenedor.cancion

    # Obtener o insertar Genero
    id_genero = buscar_genero(nombre=clase_genero.nombre, db=ruta_base_datos)
    if not id_genero:
        id_genero = insertar_genero(clase_genero, ruta_base_datos)

    # Obtener o insertar Artista Principal
    principal = Artista(nombre=clase_artistas.principal, codigo_itunes=clase_artistas.codigo_itunes)
    salida_artista = _obtener_o_insertar_artista(
        clase_artista=principal,
        entidad="Artista principal",
        db=ruta_base_datos
    )

    # Obtener o insertar Album
    alb_local = buscar_album(clase_album, ruta_base_datos)
    if alb_local and alb_local.coincide_con(clase_album):
        # Ya existe, no insertar
        salida_album = alb_local
    else:
        # Es diferente o no existe, insertar
        salida_album = insertar_album(
            album=clase_album,
            id_genero=id_genero,
            id_artista=salida_artista.id_local,
            revisado=clase_contenedor.album_revisado,
            db=ruta_base_datos
        )
    
    # Obtener o insertar Cancion
    can_local = buscar_cancion(clase_cancion, ruta_base_datos)
    if can_local and can_local.coincide_con(clase_cancion):
        # Existe, no insertar
        salida_cancion = can_local
    else:
        # Insertar
        salida_cancion= insertar_cancion(
            clase_cancion, 
            clase_contenedor.cancion_estado, 
            db=ruta_base_datos
        )
       
    # -------------------
    # Vincular los datos
    # -------------------

    vincular_genero_cancion(
        id_genero=id_genero,
        id_cancion=salida_cancion.id_local,
        db=ruta_base_datos
    )

    vincular_cancion_album(
        id_cancion=salida_cancion.id_local,
        id_album=salida_album.id_local,
        nro_pista=clase_cancion.num_pista,
        db=ruta_base_datos
    )

    vincular_artista_cancion(
        id_artista=salida_artista.id_local,
        id_cancion=salida_cancion.id_local,
        rol="Principal",
        db=ruta_base_datos
    )

    # Vincular colaboradores
    ids_colab: List[int] = []
    for nombre_colab in (clase_artistas.colaboradores or []):
        col_aux = Artista(nombre=nombre_colab)
        sal = _obtener_o_insertar_artista(
            clase_artista=col_aux,
            entidad="Artista Colaborador",
            db=ruta_base_datos
        )
        ids_colab.append(sal.id_local)
        vincular_artista_cancion(sal.id_local, salida_cancion.id_local, "Colaborador", ruta_base_datos) 

    # Vincular featurings
    for nombre_feat in (clase_artistas.feat or []):
        ft_aux = Artista(nombre=nombre_feat)
        sal = _obtener_o_insertar_artista(
            clase_artista=ft_aux,
            entidad="Artista Feature",
            db=ruta_base_datos
        )
        vincular_artista_cancion(sal.id_local, salida_cancion.id_local, "Feature", ruta_base_datos)
    
    return True