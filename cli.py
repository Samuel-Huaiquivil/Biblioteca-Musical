# cli.py
# Uso: python cli.py --accion listar_pendientes
#      python cli.py --accion marcar_revisado --id 42

import argparse
from database import crud

def main():
    parser = argparse.ArgumentParser(description="Gestión de Biblioteca Musical")
    parser.add_argument("--accion", required=True, choices=[
        "listar_pendientes",
        "marcar_revisado",
        "eliminar_cancion",
        "listar_sin_caratula",
    ])
    parser.add_argument("--id", type=int, help="ID local del registro")
    args = parser.parse_args()

    if args.accion == "listar_pendientes":
        canciones = crud.listar_canciones_pendientes()
        for c in canciones:
            print(c)
    elif args.accion == "marcar_revisado" and args.id:
        crud.marcar_album_revisado(args.id)
        print(f"Álbum {args.id} marcado como revisado.")
    # ...

if __name__ == "__main__":
    main()