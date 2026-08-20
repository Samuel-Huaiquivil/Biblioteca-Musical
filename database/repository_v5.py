"""Pipeline de integración de datos para insertar paquetes de información en la base de datos local."""
from datetime import date
import sqlite3
from pathlib import Path
from typing import List, Tuple

from utils.errores import ErrorVincularDatos
from utils.logging_class import PipelineLog
from models.schemas_v5 import (
    Album, Cancion, SalidaArtista, 
    Artista, PaqueteDatos
)

from database.ident import insertar_codigo
from database.busqueda import (
    buscar_col_ft_cancion,
    buscar_genero,
    buscar_artista_cod,
    buscar_canciones_artista_cod,
    buscar_albumes_artista_cod
)
from database.insert import (
    insertar_album,
    insertar_cancion,
    insertar_genero,
    insertar_artista,
    insertar_url_descarga,
    vincular_artista_cancion,
    vincular_cancion_album,
    vincular_genero_cancion
)


logger = PipelineLog.get_logger(__name__)

# =======================
# FUNCIONES AUXILIARES
# =======================


def _obtener_o_insertar_artista(
        clase_artista: Artista,
        codigo_identificador: int,
        db: Path | None = None
    ) -> SalidaArtista:
    """Busca un artista y lo inserta solo si no existe.

    El proceso revisa primero si ya está registrado localmente, y en caso de
    existir incorpora su código externo si corresponde. Si no existe, se inserta
    y se registra su código.

    Args:
        clase_artista: Objeto con los datos del artista a procesar.
        codigo_identificador: Identificador externo asociado a la API.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Un objeto :class:`SalidaArtista` con el identificador local y el nombre.

    Raises:
        ValueError: Si la operación no devuelve una salida válida.
    """
    # Búsqueda Inicial
    resultado_artista = buscar_artista_cod(
        nombre=clase_artista.nombre,
        codigo_ident= codigo_identificador,
        db=db
    )
    # Si es que existe.
    if resultado_artista:
        #logger.debug(f"Art: {resultado_artista.nombre}. ID: {resultado_artista.id_local}.")
        # Revisión de códigos
        if clase_artista.codigo:
            # Si no está, se inserta. Si está, pass
            if not resultado_artista.revisar_codigo(clase_artista.codigo):
                val = insertar_codigo(
                    id_entidad=resultado_artista.id_local,
                    ident=codigo_identificador,
                    tipo="artista",
                    codigo=clase_artista.codigo,
                    db=db
                )
    
    # Si no existe, Inserción de la Clase
    else:
        id_local = insertar_artista(clase_artista, db)
        logger.debug(f"Artista '{clase_artista.nombre}' Insertado. ID: {id_local}.")
        if clase_artista.codigo:
            insertar_codigo(
                id_entidad=id_local,
                ident=codigo_identificador,
                tipo="artista",
                codigo=clase_artista.codigo,
                db=db
            )
            #logger.debug("Codigo Insertado.")
        resultado_artista = SalidaArtista(
            id_local=id_local,
            nombre=clase_artista.nombre
        )
    if not resultado_artista:
        raise ValueError(f"La función de inserción no retornó una salida válida. {clase_artista.nombre}")
    return resultado_artista

