# cli.py
# Interfaz de línea de comandos para gestionar la biblioteca musical.
# Separado de main.py — este es para intervención manual, main.py es el pipeline automático.
#
# Uso:
#   python cli.py listar --estado Pendiente
#   python cli.py listar --tipo albumes
#   python cli.py ver --id 5
#   python cli.py estado --id 12 --valor Finalizado
#   python cli.py revisado --id 3
#   python cli.py mbz --entidad cancion --id 7 --codigo "uuid-mbz"
#   python cli.py renombrar --id 2 --nombre "Nombre Correcto"
#   python cli.py eliminar --tipo cancion --id 9
#   python cli.py eliminar --tipo album --id 4

import argparse
import sys
from pathlib import Path

from database import crud
from utils.errores import ErrorBaseDatos
from config.setup import DB_PATH
# Ancho de columna para la presentación en tabla
db = DB_PATH

_ANCHO = 80


# ---------------------------------------------------------------------------
# Helpers de presentación — solo aquí se imprime, nunca en crud.py
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

def cmd_listar(args: argparse.Namespace) -> None:
    """
    Listar registros de la base de datos.
    --tipo: canciones | albumes | artistas | sin_caratula
    --revisado: True | False 
    --artista: nombre del artista (filtra canciones por artista)
    """
    tipo = args.tipo or "canciones"

    if tipo == "canciones":
        if args.artista:
            filas = crud.listar_canciones_por_artista(args.artista, db)
            print(f"\nCanciones de '{args.artista}':")
        else:
            estado = None
            if args.estado == True:
                estado = True
            elif args.estado == False:
                estado = False
            filas = crud.listar_canciones(revisado=estado, db=db)
            titulo = f"Canciones — revisado: {estado or 'todos'}"
            print(f"\n{titulo}:")

    elif tipo == "albumes":
        revisado = None
        if args.estado == True:
            revisado = True
        elif args.estado == False:
            revisado = False
        filas = crud.listar_albumes(revisado=revisado, db=db)
        print(f"\nÁlbumes:")

    elif tipo == "artistas":
        filas = crud.listar_artistas(db=db)
        print(f"\nArtistas:")

    elif tipo == "sin_caratula":
        filas = crud.listar_albumes_sin_caratula(db=db)
        print(f"\nÁlbumes sin carátula:")

    else:
        print(f"Tipo desconocido: '{tipo}'. Opciones: canciones, albumes, artistas, sin_caratula")
        return

    _separador()
    _tabla(filas)
    print(f"\n  Total: {len(filas)} resultado(s)")


def cmd_ver(args: argparse.Namespace) -> None:
    """Ver el detalle completo de una canción por su id."""
    if not args.id:
        print("Error: --id es obligatorio para 'ver'.")
        return
    cancion = crud.obtener_cancion(args.id, db)
    if not cancion:
        print(f"No se encontró canción con id={args.id}.")
        return
    print(f"\nDetalle canción id={args.id}:")
    _separador()
    for clave, valor in cancion.items():
        print(f"  {clave:<25} {valor}")


def cmd_estado(args: argparse.Namespace) -> None:
    """Cambiar el estado de una canción."""
    if not args.id or not args.valor:
        print("Error: --id y --valor son obligatorios para 'estado'.")
        return
    crud.actualizar_estado_cancion(args.id, args.valor, db)
    print(f"  ✓ Canción id={args.id} → estado '{args.valor}'.")


def cmd_revisado(args: argparse.Namespace) -> None:
    """Marcar o desmarcar un álbum como revisado."""
    if not args.id:
        print("Error: --id es obligatorio para 'revisado'.")
        return
    marcar = not args.desmarcar
    crud.marcar_album_revisado(args.id, revisado=marcar, db=db)
    accion = "marcado" if marcar else "desmarcado"
    print(f"  ✓ Álbum id={args.id} {accion} como revisado.")


def cmd_mbz(args: argparse.Namespace) -> None:
    """Asignar o corregir el código MusicBrainz de un registro."""
    if not all([args.entidad, args.id, args.codigo]):
        print("Error: --entidad, --id y --codigo son obligatorios para 'mbz'.")
        return
    crud.actualizar_codigo_mbz(args.entidad, args.id, args.codigo, db=db)
    print(f"  ✓ {args.entidad.capitalize()} id={args.id} → MBZ '{args.codigo}'.")


def cmd_renombrar(args: argparse.Namespace) -> None:
    """Corregir el nombre de un artista."""
    if not args.id or not args.nombre:
        print("Error: --id y --nombre son obligatorios para 'renombrar'.")
        return
    crud.renombrar_artista(args.id, args.nombre, db)
    print(f"  ✓ Artista id={args.id} renombrado a '{args.nombre}'.")


