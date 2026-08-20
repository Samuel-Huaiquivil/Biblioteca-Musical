import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from database.busqueda import (
    buscar_albumes_artista,
    buscar_artista,
    buscar_canciones_album,
)
from utils.errores import ErrorBusquedaLocal


class TestBusquedasLocales(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "test.sqlite3"
        connection = sqlite3.connect(self.db)
        connection.executescript(
            """
            CREATE TABLE Artistas (
                id_artista INTEGER PRIMARY KEY,
                nombre_artista TEXT NOT NULL COLLATE NOCASE
            );
            CREATE TABLE Albumes (
                id_album INTEGER PRIMARY KEY,
                titulo_album TEXT NOT NULL,
                pistas_totales INTEGER NOT NULL,
                fecha_lanzamiento DATE NOT NULL,
                artista_principal_id INTEGER NOT NULL
            );
            CREATE TABLE Canciones (
                id_cancion INTEGER PRIMARY KEY,
                titulo_cancion TEXT NOT NULL
            );
            CREATE TABLE Canciones_Albumes (
                id_cancion INTEGER NOT NULL,
                id_album INTEGER NOT NULL,
                numero_cancion INTEGER NOT NULL,
                PRIMARY KEY (id_cancion, id_album)
            );
            INSERT INTO Artistas VALUES (1, 'Beyonce');
            INSERT INTO Albumes VALUES (10, 'Lemonade', 12, '2016-04-23', 1);
            INSERT INTO Canciones VALUES (1, 'Second');
            INSERT INTO Canciones VALUES (2, 'First');
            INSERT INTO Canciones_Albumes VALUES (1, 10, 2);
            INSERT INTO Canciones_Albumes VALUES (2, 10, 1);
            """
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_buscar_artista_recorta_espacios_y_ignora_mayusculas(self):
        artista = buscar_artista("  BEYONCE  ", self.db)

        self.assertIsNotNone(artista)
        self.assertEqual(1, artista.id_local)
        self.assertEqual("Beyonce", artista.nombre)

    def test_buscar_artista_devuelve_none_si_no_existe(self):
        self.assertIsNone(buscar_artista("Unknown", self.db))

    def test_buscar_artista_rechaza_nombre_invalido(self):
        for nombre in ("", "   ", None, 42):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ValueError):
                    buscar_artista(nombre, self.db)

    def test_buscar_artista_envuelve_error_de_conexion(self):
        db_inexistente = Path(self.temp_dir.name) / "missing" / "database.sqlite3"

        with self.assertRaises(ErrorBusquedaLocal) as context:
            buscar_artista("Beyonce", db_inexistente)

        error = context.exception
        self.assertEqual("Artista", error.tabla)
        self.assertEqual("Beyonce", error.valor)
        self.assertEqual(error.detalles, error.data)
        self.assertIsNotNone(error.__cause__)

    def test_buscar_albumes_artista_devuelve_albumes(self):
        albumes = buscar_albumes_artista(1, self.db)

        self.assertEqual(1, len(albumes))
        self.assertEqual(10, albumes[0].id_local)
        self.assertEqual("Lemonade", albumes[0].titulo)
        self.assertEqual(12, albumes[0].pistas_totales)

    def test_buscar_albumes_artista_devuelve_lista_vacia_sin_albumes(self):
        self.assertEqual([], buscar_albumes_artista(99, self.db))

    def test_buscar_albumes_artista_rechaza_id_invalido(self):
        for id_artista in (0, -1, True, "1"):
            with self.subTest(id_artista=id_artista):
                with self.assertRaises(ValueError):
                    buscar_albumes_artista(id_artista, self.db)

    def test_buscar_canciones_album_ordena_por_numero_de_pista(self):
        canciones = buscar_canciones_album(10, self.db)

        self.assertEqual(
            [(1, "First"), (2, "Second")],
            [(cancion.numero_cancion, cancion.titulo) for cancion in canciones],
        )

    def test_buscar_canciones_album_devuelve_lista_vacia_sin_canciones(self):
        self.assertEqual([], buscar_canciones_album(99, self.db))

    def test_buscar_canciones_album_rechaza_id_invalido(self):
        for id_album in (0, -1, True, "10"):
            with self.subTest(id_album=id_album):
                with self.assertRaises(ValueError):
                    buscar_canciones_album(id_album, self.db)

    def test_buscar_canciones_album_envuelve_error_de_conexion(self):
        db_inexistente = Path(self.temp_dir.name) / "missing" / "database.sqlite3"

        with self.assertRaises(ErrorBusquedaLocal) as context:
            buscar_canciones_album(10, db_inexistente)

        error = context.exception
        self.assertEqual("Canciones_Albumes", error.tabla)
        self.assertIn("ID: 10", error.valor)
        self.assertIsNotNone(error.__cause__)


if __name__ == "__main__":
    unittest.main()
