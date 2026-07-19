# config/settings.py
# Adaptadores, convertidores y conexión centralizada a SQLite3.
import sqlite3
from datetime import date
from pathlib import Path
from config.setup import DB_PATH

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
def get_connection(base_datos: Path | None = DB_PATH) -> sqlite3.Connection:
    """
    Retorna una conexión SQLite con adaptadores y convertidores activos.
    Siempre usar esta función — nunca sqlite3.connect() directo.
    """
    conn = sqlite3.connect(
        str(base_datos),
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# ===========================================================================
# BASE DATOS AUXILIAR - Para una mejor gestión de respuestas.
# ===========================================================================

path_DB = Path("C:\\Users\\MSI\\Proyectos Personales\\Biblioteca Musical\\DatosMBZ.sqlite3")
sql_path = Path("C:\\Users\\MSI\\Proyectos Personales\\Biblioteca Musical\\models\\SQL\\MBZ.sql")

def get_connect_MBZ(ruta_db: Path | None = path_DB) -> sqlite3.Connection:
    conx = sqlite3.connect(str(ruta_db))
    conx.execute("PRAGMA foreign_keys = ON;")
    return conx

def inicializar_base_datos(schema: Path = sql_path, ruta_db: Path | None = path_DB) -> None:
    """
    Inicializa la base de datos si no existe.
    """
    if not schema.exists():
        raise FileNotFoundError(f"No se encontró el schema SQL en: {schema}")

    sql = schema.read_text(encoding="utf-8")

    with get_connect_MBZ(ruta_db) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Base de datos cargada correctamente.")