def _gestionar_canciones(
        clase_cancion: Cancion,
        id_artista: int,
        codigo_ident: int,
        lista_colabs: List[int],
        db: Path | None = None
) -> Tuple[int, bool]:
    """Gestiona la inserción o reutilización de una canción para un artista.

    Busca si la canción ya existe para el artista y, si es así, comprueba que
    los colaboradores coincidan. Si no existe, la inserta y registra su código.

    Args:
        clase_cancion: Objeto con los datos de la canción a procesar.
        id_artista: Identificador local del artista principal.
        codigo_ident: Identificador externo asociado a la API.
        lista_colabs: Lista de identificadores de artistas colaboradores.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        Tupla con el identificador local de la canción y un valor booleano que
        indica si la canción ya estaba vinculada.
    """
    # Obtener las canciones del artista
    id_cancion = 0
    vinculado = False
    canciones_artista = buscar_canciones_artista_cod(
        id_artista=id_artista,
        codigo_ident=codigo_ident,
        db=db
        )

    # Si tiene canciones registradas.
    if canciones_artista:
        for can in canciones_artista:
            if can.coincide_con(clase_cancion):
                # Comparar colaboradores
                lista = buscar_col_ft_cancion(can.id_local, db)
                if lista.sort() == lista_colabs.sort():
                    id_cancion = can.id_local
                    vinculado = True
                    #logger.debug(f"Can: {clase_cancion.titulo}. ID: {id_cancion}.")
                    break

    # Si no tiene canciones o no está registrada
    if not id_cancion:
        id_cancion = insertar_cancion(
            cancion=clase_cancion,
            revisado=False, 
            db=db
        )
        logger.debug(f"Cancion '{clase_cancion.titulo}' Insertada. ID: {id_cancion}.")

    # Gestion de código, si es que lo tiene.
    if clase_cancion.codigo:
        val = insertar_codigo(
            id_entidad=id_cancion,
            ident=codigo_ident,
            tipo="cancion",
            codigo=clase_cancion.codigo,
            db=db
        )
        #logger.debug("Codigo Insertado.")
    return (id_cancion, vinculado)

def _gestionar_albumes(
        clase_album: Album,
        id_artista: int,
        codigo_ident: int,
        db: Path | None = None
) -> int:
    """Gestiona la inserción o reutilización de un álbum para un artista.

    Busca si el álbum ya está registrado para el artista; si no lo está, lo
    inserta y registra su código externo.

    Args:
        clase_album: Objeto con los datos del álbum a procesar.
        id_artista: Identificador local del artista principal.
        codigo_ident: Identificador externo asociado a la API.
        db: Ruta de la base de datos. Si es ``None``, se usa la ruta por defecto.

    Returns:
        El identificador local del álbum gestionado.
    """
    # Obtener los álbumes del artista
    id_album = 0
    lista_alb = buscar_albumes_artista_cod(
        id_artista=id_artista,
        codigo_ident=codigo_ident,
        db=db
    )
    if lista_alb:
        for alb in lista_alb:
            if alb.coincide_con(clase_album):
                id_album = alb.id_local
                #logger.debug(f"Alb: {alb.titulo}. ID: {id_album}.")
                break
    if not id_album:
        id_album = insertar_album(
            album=clase_album, 
            id_artista=id_artista,
            revisado=False, 
            db=db
        )
        logger.debug(f"Álbum '{clase_album.titulo}' Insertado. ID: {id_album}.")
    if clase_album.codigo:
        val = insertar_codigo(
            id_entidad=id_album,
            ident=codigo_ident,
            tipo="album",
            codigo=clase_album.codigo,
            db=db
        )

    return id_album


'''
INFO	¿Qué está haciendo el programa?
DEBUG	¿Cómo lo está haciendo?
WARNING	¿Ocurrió algo inesperado pero recuperable?
ERROR	¿Falló una operación?
CRITICAL	¿El programa no puede continuar?
'''

# =======================
# PIPELINE PRINCIPAL
# =======================


