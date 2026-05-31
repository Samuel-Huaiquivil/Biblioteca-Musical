-- models/SQL/SQLite3_v4.sql

CREATE TABLE IF NOT EXISTS Artistas (
    id_artista      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_artista  TEXT    NOT NULL COLLATE NOCASE,
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
    pistas_totales      INTEGER,
    fecha_lanzamiento   DATE,       -- Adaptador/Convertidor en settings.py
    revisado            BOOLEAN,    -- Adaptador/Convertidor en settings.py
    album_explicito     BOOLEAN,    -- Adaptador/Convertidor en settings.py
    id_genero_principal INTEGER,
    id_artista_principal INTEGER,
    creado_en           TEXT    DEFAULT (date('now')),  -- auditoría
    CONSTRAINT fk_artista_album FOREIGN KEY (id_artista_principal) REFERENCES Artistas(id_artista),
    CONSTRAINT fk_genero_album  FOREIGN KEY (id_genero_principal)  REFERENCES Generos(id_genero),
    CONSTRAINT uk_album_artista UNIQUE (titulo_album, id_artista_principal)
);

CREATE TABLE IF NOT EXISTS Canciones (
    id_cancion      INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_cancion  TEXT    NOT NULL COLLATE NOCASE,
    codigo_itunes   INTEGER UNIQUE,
    codigo_mbz      TEXT,
    revisado        BOOLEAN,
    cont_explicito  BOOLEAN,
    creado_en       TEXT    DEFAULT (date('now'))  -- auditoría
);

-- Variantes: Diferentes versiones de la misma canción, ya sea
-- concierto, instrumental, etc. Datos simples, sin mucho cambio. Es Variable.
CREATE TABLE IF NOT EXISTS Variantes (
    id_variante     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_variante TEXT    NOT NULL COLLATE NOCASE,
    tipo_variante   TEXT    NOT NULL CHECK (tipo_variante IN (
                                'Concierto', 'Instrumental',
                                'Loop Version', 'Extended Version', 'Version'
                            )),
    id_cancion      INTEGER NOT NULL,  
    CONSTRAINT fk_cancion_variante FOREIGN KEY (id_cancion) REFERENCES Canciones(id_cancion)
);

-- Tablas pivote artista ↔ canción 
CREATE TABLE IF NOT EXISTS Artistas_Canciones (
    id_cancion  INTEGER,
    id_artista  INTEGER,
    rol_artista TEXT NOT NULL CHECK (rol_artista IN ('Principal', 'Colaborador', 'Feature')),
    PRIMARY KEY (id_cancion, id_artista),
    CONSTRAINT fk_rel_cancion  FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion),
    CONSTRAINT fk_rel_artista  FOREIGN KEY (id_artista)  REFERENCES Artistas(id_artista),
    CONSTRAINT uk_cancion_artista_rol UNIQUE (id_cancion, id_artista, rol_artista)
);

-- Pivote Cancion * Género
CREATE TABLE IF NOT EXISTS Generos_Canciones (
    id_genero  INTEGER,
    id_cancion  INTEGER,
    PRIMARY KEY (id_cancion, id_genero),
    CONSTRAINT fk_rel_cancion FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion),
    CONSTRAINT fk_rel_genero  FOREIGN KEY (id_genero)  REFERENCES Generos(id_genero)
);

-- Pivote Cancion * Album
CREATE TABLE IF NOT EXISTS Canciones_Albumes (
    id_cancion  INTEGER,
    id_album  INTEGER,
    numero_cancion INTEGER,
    PRIMARY KEY (id_cancion, id_album),
    CONSTRAINT fk_rel_cancion FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion),
    CONSTRAINT fk_rel_album  FOREIGN KEY (id_album)  REFERENCES Albumes(id_album),
    CONSTRAINT uk_cancion_album_nro UNIQUE (id_cancion, id_album, numero_cancion)
);

CREATE TABLE IF NOT EXISTS Caratulas (
    id_caratula     INTEGER PRIMARY KEY AUTOINCREMENT,
    url_caratula    TEXT,
    imagen_bytes    BLOB,
    id_album        INTEGER UNIQUE,
    CONSTRAINT fk_caratula_album FOREIGN KEY (id_album) REFERENCES Albumes(id_album)
);

CREATE INDEX idx_albumes_artista ON Albumes(id_artista_principal);
CREATE INDEX idx_canciones_album ON Canciones_Albumes(id_album);
