# Consultar en la base de datos. 
from pathlib import Path
from config.settings import get_connection, DB_PATH

def mostrar_todos_database(db: Path | None = None):
    try:
        with get_connection(db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nombre_artista FROM Artistas;")
            resultados = cursor.fetchall()
            print(type(resultados))
            return resultados

    except Exception as e:
        raise Exception (f"Error: {e}") from e
    
if __name__ == "__main__":
    print(mostrar_todos_database(DB_PATH))