from typing import List, Tuple, Optional
from pathlib import Path

from utils.logging_class import PipelineLog
from models.schemas_v5 import PaqueteDatos, Cancion, Album, GrupoArtistas, Artista, Genero
from database.ident import obtener_codigos_entidad
from database.busqueda import (
    buscar_artista, 
    buscar_artistas_id, 
    buscar_canciones_artista, 
    buscar_cancion_en_album, 
    buscar_col_ft_cancion, 
    buscar_genero_cancion
)

logger = PipelineLog(__name__)

def busqueda_datos_locales(
        artista: str,
        titulo: str,
        lista_caratulas: List[Path],
        base_datos: Path | None = None
) -> Tuple[Optional[PaqueteDatos], Optional[Path]]:
    """
    Busca metadatos de una canción local priorizando álbumes con carátula física.
    """
    resp_vacia: Tuple[None, None] = (None, None)

    logger.debug(f"Iniciando búsqueda para: {artista} - {titulo}")

    # 1. Crear un diccionario de carátulas para búsqueda instantánea
    mapa_caratulas = {ruta.stem: ruta for ruta in lista_caratulas}

    # 2. Buscar al artista
    sal_artista = buscar_artista(nombre_artista=artista, db=base_datos)
    if not sal_artista:
        logger.info(f"Artista '{artista}' no encontrado en DB.")
        return resp_vacia

    # 3. Buscar la canción
    lista_canciones = buscar_canciones_artista(id_artista=sal_artista.id_local, db=base_datos)
    if not lista_canciones:
        logger.info(f"El artista '{artista}' no tiene canciones registradas.")
        return resp_vacia

    sal_cancion = next((c for c in lista_canciones if c.titulo.lower() == titulo.lower()), None)
    if not sal_cancion:
        logger.info(f"Canción '{titulo}' no encontrada para el artista '{artista}'.")
        return resp_vacia

    # 4. Buscar los álbumes donde aparece esta canción específica
    lista_albumes_nro = buscar_cancion_en_album(id_cancion=sal_cancion.id_local, db=base_datos)
    if not lista_albumes_nro:
        logger.warning(f"La canción '{titulo}' existe pero no está vinculada a ningún álbum.")
        return resp_vacia

    # 5. Clasificar los álbumes
    albumes_con_img = []
    albumes_sin_img = []

    for album, nro_pista in lista_albumes_nro:
        codigos = obtener_codigos_entidad(id_tabla=album.id_local, tipo="album", db=base_datos) or []
        
        ruta_encontrada = next((mapa_caratulas[cod] for cod in codigos if cod in mapa_caratulas), None)

        if ruta_encontrada:
            albumes_con_img.append((album, nro_pista, ruta_encontrada))
        else:
            albumes_sin_img.append((album, nro_pista, None))

    # 6. Selección del álbum óptimo
    if albumes_con_img:
        albumes_con_img.sort(key=lambda x: x[0].lanzamiento)
        album_elegido, nro_elegido, ruta_elegida = albumes_con_img[0]
        logger.debug(f"Álbum con carátula seleccionado: {album_elegido.titulo}")
    else:
        albumes_sin_img.sort(key=lambda x: x[0].lanzamiento)
        album_elegido, nro_elegido, ruta_elegida = albumes_sin_img[0]
        logger.debug(f"Álbum sin carátula seleccionado: {album_elegido.titulo}")

    # 7. Consultar datos adicionales
    id_colab = buscar_col_ft_cancion(id_cancion=sal_cancion.id_local, db=base_datos)
    nombres_colab = buscar_artistas_id(lista_ids=id_colab, db=base_datos) if id_colab else []
    generos = buscar_genero_cancion(id_cancion=sal_cancion.id_local, db=base_datos)

    # 8. Construcción del Paquete
    can_obj = Cancion(titulo=sal_cancion.titulo, num_pista=nro_elegido)
    alb_obj = Album(titulo=album_elegido.titulo, lanzamiento=album_elegido.lanzamiento)
    
    lista_colab = [Artista(nombre=col) for col in nombres_colab]
    grp_art = GrupoArtistas(
        principal=Artista(nombre=sal_artista.nombre),
        feat=lista_colab
    )
    
    gen_str = ", ".join(generos) if generos else "Desconocido"
    gen_obj = Genero(nombre=gen_str)

    paquete = PaqueteDatos(
        cancion=can_obj,
        album=alb_obj,
        artistas=grp_art,
        genero=gen_obj
    )

    logger.info(f"Paquete construido exitosamente para '{titulo}'.")
    return paquete, ruta_elegida

        
