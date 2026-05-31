# models/schemas.py — agregar
from pydantic import BaseModel
from typing import Optional

from models.schemas import Cancion, Album, Genero, GrupoArtistas


class SalidaCancion(BaseModel):
    """Datos de una canción tal como están en la base de datos local."""
    id_local: int
    titulo: str
    codigo_itunes: int
    codigo_mbz: Optional[str]
    id_album: int
    titulo_album: str
    id_artista_principal: int
    nombre_artista: str

    def coincide_con(self, cancion: Cancion, album: Album) -> bool:
        """
        Compara los datos locales con los de entrada.
        Prioriza código iTunes sobre nombre para evitar falsos positivos.
        """
        if self.codigo_itunes and cancion.codigo_itunes:
            return self.codigo_itunes == cancion.codigo_itunes
        # Fallback: nombre + álbum
        return (
            self.titulo.lower() == cancion.titulo.lower() and
            self.titulo_album.lower() == album.titulo.lower()
        )