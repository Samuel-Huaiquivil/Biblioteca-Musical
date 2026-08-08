# CLASE LOGGING
import json
import logging
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Convierte cada registro de log en una línea JSON (formato JSON Lines).
    Esto permite usar mode="a" sin romper la validez del archivo,
    ya que cada línea es un objeto JSON independiente.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        extra_data = getattr(record, "extra_data", None)
        if extra_data:
            log_entry["detalle"] = extra_data

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class PipelineLog:
    _configurado = False

    @classmethod
    def setup(cls, ruta_log: Path) -> None:
        if cls._configurado:
            return

        logger = logging.getLogger("pipeline")
        logger.setLevel(logging.DEBUG)

        formatter_archivo = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        formatter_consola = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )

        handler_archivo = logging.FileHandler(
            ruta_log,
            mode="w",
            encoding="utf-8",
        )
        handler_archivo.setLevel(logging.DEBUG)
        handler_archivo.setFormatter(formatter_archivo)

        handler_consola = logging.StreamHandler()
        handler_consola.setLevel(logging.INFO)
        handler_consola.setFormatter(formatter_consola)

        ruta_json = ruta_log.parent
        handler_json = logging.FileHandler(
            filename=ruta_json / "pipeline_debug.json",
            mode="w",
            encoding="utf-8",
            delay=True,
        )
        handler_json.setLevel(logging.WARNING)
        handler_json.setFormatter(JSONFormatter())

        logger.addHandler(handler_json)
        logger.addHandler(handler_archivo)
        logger.addHandler(handler_consola)

        cls._configurado = True

    @classmethod
    def get_logger(cls, modulo: str):
        return logging.getLogger(f"pipeline.{modulo}")

    def __init__(self, modulo) -> None:
        self._logger = self.get_logger(modulo)

    def debug(self, mensaje: str, extra: dict | None = None):
        self._logger.debug(msg=mensaje, extra=self._empaquetar(extra))

    def info(self, mensaje: str, extra: dict | None = None):
        self._logger.info(msg=mensaje, extra=self._empaquetar(extra))

    def warning(self, mensaje: str, extra: dict | None = None):
        self._logger.warning(msg=mensaje, extra=self._empaquetar(extra))

    def error(self, mensaje: str, extra: dict | None = None, exc_info: bool = False):
        self._logger.error(msg=mensaje, extra=self._empaquetar(extra), exc_info=exc_info)

    def proceso(self, nombre: str):
        self._logger.info(msg=f"Iniciando el Proceso: {nombre}")

    @staticmethod
    def _empaquetar(extra: dict | None) -> dict | None:
        """
        logging.Logger.warning(..., extra=...) exige que las claves de 'extra'
        no choquen con atributos internos de LogRecord (name, message, args, etc.).
        Por eso guardamos el dict del usuario dentro de una sola clave segura:
        'extra_data', que luego el JSONFormatter sabe leer.
        """
        if not extra:
            return None
        return {"extra_data": extra}