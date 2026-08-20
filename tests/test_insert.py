import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from database.insert import insertar_artista
from models.schemas_v5 import Artista
from utils.errores import ErrorInsercionLocal


class TestInsertarArtista(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "test.sqlite3"
        connection = sqlite3.connect(self.db)
        connection.execute(
            """
            CREATE TABLE Artistas (
                id_artista INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_artista TEXT UNIQUE NOT NULL COLLATE NOCASE
            )
            """
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inserta_nombre_recortado_y_devuelve_id(self):
        artista_id = insertar_artista(Artista(nombre="  Bjork  "), self.db)

        self.assertEqual(1, artista_id)
        connection = sqlite3.connect(self.db)
        row = connection.execute(
            "SELECT id_artista, nombre_artista FROM Artistas"
        ).fetchone()
        connection.close()
        self.assertEqual((1, "Bjork"), row)

    def test_devuelve_id_existente_sin_insertar_duplicado(self):
        artista_id = insertar_artista(Artista(nombre="Bjork"), self.db)

        self.assertEqual(artista_id, insertar_artista(Artista(nombre="BJORK"), self.db))
        connection = sqlite3.connect(self.db)
        count = connection.execute("SELECT COUNT(*) FROM Artistas").fetchone()[0]
        connection.close()
        self.assertEqual(1, count)

    def test_rechaza_nombre_vacio_o_compuesto_solo_por_espacios(self):
        for nombre in ("", "   "):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ValueError):
                    insertar_artista(Artista(nombre=nombre), self.db)

    def test_envuelve_error_de_conexion(self):
        db_inexistente = Path(self.temp_dir.name) / "missing" / "database.sqlite3"

        with self.assertRaises(ErrorInsercionLocal) as context:
            insertar_artista(Artista(nombre="Artist"), db_inexistente)

        error = context.exception
        self.assertEqual("Artista", error.tabla)
        self.assertEqual("Artist", error.datos)
        self.assertIsNotNone(error.__cause__)


if __name__ == "__main__":
    unittest.main()
