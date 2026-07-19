from pathlib import Path
from typing import List

from config.settings import get_connection
from models.schemas_v5 import SalidaArtista, Artista, PaqueteDatos, Codigo
from database.ident import insertar_codigo



# ==========

def _obtener_o_insertar_artista(clase_artista: Artista, entidad: str, db: Path | None = None) -> SalidaArtista:
    """
    Patrón: busca primero, inserta solo si no existe.
    Retorna clase predefinida.
    """
    resultado = buscar_artista(clase_artista.nombre, db)
    if not resultado:
        id_local = insertar_artista(clase_artista, db)
        resultado = SalidaArtista(
            id_local=id_local,
            nombre=clase_artista.nombre
        )
    if not resultado:
        raise ValueError(f"La función de inserción no retornó una salida válida. {entidad}")

    return resultado

def pipeline_insertar_paquete(
        paquete_datos: PaqueteDatos, 
        codigo_ident: int,
        ruta_base_datos: Path | None = None
    ) -> None:
    "Pipeline para registrar un Paquete de Datos"
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


    # Obtener o insertar Artista Principal
    art_principal = clase_artistas.principal
    id_artista = 0
    if art_principal:
        art = buscar_artista(art_principal.nombre, ruta_base_datos)
        if not art:
            id_artista = insertar_artista(art_principal, ruta_base_datos)
        else:
            id_artista = art.id_local
    # Obtener los álbumes del artista
    id_album = 0
    lista_alb = buscar_albumes_artista(id_artista=id_artista, db=ruta_base_datos)
    if lista_alb:
        for alb in lista_alb:
            if alb.coincide_con(clase_album):
                id_album = alb.id_local
                break
    if not id_album:
        id_album = insertar_album(clase_album, id_artista, id_genero, False, ruta_base_datos)

    # Obtener las canciones del álbum
    id_cancion = 0
    lista_canciones = buscar_canciones_artista(id_artista, ruta_base_datos)
    if lista_canciones:
        for can in lista_canciones:
            if can.coincide_con(clase_cancion):
                id_cancion = can.id_local
                break
    if not id_cancion:
        id_cancion = insertar_cancion(clase_cancion, False, ruta_base_datos)
    print(f"G{id_genero} - C{id_cancion} - A{id_album} - Ar{id_artista}")
    # -------------------
    # Vincular los datos
    # -------------------
    if id_genero:
        vincular_genero_cancion(
            id_genero=id_genero,
            id_cancion=id_cancion,
            db=ruta_base_datos
        )
    else:
        raise ValueError(f"Genero-Cancion: {clase_cancion.titulo}")

    vincular_cancion_album(
        id_cancion=id_cancion,
        id_album=id_album,
        nro_pista=clase_cancion.num_pista,
        db=ruta_base_datos
    )

    vincular_artista_cancion(
        id_artista=id_artista,
        id_cancion=id_cancion,
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
        vincular_artista_cancion(sal.id_local, id_cancion, "Colaborador", ruta_base_datos) 

    # Vincular featurings
    for nombre_feat in (clase_artistas.feat or []):
        ft_aux = Artista(nombre=nombre_feat)
        sal = _obtener_o_insertar_artista(
            clase_artista=ft_aux,
            entidad="Artista Feature",
            db=ruta_base_datos
        )
        vincular_artista_cancion(sal.id_local, id_cancion, "Feature", ruta_base_datos)

    # Codigos
    if codigo_ident:
        if art_principal.codigo:
            cod_art = Codigo(
                tabla_id=id_artista,
                api_id=codigo_ident,
                codigo_ext=art_principal.codigo
            )
            insertar_codigo(cod_art, "artista", ruta_base_datos)
        if clase_album.codigo:
            cod_alb = Codigo(
                tabla_id=id_album,
                api_id=codigo_ident,
                codigo_ext=clase_album.codigo
            )
            insertar_codigo(cod_alb, "album", ruta_base_datos)
        if clase_cancion.codigo:
            cod_can=Codigo(
                tabla_id=id_cancion,
                api_id=codigo_ident,
                codigo_ext=clase_cancion.codigo
            )
            insertar_codigo(cod_can, "cancion", ruta_base_datos)
    else:
        raise ValueError(f"Sin Codigos")
