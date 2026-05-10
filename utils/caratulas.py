import os
import requests
from pathlib import Path
from models.schemas import DatosCaratula


def descargar_caratula(caratula: DatosCaratula, ruta_destino: Path) -> bool:
    """
    Descarga la carátula desde iTunes usando la clase proporcionada.
    Retorna True si logra descargar la carátula, False si no se pudo.
    """
    try:
        response = requests.get(caratula.url_caratula, timeout=10, stream=True)
        if response.status_code == 200:
            ruta_archivo = ruta_destino / f"{caratula.codigo_album}.jpg"
            with open(ruta_archivo, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            raise Exception(f"Error al descargar carátula iTunes. Código: {response.status_code}")

    except Exception as e:
        raise Exception(f"Error al descargar carátula iTunes: {e}") from e



