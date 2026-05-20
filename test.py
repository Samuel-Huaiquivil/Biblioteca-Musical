# Consultar en la base de datos. 
from pathlib import Path
from models.schemas import Album, Artista, Cancion, Genero, GrupoArtistas
from processing.biblioteca_musical import procesar_canciones
from database.repository import buscar_cancion, busqueda_avanzada, guardar_cancion_completa

principal = Path("C:/Users/MSI/Proyectos Personales/Nueva carpeta/control")
base_datos = Path("C:/Users/MSI/Proyectos Personales/Nueva carpeta/control/Biblioteca_Musical.sqlite3")


c1 = Cancion(titulo="Hola", codigo_itunes=1)
c2 = Cancion(titulo="Hola", codigo_itunes=2)
alb1 = Album(titulo="Alb01", codigo_itunes=1)
alb2 = Album(titulo="Alb02", codigo_itunes=2)
gen = Genero(nombre="Otros")
art = Artista(nombre="Artista01", codigo_itunes=1)
gart = GrupoArtistas(principal="Artista01", codigo_itunes=1)
guardar_cancion_completa(gen, gart, alb1, c1, base_datos)
guardar_cancion_completa(gen, gart, alb2, c2, base_datos)


num = busqueda_avanzada("Hola", "Artista01", base_datos)
print(num)
'''
procesar_canciones(principal, 3, 2, False, False, False)
'''