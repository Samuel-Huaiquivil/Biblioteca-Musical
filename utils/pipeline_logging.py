# utils/pipeline_logging.py
# Sistema de logging mejorado con timestamps, niveles y contexto por canción.

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class PipelineLogger:
    """Sistema de logging centralizado para el pipeline."""
    
    def __init__(self, ruta_log: Path):
        """
        Inicializa el logger del pipeline.
        
        Args:
            ruta_log: Ruta del archivo de log
        """
        self.ruta_log = ruta_log
        self.logger = logging.getLogger("pipeline")
        
        # Evitar duplicados si ya existe handler
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self.logger.setLevel(logging.DEBUG)
        
        # Formato con timestamp
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo
        file_handler = logging.FileHandler(ruta_log, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para consola (solo INFO y superior)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, mensaje: str, archivo: Optional[str] = None) -> None:
        """Registra un mensaje informativo."""
        msg = self._formato_con_contexto(mensaje, archivo)
        self.logger.info(msg)
    
    def warning(self, mensaje: str, archivo: Optional[str] = None) -> None:
        """Registra una advertencia."""
        msg = self._formato_con_contexto(mensaje, archivo)
        self.logger.warning(msg)
    
    def error(self, mensaje: str, archivo: Optional[str] = None, excepcion: Optional[Exception] = None) -> None:
        """Registra un error."""
        msg = self._formato_con_contexto(mensaje, archivo)
        if excepcion:
            self.logger.error(msg, exc_info=excepcion)
        else:
            self.logger.error(msg)
    
    def debug(self, mensaje: str, archivo: Optional[str] = None) -> None:
        """Registra un mensaje de depuración."""
        msg = self._formato_con_contexto(mensaje, archivo)
        self.logger.debug(msg)
    
    def _formato_con_contexto(self, mensaje: str, archivo: Optional[str] = None) -> str:
        """Agrega contexto (nombre de archivo) al mensaje si está disponible."""
        if archivo:
            return f"[{archivo}] {mensaje}"
        return mensaje
    
    def inicio_procesamiento(self, num_canciones: int) -> None:
        """Registra el inicio del procesamiento."""
        self.info(f"=== INICIO PROCESAMIENTO PIPELINE ===")
        self.info(f"Canciones a procesar: {num_canciones}")
    
    def fin_procesamiento(self, total_procesadas: int, total_errores: int) -> None:
        """Registra el fin del procesamiento con resumen."""
        self.info(f"=== FIN PROCESAMIENTO PIPELINE ===")
        self.info(f"Canciones procesadas: {total_procesadas}")
        self.info(f"Errores totales: {total_errores}")
        if total_errores > 0:
            self.warning(f"Ver log para detalles de errores")
    
    def procesando_cancion(self, archivo: str, paso: str) -> None:
        """Registra que se está procesando una canción en un paso específico."""
        self.debug(f"Procesando en paso: {paso}", archivo=archivo)
    
    def cancion_encontrada_localmente(self, archivo: str, id_local: int) -> None:
        """Registra cuando se encuentra una canción en BD local."""
        self.info(f"Encontrada en BD local (id={id_local})", archivo=archivo)
    
    def cancion_consultada_itunes(self, archivo: str) -> None:
        """Registra consulta a iTunes."""
        self.debug(f"Consultando iTunes", archivo=archivo)
    
    def cancion_consultada_mbz(self, archivo: str) -> None:
        """Registra consulta a MusicBrainz."""
        self.debug(f"Consultando MusicBrainz", archivo=archivo)
