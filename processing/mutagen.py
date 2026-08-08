from pathlib import Path
from typing import List

from models.schemas_v5 import DatosMusica, PaqueteDatos
from utils.id3 import escribir_tags, incrustar_portada


def _paquete_to_datos_musica(paquete: PaqueteDatos) -> DatosMusica:
    cls_alb = paquete.album
    cls_can = paquete.cancion
    cls_art = paquete.artistas
    cls_gen = paquete.genero

    artistas: List[str] = []
    for c in cls_art.colaboradores or []:
        artistas.append(c.nombre)
    for f in cls_art.feat or []:
        artistas.append(f.nombre)

    gen = "Desconocido"
    if cls_gen:
        gen = cls_gen.nombre

    return DatosMusica(
        titulo=cls_can.titulo,
        album=cls_alb.titulo,
        artista_principal=cls_art.principal.nombre,
        artistas_colab=artistas,
        anio=cls_alb.lanzamiento.year,
        num_pista=cls_can.num_pista,
        genero=gen
    )

# ---------------------------------------------------------------------------
# PIPELINE PRINCIPAL
# ---------------------------------------------------------------------------


def pipeline_mutagen(ruta_mp3: Path, paquete: PaqueteDatos, ruta_img: Path) -> Path:
    '''
    Inserta los datos al archivo
    '''

    # Adaptador
    datos = _paquete_to_datos_musica(paquete=paquete)

    escribir_tags(ruta_mp3, datos)

    incrustar_portada(ruta_mp3, ruta_img)

    return ruta_mp3