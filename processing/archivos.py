# Gestión de carátulas
import requests
from pathlib import Path
from config.settings import get_connection
from models.schemas import DatosCaratula, RespuestaItunes
from utils.errores import ErrorInsercion


def guardar_enlace_caratula(resultado: RespuestaItunes, db: Path | None = None) -> None:
    return None

def guardar_imagen_caratula(resultado: RespuestaItunes, db: Path | None = None) -> bool:
    '''
    Toma una clase RespuestaItunes y almacena la imagen del Album en la base de datos.
    Retorna True si sale todo bien, de lo contrario False.
    '''
    for prop in ["artworkUrl100", "artworkUrl60", "artworkUrl30"]:
        url = getattr(resultado, prop)
        if url:
            try:
                respuesta = requests.get(url, timeout=10)
                respuesta.raise_for_status() 
                imagen_bytes = respuesta.content
                with get_connection(db) as conn:
                    cursor = conn.execute(
                    "INSERT OR IGNORE INTO Caratulas (url_caratula, imagen_bytes, id_album) VALUES (?, ?, ?);",
                    (url, imagen_bytes, )
                    )
                    conn.commit()
                    val =  cursor.lastrowid or 0
                if val:
                    return True
            except Exception as e:
                raise ErrorInsercion("Carátula", str(e)) from e
    return False
