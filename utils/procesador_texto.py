import re
from typing import Protocol, List

class ProcesadorTexto(Protocol):
    def procesar(self, texto: str) -> str:
        ...

class Espacios:
    "Elimina los espacios y las irregularidades"
    def procesar(self, texto: str) -> str:
        if not texto:
            return ""
        return " ".join(texto.split())

class Fallback:
    "Aplica un valor por defecto si el texto está vacío."
    def __init__(self, valor_fallback: str = "No definido") -> None:
        self.fallback = valor_fallback

    def procesar(self, texto: str) -> str:
        return texto if texto.strip() else self.fallback

class Titulo:
    "Formatea para los títulos"
    def procesar(self, texto: str) -> str:
        if not texto:
            return texto
        return texto.title()

class Formato:
    """Capitaliza títulos respetando excepciones (stop words) y puntuación."""
    
    STOP_WORDS = {
        # Español
        "el", "la", "los", "las", "un", "una", "y", "o", "u", "e", 
        "de", "del", "en", "por", "para", "con", "a", "al",
        # Inglés
        "the", "a", "an", "and", "or", "of", "in", "on", "for", "with", "to"
    }

    def procesar(self, texto: str) -> str:
        if not texto:
            return texto

        # 1. Normalizamos todo a minúsculas como base
        texto = texto.lower()

        # 2. Función callback: Regex llamará a esto por cada palabra que encuentre
        def _capitalize_match(match) -> str:
            palabra = match.group(0)

            if palabra in self.STOP_WORDS:
                return palabra
            
            return palabra.capitalize()

        # 3. Aplicamos Regex. 
        con_formato = re.sub(r'[a-záéíóúüñ]+', _capitalize_match, texto)

        # 4. La primera letra del título SIEMPRE debe ser mayúscula,
        if con_formato:
            return con_formato[0].upper() + con_formato[1:]
        
        return con_formato


class Diagonal:
    "Limpia los 'slash' para evitar errores"
    def procesar(self, texto: str) -> str:
        if not texto:
            return texto
        return texto.replace("/", "-")

# Motor (Pipeline)
class PipelineLimpiezaTexto:
    def __init__(self, procesos: List[ProcesadorTexto]):
        self.procesos = procesos

    def ejecutar(self, texto: str) -> str:
        resultado = texto
        for p in self.procesos:
            resultado = p.procesar(resultado)
        return resultado


pipeline_album = PipelineLimpiezaTexto(
    [
        Espacios(),
        Formato(),
        Fallback("Sin Álbum")
    ]
)

pipeline_titulo = PipelineLimpiezaTexto(
    [
        Espacios(),
        Diagonal(),
        Formato(),
        Fallback("Sin Título")
    ]
)

pipeline_genero = PipelineLimpiezaTexto(
    [
        Espacios(),
        Titulo(),
        Fallback("Desconocido")
    ]
)

pipeline_artistas = PipelineLimpiezaTexto(
    [
        Espacios(),
        Titulo(),
        Diagonal(),
        Fallback("")
    ]
)

pipeline_art_prin = PipelineLimpiezaTexto(
    [
        Espacios(),
        Titulo(),
        Diagonal(),
        Fallback("Sin Artista")
    ]
)

if __name__ == "__main__":
    alb = pipeline_titulo.ejecutar("La vida como un viaje no una estación")
    print(alb)