def cmd_eliminar(args: argparse.Namespace) -> None:
    """Eliminar una canción, álbum completo, o artista."""
    if not args.tipo or not args.id:
        print("Error: --tipo y --id son obligatorios para 'eliminar'.")
        return

    if args.tipo == "cancion":
        if not _confirmar(f"¿Eliminar canción id={args.id}? Esta acción no se puede deshacer."):
            print("  Cancelado.")
            return
        crud.eliminar_cancion(args.id, db)
        print(f"  ✓ Canción id={args.id} eliminada.")

    elif args.tipo == "album":
        if not _confirmar(f"¿Eliminar ÁLBUM COMPLETO id={args.id} con todas sus canciones?"):
            print("  Cancelado.")
            return
        crud.eliminar_album_completo(args.id, db)
        print(f"  ✓ Álbum id={args.id} y sus canciones eliminados.")

    elif args.tipo == "artista":
        if not _confirmar(f"¿Eliminar artista id={args.id}?"):
            print("  Cancelado.")
            return
        crud.eliminar_artista(args.id, db)
        print(f"  ✓ Artista id={args.id} eliminado.")

    else:
        print(f"Tipo desconocido: '{args.tipo}'. Opciones: cancion, album, artista")


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Gestión manual de la Biblioteca Musical.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  python cli.py listar --estado Pendiente
  python cli.py listar --tipo albumes
  python cli.py listar --tipo canciones --artista "The Beatles"
  python cli.py ver --id 5
  python cli.py estado --id 12 --valor Finalizado
  python cli.py revisado --id 3
  python cli.py revisado --id 3 --desmarcar
  python cli.py mbz --entidad cancion --id 7 --codigo "550e8400-e29b-41d4-a716"
  python cli.py renombrar --id 2 --nombre "AC/DC"
  python cli.py eliminar --tipo cancion --id 9
  python cli.py eliminar --tipo album --id 4
        """
    )

    subparsers = parser.add_subparsers(dest="comando", required=True)

    # listar
    p_listar = subparsers.add_parser("listar", help="Listar registros.")
    p_listar.add_argument("--tipo", choices=["canciones", "albumes", "artistas", "sin_caratula"],
                          default="canciones")
    p_listar.add_argument("--estado", help="Filtrar por estado (canciones) o 'revisado'/'sin_revisar' (álbumes).")
    p_listar.add_argument("--artista", help="Filtrar canciones por nombre de artista.")

    # ver
    p_ver = subparsers.add_parser("ver", help="Ver detalle de una canción.")
    p_ver.add_argument("--id", type=int, required=True)

    # estado
    p_estado = subparsers.add_parser("estado", help="Cambiar estado de una canción.")
    p_estado.add_argument("--id", type=int, required=True)
    p_estado.add_argument("--valor", action="store_true", help="Cambia el estado")

    # revisado
    p_rev = subparsers.add_parser("revisado", help="Marcar/desmarcar álbum como revisado.")
    p_rev.add_argument("--id", type=int, required=True)
    p_rev.add_argument("--desmarcar", action="store_true", help="Quitar la marca de revisado.")

    # mbz
    p_mbz = subparsers.add_parser("mbz", help="Asignar código MusicBrainz.")
    p_mbz.add_argument("--entidad", required=True, choices=["cancion", "album", "artista"])
    p_mbz.add_argument("--id", type=int, required=True)
    p_mbz.add_argument("--codigo", required=True, help="UUID de MusicBrainz.")

    # renombrar
    p_ren = subparsers.add_parser("renombrar", help="Corregir nombre de un artista.")
    p_ren.add_argument("--id", type=int, required=True)
    p_ren.add_argument("--nombre", required=True)

    # eliminar
    p_del = subparsers.add_parser("eliminar", help="Eliminar un registro.")
    p_del.add_argument("--tipo", required=True, choices=["cancion", "album", "artista"])
    p_del.add_argument("--id", type=int, required=True)

    return parser


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

COMANDOS = {
    "listar":   cmd_listar,
    "ver":      cmd_ver,
    "estado":   cmd_estado,
    "revisado": cmd_revisado,
    "mbz":      cmd_mbz,
    "renombrar": cmd_renombrar,
    "eliminar": cmd_eliminar,
}

if __name__ == "__main__":
    parser = construir_parser()
    args = parser.parse_args()

    try:
        COMANDOS[args.comando](args)
    except (ErrorBaseDatos, ValueError) as e:
        print(f"\n  Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrumpido.")
        sys.exit(0)
