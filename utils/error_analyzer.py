# utils/error_analyzer.py
# Módulo para capturar y registrar diccionarios que fallan durante el procesamiento.
# Permite análisis posterior para mejorar validaciones.

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ErrorAnalyzer:
    """Registra diccionarios fallidos para análisis y mejora de validaciones."""
    
    def __init__(self, ruta_log_errores: Path):
        """
        Inicializa el analizador de errores.
        
        Args:
            ruta_log_errores: Ruta donde guardar el archivo JSON de errores
        """
        self.ruta_log_errores = ruta_log_errores
        self.logger = logging.getLogger(__name__)
        
        # Crear archivo si no existe
        if not ruta_log_errores.exists():
            ruta_log_errores.write_text('[]', encoding='utf-8')
    
    def registrar_diccionario_fallido(
        self,
        diccionario: Dict[str, Any],
        tipo_error: str,
        detalle: str,
        nombre_archivo: Optional[str] = None,
        punto_fallo: Optional[str] = None
    ) -> None:
        """
        Registra un diccionario que falló durante el procesamiento.
        
        Args:
            diccionario: El diccionario que falló
            tipo_error: Tipo de error (ValidationError, ErrorInsercion, etc.)
            detalle: Descripción del error específico
            nombre_archivo: Nombre del archivo MP3 siendo procesado
            punto_fallo: Dónde falló (iTunes, MBZ, BD, Validación, etc.)
        """
        try:
            registro = {
                "timestamp": datetime.now().isoformat(),
                "nombre_archivo": nombre_archivo,
                "punto_fallo": punto_fallo,
                "tipo_error": tipo_error,
                "detalle": detalle,
                "diccionario": diccionario
            }
            
            # Leer registros existentes
            try:
                registros = json.loads(self.ruta_log_errores.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, FileNotFoundError):
                registros = []
            
            # Agregar nuevo registro
            registros.append(registro)
            
            # Guardar actualizado
            self.ruta_log_errores.write_text(
                json.dumps(registros, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8'
            )
            
            self.logger.debug(f"Diccionario fallido registrado: {punto_fallo} - {tipo_error}")
            
        except Exception as e:
            self.logger.error(f"Error al registrar diccionario fallido: {e}")
    
    def registrar_error_insercion(
        self,
        clases: Dict[str, Any],
        detalle: str,
        nombre_archivo: Optional[str] = None
    ) -> None:
        """Registra un error al insertar en BD."""
        self.registrar_diccionario_fallido(
            diccionario=clases,
            tipo_error="ErrorInsercion",
            detalle=detalle,
            nombre_archivo=nombre_archivo,
            punto_fallo="BaseDatos"
        )
    
    def registrar_error_validacion(
        self,
        diccionario: Dict[str, Any],
        detalle: str,
        nombre_archivo: Optional[str] = None
    ) -> None:
        """Registra un error de validación."""
        self.registrar_diccionario_fallido(
            diccionario=diccionario,
            tipo_error="ErrorValidacion",
            detalle=detalle,
            nombre_archivo=nombre_archivo,
            punto_fallo="Validacion"
        )
    
    def registrar_error_itunes(
        self,
        diccionario: Dict[str, Any],
        detalle: str,
        nombre_archivo: Optional[str] = None
    ) -> None:
        """Registra un error con respuesta de iTunes."""
        self.registrar_diccionario_fallido(
            diccionario=diccionario,
            tipo_error="ErrorAPI_iTunes",
            detalle=detalle,
            nombre_archivo=nombre_archivo,
            punto_fallo="iTunes"
        )
    
    def obtener_resumen(self) -> Dict[str, Any]:
        """
        Lee los registros de errores y retorna un resumen de los fallos.
        
        Returns:
            Diccionario con estadísticas de errores
        """
        try:
            registros = json.loads(self.ruta_log_errores.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "total_errores": 0,
                "por_tipo": {},
                "por_punto_fallo": {}
            }
        
        resumen = {
            "total_errores": len(registros),
            "por_tipo": {},
            "por_punto_fallo": {},
            "ultimos_errores": registros[-5:] if registros else []
        }
        
        for registro in registros:
            tipo = registro.get("tipo_error", "Desconocido")
            punto = registro.get("punto_fallo", "Desconocido")
            
            resumen["por_tipo"][tipo] = resumen["por_tipo"].get(tipo, 0) + 1
            resumen["por_punto_fallo"][punto] = resumen["por_punto_fallo"].get(punto, 0) + 1
        
        return resumen
