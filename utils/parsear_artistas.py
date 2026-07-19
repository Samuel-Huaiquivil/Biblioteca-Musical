import re
from dataclasses import dataclass, field
from typing import List, Optional


def normalizar_separadores(txt: str) -> str:
    """
    Convierte separadores comunes (/, \\, |, &, and, +) a comas.
    """
    if not txt:
        return ""
    #txt = txt.lower()
    reemplazos = [
        (r"[/\\|]",            ","),   # /, \, |
        (r",?\s*&\s*",         ","),   # & con o sin coma previa
        (r",?\s*\band\b\s*",   ","),   # 'and' con word boundary
        (r"\+",                ","),
    ]
    for patron, rep in reemplazos:
        txt = re.sub(patron, rep, txt)
    return txt

def suprimir_parentesis(txt: str) -> str:
    """
    Reemplaza paréntesis, corchetes y llaves por comas.
    """
    return re.sub(r"[\(\)\[\]\{\}]", ",", txt)

def normalizar_feat(txt: str) -> str:
    """
    Convierte variantes de 'feat'/'ft'/'with'/'featuring' en comas.
    """
    if not txt:
        return ""
    reemplazos = [
        (r"\bfeaturing\b\s*", ","),  # más específico primero
        (r"\bfeat\.\s*",      ","),  # punto literal escapado
        (r"\bfeat\b\s*",      ","),
        (r"\bft\.\s*",        ","),
        (r"\bft\b\s*",        ","),
        (r"\bwith\b\s*",      ","),  # word boundary: no afecta "within"
    ]
    for patron, rep in reemplazos:
        txt = re.sub(patron, rep, txt, flags=re.IGNORECASE)
    return txt

def limpiar_comas(txt: str) -> str:
    """
    Colapsa comas múltiples/consecutivas y espacios sobrantes.
    """
    txt = re.sub(r",[\s,]+", ",", txt)  # comas múltiples o con espacios
    txt = re.sub(r"\s+",     " ", txt)  # espacios múltiples
    txt = txt.strip().strip(",")        # comas y espacios en los extremos
    return txt

def conv_lista(txt: str) -> List[str]:
    """
    Divide el texto por comas y devuelve una lista sin elementos vacíos.

    BUG ORIGINAL: no filtraba strings vacíos.  Un input como "a,,b," generaba
    ["a", "", "b", ""].  Ahora se usa una comprensión de lista con filtro.
    """
    return [elem.strip() for elem in txt.split(",") if elem.strip()]


# ---------------------------------------------------------------------------
# Pipeline público
# ---------------------------------------------------------------------------

def parsear_artistas(txt: str) -> List[str]:
    """
    Pipeline completo: string con uno o varios artistas → lista normalizada.

    Orden de las etapas:
        1. normalizar_separadores  - unifica /, \\, |, &, and, + → coma
        2. suprimir_parentesis     - convierte () [] {} → coma
        3. normalizar_feat         - convierte feat/ft/with/featuring → coma
        4. limpiar_comas           - colapsa basura residual
        5. conv_lista              - split y filtrado final
    """
    txt = normalizar_separadores(txt)
    txt = suprimir_parentesis(txt)
    txt = normalizar_feat(txt)
    txt = limpiar_comas(txt)
    return conv_lista(txt)

"""
track_info.py
Extrae título, artistas y versión de strings de canciones/álbumes.

Diseño:
    En vez de hacer split() sobre "feat", se aplican patrones regex con
    grupos nombrados en cascada.  El primero que matchee gana y produce
    un TrackInfo con semántica explícita.  El parseo de artistas lo delega
    al pipeline de parsear_artistas.py.
"""



# ── Fragmentos de regex reutilizables ────────────────────────────────────────
_FEAT = r"feat(?:uring)?\.?\s*|ft\.?\s*"

# Palabras clave de versión — se expanden fácilmente agregando alternativas
_VER  = (
    r"single"
    r"|deluxe(?:\s+edition)?"
    r"|remaster(?:ed)?"
    r"|live(?:\s+version)?"
    r"|radio\s+edit"
    r"|acoustic(?:\s+version)?"
    r"|remix(?:\s+version)?"
)


_PATRONES: List[re.Pattern] = [
    re.compile(
        rf"^(?P<titulo>.+?)\s*"
        rf"\(\s*(?:{_FEAT})(?P<artistas>[^)]+)\)\s*"
        rf"(?:[–\-]\s*(?P<version>{_VER}))?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^(?P<titulo>.+?)\s*\(\s*(?P<version>{_VER})\s*\)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^(?P<titulo>.+?)\s*[–\-]\s*(?P<version>{_VER})\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        rf"^(?P<titulo>.+?)\s+(?:{_FEAT})(?P<artistas>.+?)"
        rf"(?:\s*[–\-]\s*(?P<version>{_VER}))?\s*$",
        re.IGNORECASE,
    ),
]


# ── Modelo de datos ──────────────────────────────────────────────────────────

@dataclass
class TrackInfo:
    """
    Resultado estructurado del parseo de un string de canción/álbum.

    Campos:
        titulo   - Título limpio (sin feat ni sufijo de versión).
        artistas - Lista de artistas colaboradores (puede estar vacía).
        version  - Tipo de versión si se detectó ("Single", "Live", …).
    """
    titulo:   str
    artistas: List[str]     = field(default_factory=list)
    version:  Optional[str] = None

    def __str__(self) -> str:
        partes = [f'titulo="{self.titulo}"']
        if self.artistas:
            partes.append(f"artistas={self.artistas}")
        if self.version:
            partes.append(f'version="{self.version}"')
        return f"TrackInfo({', '.join(partes)})"


# ── Función pública ──────────────────────────────────────────────────────────

def parsear_track(raw: str) -> TrackInfo:
    """
    Extrae título, artistas y versión de un string de canción/álbum.

    Estrategia:
        Aplica _PATRONES en orden; el primero que matchee produce el resultado.
        Si ninguno matchea, el string completo se considera el título.

    Args:
        raw: String crudo, p.ej. "Song (feat. A1, A2) - Single".

    Returns:
        TrackInfo con los campos completados según lo que se detectó.

    """
    for patron in _PATRONES:
        m = patron.match(raw.strip())
        if not m:
            continue
        g = m.groupdict()
        titulo   = g.get("titulo",   "").strip()
        artistas = parsear_artistas(g["artistas"]) if g.get("artistas") else []
        version  = g["version"].strip().title() if g.get("version") else None
        return TrackInfo(titulo=titulo, artistas=artistas, version=version)

    return TrackInfo(titulo=raw.strip())

