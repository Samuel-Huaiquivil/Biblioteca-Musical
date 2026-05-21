## Script para la Gestión de Biblioteca Musical

Este script en Python permite gestionar una biblioteca musical, insertando tags a través de ID3 y la carátula respectiva del álbum.

Esto se realiza gracias a la búsqueda de canciones a través de APIs como iTunes y MusicBrainz, además se utiliza Cover Art Archive para la obtención de las carátulas.

## Funcionalidades

La funcion principal del script es 'procesar_canciones', la cual toma una lista de canciones y procesa cada una de ellas para obtener la información necesaria y actualizar los tags ID3.

ruta_principal : Ruta principal donde se encuentran las canciones a procesar. El script buscará recursivamente en esta ruta para encontrar todas las canciones.
    
nivel_busqueda : Nivel de búsqueda para encontrar la canción en las APIs. Es un valor del 1 al 5 en donde 1 es una búsqueda rápida y 5 es una búsqueda exhaustiva.
    
numero_canciones : Número de canciones a procesar. Si se establece en 0, se procesarán todas las canciones encontradas en la ruta principal.
    
caratulas_mejoradas : Si se establece en True, el script intentará obtener carátulas de mejor calidad utilizando la API de Cover Art Archive. Si se establece en False, se utilizarán las carátulas obtenidas a través de las APIs de iTunes y MusicBrainz.

descargar_caratulas : Si se establece en True, el script descargará las carátulas de las canciones en una ruta local. Si se establece en False, no se descargarán carátulas.

mover_canciones : Si se establece en True, el script moverá las canciones procesadas a una nueva ubicación. Si se establece en False, las canciones permanecerán en su ubicación original.
