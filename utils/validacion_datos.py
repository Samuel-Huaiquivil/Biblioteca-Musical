# utils/validacion_datos.py
# Validaciones mejoradas para detectar datos inválidos ANTES de guardar en BD.

from typing import Any, Dict, Optional, Tuple
from models.schemas import Album, Cancion, GrupoArtistas, Genero


class ValidadorDatos:
    """Valida datos antes de guardarlos en la base de datos."""
    
    @staticmethod
    def validar_genero(genero: Genero) -> Tuple[bool, Optional[str]]:
        """
        Valida un objeto Genero.
        
        Returns:
            (es_valido, mensaje_error)
        """
        if not genero:
            return False, "Genero es None"
        
        if not genero.nombre or not isinstance(genero.nombre, str):
            return False, f"Nombre de género inválido: {genero.nombre}"
        
        if len(genero.nombre.strip()) == 0:
            return False, "Nombre de género está vacío"
        
        return True, None
    
    @staticmethod
    def validar_artistas(artistas: GrupoArtistas) -> Tuple[bool, Optional[str]]:
        """
        Valida un objeto GrupoArtistas.
        
        Returns:
            (es_valido, mensaje_error)
        """
        if not artistas:
            return False, "GrupoArtistas es None"
        
        if not artistas.principal or not isinstance(artistas.principal, str):
            return False, f"Artista principal inválido: {artistas.principal}"
        
        if len(artistas.principal.strip()) == 0:
            return False, "Artista principal está vacío"
        
        # Validar colaboradores si existen
        if artistas.colaboradores:
            if not isinstance(artistas.colaboradores, list):
                return False, f"Colaboradores debe ser lista, recibido: {type(artistas.colaboradores)}"
            
            for colab in artistas.colaboradores:
                if not isinstance(colab, str) or len(colab.strip()) == 0:
                    return False, f"Colaborador inválido: '{colab}'"
        
        # Validar featurings si existen
        if artistas.feat:
            if not isinstance(artistas.feat, list):
                return False, f"Featurings debe ser lista, recibido: {type(artistas.feat)}"
            
            for feat in artistas.feat:
                if not isinstance(feat, str) or len(feat.strip()) == 0:
                    return False, f"Featuring inválido: '{feat}'"
        
        return True, None
    
    @staticmethod
    def validar_album(album: Album) -> Tuple[bool, Optional[str]]:
        """
        Valida un objeto Album.
        
        Returns:
            (es_valido, mensaje_error)
        """
        if not album:
            return False, "Album es None"
        
        if not album.titulo or not isinstance(album.titulo, str):
            return False, f"Título de álbum inválido: {album.titulo}"
        
        if len(album.titulo.strip()) == 0:
            return False, "Título de álbum está vacío"
        
        if not album.lanzamiento:
            return False, "Fecha de lanzamiento es None"
        
        return True, None
    
    @staticmethod
    def validar_cancion(cancion: Cancion) -> Tuple[bool, Optional[str]]:
        """
        Valida un objeto Cancion.
        
        Returns:
            (es_valido, mensaje_error)
        """
        if not cancion:
            return False, "Cancion es None"
        
        if not cancion.titulo or not isinstance(cancion.titulo, str):
            return False, f"Título de canción inválido: {cancion.titulo}"
        
        if len(cancion.titulo.strip()) == 0:
            return False, "Título de canción está vacío"
        
        return True, None
    
    @staticmethod
    def validar_clases_completas(clases: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Valida que el diccionario de clases tenga todos los modelos requeridos
        y que sean válidos.
        
        Args:
            clases: Diccionario con 'genero', 'artistas', 'album', 'cancion'
        
        Returns:
            (es_valido, mensaje_error)
        """
        if not clases:
            return False, "Diccionario de clases es None"
        
        # Verificar que existan todas las claves
        claves_requeridas = {"genero", "artistas", "album", "cancion"}
        claves_presentes = set(clases.keys())
        
        if not claves_requeridas.issubset(claves_presentes):
            faltantes = claves_requeridas - claves_presentes
            return False, f"Faltan clases requeridas: {faltantes}"
        
        # Validar cada clase
        es_valido, error = ValidadorDatos.validar_genero(clases["genero"])
        if not es_valido:
            return False, f"Genero inválido: {error}"
        
        es_valido, error = ValidadorDatos.validar_artistas(clases["artistas"])
        if not es_valido:
            return False, f"Artistas inválido: {error}"
        
        es_valido, error = ValidadorDatos.validar_album(clases["album"])
        if not es_valido:
            return False, f"Album inválido: {error}"
        
        es_valido, error = ValidadorDatos.validar_cancion(clases["cancion"])
        if not es_valido:
            return False, f"Cancion inválido: {error}"
        
        return True, None
