import re
from typing import List

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

