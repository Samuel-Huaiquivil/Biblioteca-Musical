from pathlib import Path
from typing import List

from models.schemas_v5 import DatosMusica, PaqueteDatos
from utils.id3 import escribir_tags, incrustar_portada
from utils.procesador_texto import (
    pipeline_album,
    pipeline_artistas,
    pipeline_genero,
    pipeline_titulo,
    pipeline_art_prin
)

def _paquete_to_datos_musica(paquete: PaqueteDatos) -> DatosMusica:
    "Limpia los texto a través de un Pipeline."
    cls_alb = paquete.album
    cls_can = paquete.cancion
    cls_art = paquete.artistas
    cls_gen = paquete.genero

    artistas: List[str] = []
    for c in cls_art.colaboradores or []:
        art = pipeline_artistas.ejecutar(c.nombre)
        if not art:
            continue
        artistas.append(art)
    for f in cls_art.feat or []:
        art = pipeline_artistas.ejecutar(f.nombre)
        if not art:
            continue
        artistas.append(art)
        
    can_limpio = pipeline_titulo.ejecutar(cls_can.titulo)
    alb_limpio = pipeline_album.ejecutar(cls_alb.titulo)
    gro_limpio = pipeline_genero.ejecutar(cls_gen.nombre if cls_gen else "" )
    principal = pipeline_art_prin.ejecutar(cls_art.principal.nombre)
    

    return DatosMusica(
        titulo=can_limpio,
        album=alb_limpio,
        artista_principal=principal,
        artistas_colab=artistas,
        anio=cls_alb.lanzamiento.year,
        num_pista=cls_can.num_pista,
        genero=gro_limpio
    )

# ---------------------------------------------------------------------------
# PIPELINE PRINCIPAL
# ---------------------------------------------------------------------------


def pipeline_mutagen(ruta_mp3: Path, paquete: PaqueteDatos, ruta_img: Path | None = None) -> Path:
    '''
    Inserta los datos al archivo
    '''

    # Pipeline
    datos = _paquete_to_datos_musica(paquete=paquete)

    # Añadir tags Eventualmente
    escribir_tags(ruta_mp3, datos)

    if ruta_img:
        incrustar_portada(ruta_mp3, ruta_img)

    return ruta_mp3