-- models/SQL/SQLite3_v3.sql

CREATE TABLE IF NOT EXISTS Artistas (
    id_artista      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_artista  TEXT    UNIQUE NOT NULL COLLATE NOCASE,
    codigo_itunes   INTEGER UNIQUE,
    codigo_mbz      TEXT,
    creado_en       TEXT    DEFAULT (date('now'))  -- auditoría
);

CREATE TABLE IF NOT EXISTS Generos (
    id_genero       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_genero   TEXT    UNIQUE NOT NULL COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS Albumes (
    id_album            INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_album        TEXT    NOT NULL COLLATE NOCASE,
    codigo_itunes       INTEGER UNIQUE,
    codigo_mbz          TEXT,
    numero_canciones    INTEGER,
    fecha_lanzamiento   DATE,       -- Adaptador/Convertidor en settings.py
    revisado            BOOLEAN,    -- Adaptador/Convertidor en settings.py
    album_explicito     BOOLEAN,    -- Adaptador/Convertidor en settings.py
    id_genero_principal INTEGER,
    id_artista_principal INTEGER,
    creado_en           TEXT    DEFAULT (date('now')),  -- auditoría
    CONSTRAINT fk_artista_album FOREIGN KEY (id_artista_principal) REFERENCES Artistas(id_artista),
    CONSTRAINT fk_genero_album  FOREIGN KEY (id_genero_principal)  REFERENCES Generos(id_genero)
);

CREATE TABLE IF NOT EXISTS Canciones (
    id_cancion      INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_cancion  TEXT    NOT NULL COLLATE NOCASE,
    codigo_itunes   INTEGER UNIQUE,
    codigo_mbz      TEXT,
    estado          TEXT    NOT NULL DEFAULT 'Pendiente'
                            CHECK (estado IN ('Pendiente', 'Revision', 'Finalizado')),
    numero_pista    INTEGER,
    cont_explicito  BOOLEAN,    -- Adaptador/Convertidor en settings.py
    id_album        INTEGER,
    id_genero       INTEGER,
    creado_en       TEXT    DEFAULT (date('now')),  -- auditoría
    CONSTRAINT fk_album_cancion  FOREIGN KEY (id_album)  REFERENCES Albumes(id_album),
    CONSTRAINT fk_genero_cancion FOREIGN KEY (id_genero) REFERENCES Generos(id_genero)
);

-- Variantes: remix, concierto, instrumental, etc.
-- Tiene los mismos campos informativos que Canciones porque
-- puede tener su propio código iTunes/MBZ y número de pista.
CREATE TABLE IF NOT EXISTS Variantes (
    id_variante     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_variante TEXT    NOT NULL COLLATE NOCASE,
    tipo_variante   TEXT    NOT NULL
                            CHECK (tipo_variante IN (
                                'Remix', 'Concierto', 'Instrumental',
                                'Loop Version', 'Extended Version', 'Version'
                            )),
    codigo_itunes   INTEGER UNIQUE,
    codigo_mbz      TEXT,
    numero_pista    INTEGER,
    cont_explicito  BOOLEAN,
    id_cancion      INTEGER NOT NULL,   -- canción original de referencia
    CONSTRAINT fk_cancion_variante FOREIGN KEY (id_cancion) REFERENCES Canciones(id_cancion)
);

-- Tablas pivote artista ↔ canción / variante
CREATE TABLE IF NOT EXISTS Artistas_Canciones (
    id_cancion  INTEGER,
    id_artista  INTEGER,
    rol_artista TEXT NOT NULL CHECK (rol_artista IN ('Principal', 'Colaborador', 'Feature')),
    PRIMARY KEY (id_cancion, id_artista),
    CONSTRAINT fk_rel_cancion  FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion),
    CONSTRAINT fk_rel_artista  FOREIGN KEY (id_artista)  REFERENCES Artistas(id_artista)
);

CREATE TABLE IF NOT EXISTS Artistas_Variantes (
    id_variante INTEGER,
    id_artista  INTEGER,
    rol_artista TEXT NOT NULL CHECK (rol_artista IN ('Principal', 'Colaborador', 'Feature')),
    PRIMARY KEY (id_variante, id_artista),
    CONSTRAINT fk_rel_variante FOREIGN KEY (id_variante) REFERENCES Variantes(id_variante),
    CONSTRAINT fk_rel_artista  FOREIGN KEY (id_artista)  REFERENCES Artistas(id_artista)
);

-- Playlists
-- numero_canciones se elimina: se calcula con COUNT sobre Canciones_Playlist.
CREATE TABLE IF NOT EXISTS Playlists (
    id_playlist     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_playlist TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS Canciones_Playlist (
    id_cancion  INTEGER,
    id_playlist INTEGER,
    PRIMARY KEY (id_cancion, id_playlist),      -- coma correcta aquí
    CONSTRAINT fk_rel_cancion  FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion),
    CONSTRAINT fk_rel_playlist FOREIGN KEY (id_playlist) REFERENCES Playlists(id_playlist)
);

-- Carátulas separadas por tamaño BLOB
CREATE TABLE IF NOT EXISTS Caratulas (
    id_caratula     INTEGER PRIMARY KEY AUTOINCREMENT,
    imagen_bytes    BLOB,
    id_album        INTEGER UNIQUE,
    CONSTRAINT fk_caratula_album FOREIGN KEY (id_album) REFERENCES Albumes(id_album)
);
