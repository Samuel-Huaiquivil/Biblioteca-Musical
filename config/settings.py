# config/settings.py
# Adaptadores, convertidores y conexión centralizada a SQLite3.
import sqlite3
from datetime import date
from pathlib import Path
from config.setup import RUTA_DATABASE

# ---------------------------------------------------------------------------
# Adaptadores: Python → SQLite (al guardar)
# ---------------------------------------------------------------------------

def _adaptar_bool(valor: bool) -> int:
    return 1 if valor else 0

def _adaptar_fecha(valor: date) -> str:
    return valor.isoformat()

sqlite3.register_adapter(bool, _adaptar_bool)
sqlite3.register_adapter(date, _adaptar_fecha)

# ---------------------------------------------------------------------------
# Convertidores: SQLite → Python (al leer)
# ---------------------------------------------------------------------------
def _convertir_bool(valor: bytes) -> bool:
    return bool(int(valor.decode("utf-8")))

def _convertir_fecha(valor: bytes) -> date:
    return date.fromisoformat(valor.decode("utf-8"))

sqlite3.register_converter("BOOLEAN", _convertir_bool)
sqlite3.register_converter("DATE", _convertir_fecha)

# -------------------
def get_connection(base_datos: Path | None = RUTA_DATABASE) -> sqlite3.Connection:
    """
    Retorna una conexión SQLite con adaptadores y convertidores activos.
    Siempre usar esta función — nunca sqlite3.connect() directo.
    """
    if not base_datos:
        conn = sqlite3.connect(
            str(RUTA_DATABASE),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
    else:
        conn = sqlite3.connect(
            str(base_datos),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn



