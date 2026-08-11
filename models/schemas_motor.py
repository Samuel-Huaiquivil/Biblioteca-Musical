# models/schemas_motor.py
from dataclasses import dataclass, field
from collections.abc import Callable
from datetime import date
from typing import List, Tuple, Any

from models.schemas_v5 import PaqueteDatos


@dataclass
class ItemNormalizado:
    titulo_album: str = ""
    lanzamiento: str = ""
    artista_principal: str = ""
    codigo_album: str = ""
    url_descarga: str = ""
    ptje_referencia: int = 0
    titulo_version: str = ""


    def formatear_fecha(self) -> str:
        try:
            fecha = date.fromisoformat(self.lanzamiento[:10])
            return fecha.strftime("%d/%m/%Y")
        except ValueError:
            return self.lanzamiento

    def to_dict(self):
        return {
            "Titulo Album": self.titulo_album,
            "Lanzamiento": self.lanzamiento,
            "Artista Prin.": self.artista_principal,
            "Codigo Album": self.codigo_album,
            "Puntaje Ref.": self.ptje_referencia,
            "URL": self.url_descarga
        }

    def comparar_paquete(self, paquete: PaqueteDatos) -> bool:
        "Compara el Item Normalizado con un Paquete Datos"
        cls_alb = paquete.album
        if self.codigo_album == cls_alb.codigo:
            return True
        else:
            return False

# ---------------------------------------------------------------------------
# Modelo para clasificar y puntuar Datos
# ---------------------------------------------------------------------------


@dataclass(order=True)
class Puntuador:
    """Contiene un ítem con su puntaje y análisis de reglas.

    Attributes:
        puntaje (float): Puntaje acumulado del ítem.
        item (ItemNormalizado): Datos del ítem evaluado.
        analisis (dict[str, float]): Desglose del puntaje por regla.
    """
    puntaje: float
    item: ItemNormalizado = field(compare=False)
    analisis: dict[str, float] = field(compare=False, default_factory=dict)

    def __str__(self) -> str:
        cod = self.item.codigo_album
        return f"Puntuador[{self.puntaje}, Cod:{cod} - Análisis: {self.analisis}]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "puntaje": self.puntaje,
            "item": self.item.to_dict(),
            "analisis": self.analisis
        }

    def obtener_url(self) -> str:
        return self.item.url_descarga or ""



@dataclass
class DatosLote:
    """Agrupa los datos estadísticos de un lote de items.

    Attributes:
        moda_tit (str): Título más frecuente del lote.
        moda_art (str): Artista más frecuente del lote.
        fecha_min (str): Fecha mínima encontrada en el lote.
    """
    moda_tit: str = ""
    moda_art: str = ""
    fecha_min: str = ""


class MotorPuntuador:
    """Aplica validaciones y reglas de puntuación sobre un conjunto de items.

    Attributes:
        validadores (List[Callable[[ItemNormalizado], bool]]): Funciones que validan un item.
        reglas (List[Callable[[ItemNormalizado, DatosLote], Tuple[str, float]]]): Reglas que asignan puntos.
    """
    def __init__(
            self,
            validadores: List[Callable[[ItemNormalizado], bool]],
            reglas: List[Callable[[ItemNormalizado, DatosLote], Tuple[str, float]]]
    ) -> None:
        self.validadores = validadores
        self.reglas = reglas

    def puntuar(
            self, 
            items: List[ItemNormalizado],
            lote: DatosLote
        ) -> Tuple[List[Puntuador], List[ItemNormalizado]]:

        # Filtrado y Validación
        items_validos: List[ItemNormalizado] = []
        items_descartados: List[ItemNormalizado] = []

        for item in items:
            if all(validador(item) for validador in self.validadores):
                items_validos.append(item)
            else:
                items_descartados.append(item)

        if not items_validos:
            return [], items_descartados

        # Calculo individual
        puntaje_calculado = []
        for item in items_validos:
            puntaje = 0.0
            analisis = {}

            for regla in self.reglas:
                referencia, puntos = regla(item, lote)
                analisis[referencia] = puntos
                puntaje += puntos

            puntaje_calculado.append(
                Puntuador(
                    puntaje=round(puntaje * 100, 2),
                    item=item,
                    analisis=analisis
                )
            )
        return sorted(puntaje_calculado, reverse=True), items_descartados