def pipeline_insertar_paquete(
        paquete_datos: PaqueteDatos, 
        codigo_ident: int,
        ruta_base_datos: Path | None = None
    ) -> None:
    """Inserta un paquete de datos completo en la base de datos local.

    El pipeline procesa el género, el artista principal, los artistas
    colaboradores, el álbum y la canción, y finalmente vincula todas las
    entidades entre sí.

    Args:
        paquete_datos: Objeto con la información del paquete a insertar.
        codigo_ident: Identificador externo asociado a la API.
        ruta_base_datos: Ruta de la base de datos. Si es ``None``, se usa la ruta
            por defecto.
    """
    clase_genero = paquete_datos.genero
    clase_artistas = paquete_datos.artistas
    clase_album = paquete_datos.album
    clase_cancion = paquete_datos.cancion

    # Obtener o insertar Genero
    id_genero = 0
    if clase_genero:
        id_genero = buscar_genero(nombre_genero=clase_genero.nombre, db=ruta_base_datos)
        if not id_genero:
            id_genero = insertar_genero(genero=clase_genero, db=ruta_base_datos)
            logger.debug(f"Genero '{clase_genero.nombre}' Insertado. ID {id_genero}")

    sal_art = _obtener_o_insertar_artista(
        clase_artista=clase_artistas.principal,
        codigo_identificador=codigo_ident,
        db=ruta_base_datos
    )
    id_artista = sal_art.id_local

    # Obtener o insertar Artistas Colaboradores - Feature
    ids_colab: List[int] = []
    for colab in (clase_artistas.colaboradores or []):
        sal = _obtener_o_insertar_artista(
            clase_artista=colab,
            codigo_identificador=codigo_ident,
            db=ruta_base_datos
        )
        ids_colab.append(sal.id_local)
    
    ids_ft: List[int] = []
    for feat in (clase_artistas.feat or []):
        sal = _obtener_o_insertar_artista(
            clase_artista=feat,
            codigo_identificador=codigo_ident,
            db=ruta_base_datos
        )
        ids_ft.append(sal.id_local)
    
    id_album = _gestionar_albumes(
        clase_album=clase_album,
        id_artista=id_artista,
        codigo_ident=codigo_ident,
        db=ruta_base_datos
    )

    (id_cancion, vinculado) = _gestionar_canciones(
        clase_cancion=clase_cancion,
        id_artista=id_artista,
        codigo_ident=codigo_ident,
        lista_colabs=ids_colab+ids_ft or [],
        db=ruta_base_datos
    )

    logger.debug(f"Local IDs | Art:{id_artista} - Alb:{id_album} - Can:{id_cancion} - Gen:{id_genero}")
    # -------------------
    # Vincular los datos
    # -------------------
    if id_genero:
        try:
            vincular_genero_cancion(
                id_genero=id_genero,
                id_cancion=id_cancion,
                db=ruta_base_datos
            )
            #logger.debug("Genero y Canción vinculados correctamente.")
        except sqlite3.IntegrityError:
            #logger.debug("Genero y Canción ya vinculados.")
            pass
    try:
        vincular_cancion_album(
            id_cancion=id_cancion,
            id_album=id_album,
            nro_pista=clase_cancion.num_pista,
            db=ruta_base_datos
        )
        #logger.debug("Canción y Álbum vinculados Correctamente.")
    except sqlite3.IntegrityError:
        #logger.debug("Canción y Álbum ya vinculados.")
        pass

    if not vinculado:
        try:
            vincular_artista_cancion(
                id_artista=id_artista,
                id_cancion=id_cancion,
                rol="Principal",
                db=ruta_base_datos
            )
            for c in ids_colab:
                vincular_artista_cancion(c, id_cancion, "Colaborador", ruta_base_datos) 
            for f in ids_ft:
                vincular_artista_cancion(f, id_cancion, "Feature", ruta_base_datos)
            #logger.debug("Artista(s) y Canción Vinculados Correctamente.")
        except ErrorVincularDatos:
            raise

    if clase_album.url_descarga:
        try:
            val = insertar_url_descarga(
                album_id=id_album,
                url_descarga=clase_album.url_descarga,
                fecha= date.today(),
                revisado=False,
                db=ruta_base_datos
            )
        except Exception as identifier:
            logger.debug(f"No se pudo insertar la url del álbum '{id_album}'. ")

def pipeline_insertar_canciones_de_album(
        paquete_album: PaqueteDatos
) -> None:
    pass