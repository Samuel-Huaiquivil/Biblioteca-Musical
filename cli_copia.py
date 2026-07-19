# Funciones a implementar
'''
Listar      Mostrar varios elementos
    -- tipo     [canciones, albumes, artistas] {canciones}
    -- estado   Revisado/No Revisado {Todos}
    -- artista  nombre artista
Detalles    Mostrar los detalles de una entidad
    -- tipo     [Cancion, Album, Artista] {Cancion}
    -- id       ID local de la entidad (int)
Muestra     Seleccionar una muestra de canciones no revisadas
    -- limite   Cantidad {5}
Revisado    Marcar revisado/no revisado
    -- tipo     [Cancion, Album]
    -- id       ID local de la entidad (int)
    -- rev      Revisado/No Revisado {Revisado} 
MBZ         Añadir información mbz
    -- tipo     [Cancion, Album, Artista]
    -- id       ID local de la entidad
    -- codigo   Codigo mbz(str)
Renombrar   Cambiar el nombre
    -- tipo     [cancion, album, artista]
    -- id       ID local de la entidad (int)
    -- nombre   nuevo nombre
'''
import click

from database import crud
from utils.errores import ErrorBaseDatos
from config.setup import DB_PATH
# Ancho de columna para la presentación en tabla
db = DB_PATH

_ANCHO = 80


# ---------------------------------------------------------------------------
# Helpers de presentación 
# ---------------------------------------------------------------------------

def _separador() -> None:
    print("-" * _ANCHO)


def _tabla(filas: list[dict]) -> None:
    """Imprime una lista de diccionarios como tabla simple."""
    if not filas:
        print("  (sin resultados)")
        return
    columnas = list(filas[0].keys())
    # Calcular anchos por columna
    anchos = {c: max(len(c), max(len(str(f.get(c, ""))) for f in filas)) for c in columnas}
    anchos = {c: min(v, 30) for c, v in anchos.items()}  # máximo 30 por columna

    encabezado = "  ".join(c.upper().ljust(anchos[c]) for c in columnas)
    print(encabezado)
    _separador()
    for fila in filas:
        linea = "  ".join(str(fila.get(c, "")).ljust(anchos[c])[:anchos[c]] for c in columnas)
        print(linea)


def _confirmar(mensaje: str) -> bool:
    """Pide confirmación antes de operaciones destructivas."""
    respuesta = input(f"  ⚠ {mensaje} [s/N]: ").strip().lower()
    return respuesta == "s"


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
'''
    _separador()
    _tabla(filas)
    print(f"\n  Total: {len(filas)} resultado(s)")
'''

@click.group()
def cli():
    """CLI para la base de datos musical."""
    pass

# ----------
# Listar
# ----------

# Listar varios
@cli.command()
@click.option('--tipo', type=click.Choice(['canciones', 'albumes', 'artistas']), default='canciones')
@click.option('--estado', type=bool, default=None)
@click.option('--artista', default=None)
def listar(tipo, estado, artista):
    """Mostrar varios elementos."""
    if tipo == 'artistas':
        filas = crud.listar_artistas(db=db)
        click.echo("Listando todos los artistas.")

    elif tipo == 'albumes':
        if artista:
            click.echo(f"Listando los álbumes de {artista}")
            filas = crud.listar_albumes_artista(nombre_artista=artista, db=db)
        else:
            filas = crud.listar_albumes(revisado=estado, db=db)
            click.echo(f"Listando los álbumes. Estado: {estado or "Todos"}. ")

    # Canciones
    else:
        if artista:
            click.echo(f"Listando las canciones de {artista}")
            filas = crud.listar_canciones_por_artista(nombre_artista=artista, db=db)
        else:
            click.echo(f"Listando las canciones. Estado: {estado or "Todos"} ")
            filas = crud.listar_canciones(revisado=estado, db=db)
    
    _separador()
    _tabla(filas)
    print(f"\n  Total: {len(filas)} resultado(s)")


# Detalles
@cli.command()
@click.option('--tipo', type=click.Choice(['cancion', 'album', 'artista']), default='cancion')
@click.option('--id', type=int, required=True)
def detalles(tipo, id):
    """Mostrar los detalles de una entidad."""
    click.echo(f"Mostrando detalles de [{tipo}] con ID {id}")
    if tipo == 'cancion':
        contenido = crud.obtener_cancion(id_cancion=id, db=db)
    elif tipo == 'album':
        contenido = crud.obtener_album(id_album=id, db=db)
    else:
        contenido = crud.obtener_artista(id_artista=id, db=db)
    if not contenido:
        click.echo(f"Sin Resultados")
    else:
        _separador()
        for clave, valor in contenido.items():
            print(f"  {clave:<25} {valor}")
    

# Muestra
@cli.command()
@click.option('--cantidad', type=int, default=5)
def muestra(cantidad):
    if cantidad <= 0:
        click.echo(f"Cantidad {cantidad} inválida.")
        return
    elif cantidad == 1:
        click.echo(f"Mostrando {cantidad} canción")
    else:
        click.echo(f"Muestra de {cantidad} canciones.")
    filas = crud.muestra_canciones(cantidad=cantidad, db=db)
    _separador()
    _tabla(filas)  

# ----------
# Modificar
# ----------
# Revisado
@cli.command()
@click.option('--tipo', type=click.Choice(['cancion', 'album']), default="cancion")
@click.option('--id', type=int, required=True)
@click.option('--estado', type=bool, default=True)
def revisado(tipo, id, estado):
    "Marca una entidad como REVISADO"
    if tipo == 'album':
        fila = crud.actualizar_estado_album(id_album=id, revisado=estado, db=db)
    else:
        fila = crud.actualizar_estado_cancion(id_cancion=id, revisado=estado, db=db)
    click.echo(f"El tipo {tipo}, ha cambiado estado revisado a {estado}.")


# MBZ
@cli.command()
@click.option('--tipo', type=click.Choice(['cancion', 'album', 'artista']), default='cancion')
@click.option('--id', type=int, required=True)
@click.option('--mbz', type=str, required=True)
def mbz(id, mbz):
    "Cambia el codigo mbz"
    pass


# Renombrar
@cli.command()
@click.option('--tipo', type=click.Choice(['album', 'cancion', 'artista']), default='cancion')
@click.option('--id', type=int, required=True)
@click.option('--nombre', required=True)
def renombrar(tipo, id, nombre):
    "Renombar el elemento"
    if tipo == 'album':
        pass
    elif tipo == 'artista':
        pass
    else:
        pass


if __name__ == '__main__':
    cli()