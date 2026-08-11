# db/init_db.py
# Inicializa el schema de la base de datos leyendo el archivo SQL externo.

from pathlib import Path
from config.settings import get_connection
from config.setup import RUTA_DATABASE

SQL_PATH = Path(__file__).parent.parent / "models" / "SQL" / "SQLite3_v5.sql"


def iniciar_base_datos(base_datos: Path | None = RUTA_DATABASE) -> None:
    """
    Crea las tablas si no existen.
    Si no se pasa ruta, usa la ruta por defecto definida en settings.py.
    """
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"No se encontró el schema SQL en: {SQL_PATH}")

    sql = SQL_PATH.read_text(encoding="utf-8")


    with get_connection(base_datos) as conn:
        cursor = conn.cursor()
        cursor.executescript(sql)
        conn.commit()

    with get_connection(base_datos) as conn:
        query = '''
        INSERT OR IGNORE INTO Apis (nombre_api, region_api) VALUES (?, ?);
        '''
        params = [
            ("iTunes", "USA"),
            ("MusicBrainz", "Global"), 
            ("MusicBrainz", "Groups")
            ]
        res = conn.executemany(query, params)
        conn.commit()
    print("Base de datos cargada correctamente.")
