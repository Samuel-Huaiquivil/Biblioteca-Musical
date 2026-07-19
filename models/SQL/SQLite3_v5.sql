-- models/SQL/SQLite3_v5.sql
-- Modelo Actualizado con Restricciones.

-- TABLAS PRINCIPALES
CREATE TABLE IF NOT EXISTS Artistas (
    id_artista      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_artista  TEXT    UNIQUE NOT NULL COLLATE NOCASE,
    creado_en       TEXT    DEFAULT (date('now'))  -- auditoría
);

CREATE TABLE IF NOT EXISTS Generos (
    id_genero       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_genero   TEXT    UNIQUE NOT NULL COLLATE NOCASE,
    descripcion     TEXT
);

CREATE TABLE IF NOT EXISTS Albumes (
    id_album            INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_album        TEXT    NOT NULL COLLATE NOCASE,
    pistas_totales      INTEGER,
    fecha_lanzamiento   DATE,       -- Adaptador/Convertidor en settings.py
    revisado            BOOLEAN,    -- Adaptador/Convertidor en settings.py
    genero_principal_id INTEGER,
    artista_principal_id INTEGER,
    creado_en           TEXT    DEFAULT (date('now')),  -- auditoría
    CONSTRAINT fk_artista_album FOREIGN KEY (artista_principal_id) REFERENCES Artistas(id_artista) ON DELETE CASCADE,
    CONSTRAINT fk_genero_album  FOREIGN KEY (genero_principal_id)  REFERENCES Generos(id_genero) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Canciones (
    id_cancion      INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo_cancion  TEXT    NOT NULL COLLATE NOCASE,
    revisado        BOOLEAN,
    creado_en       TEXT    DEFAULT (date('now'))  -- auditoría
);

-- Variantes: Diferentes versiones de la misma canción, ya sea:
-- concierto, instrumental, etc. Datos simples, sin mucho cambio. Es Variable.
CREATE TABLE IF NOT EXISTS Variantes (
    id_variante     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_variante TEXT    NOT NULL COLLATE NOCASE,
    tipo_variante   TEXT    NOT NULL CHECK (tipo_variante IN (
                                'Concierto', 'Instrumental', 'Loop Version', 'Extended Version', 
                                'Speed Version', 'Slow Version', 'Spanish Version', 'Version', 'Cover'
                            )),
    cancion_id      INTEGER NOT NULL,  
    CONSTRAINT fk_cancion_variante FOREIGN KEY (cancion_id) REFERENCES Canciones(id_cancion) ON DELETE CASCADE
);

-- TABLAS PIVOTE
-- Pivote artista * canción 
CREATE TABLE IF NOT EXISTS Artistas_Canciones (
    id_cancion  INTEGER,
    id_artista  INTEGER,
    rol_artista TEXT NOT NULL CHECK (rol_artista IN ('Principal', 'Colaborador', 'Feature')),
    PRIMARY KEY (id_cancion, id_artista),
    CONSTRAINT fk_rel_cancion  FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion) ON DELETE CASCADE,
    CONSTRAINT fk_rel_artista  FOREIGN KEY (id_artista)  REFERENCES Artistas(id_artista) ON DELETE RESTRICT,
    CONSTRAINT uk_cancion_artista_rol UNIQUE (id_cancion, id_artista, rol_artista)
);

-- Pivote Cancion * Género
CREATE TABLE IF NOT EXISTS Generos_Canciones (
    id_genero  INTEGER,
    id_cancion  INTEGER,
    PRIMARY KEY (id_cancion, id_genero),
    CONSTRAINT fk_rel_cancion FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion) ON DELETE CASCADE,
    CONSTRAINT fk_rel_genero  FOREIGN KEY (id_genero)  REFERENCES Generos(id_genero) ON DELETE CASCADE
);

-- Pivote Cancion * Album
CREATE TABLE IF NOT EXISTS Canciones_Albumes (
    id_cancion  INTEGER,
    id_album  INTEGER,
    numero_cancion INTEGER,
    PRIMARY KEY (id_cancion, id_album),
    CONSTRAINT fk_rel_cancion FOREIGN KEY (id_cancion)  REFERENCES Canciones(id_cancion) ON DELETE CASCADE,
    CONSTRAINT fk_rel_album  FOREIGN KEY (id_album)  REFERENCES Albumes(id_album) ON DELETE CASCADE,
    CONSTRAINT uk_album_nro_pista UNIQUE (id_album, numero_cancion)
);

-- CARATULAS
CREATE TABLE IF NOT EXISTS Caratulas (
    id_caratula     INTEGER PRIMARY KEY AUTOINCREMENT,
    url_caratula    TEXT,
    imagen_bytes    BLOB,
    album_id        INTEGER UNIQUE,
    CONSTRAINT fk_caratula_album FOREIGN KEY (album_id) REFERENCES Albumes(id_album) ON DELETE CASCADE
);

-- IDENTIFICADORES
CREATE TABLE IF NOT EXISTS Apis (
    id_api      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_api  TEXT NOT NULL CHECK (nombre_api IN (
                            'iTunes', 'MusicBrainz'
                            )),
    region_api  TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS Artistas_Identificadores(
    codigo_ext   TEXT NOT NULL,
    artista_id          INTEGER,
    api_id              INTEGER,
    PRIMARY KEY (codigo_ext, artista_id, api_id),
    CONSTRAINT fk_artista FOREIGN KEY (artista_id) REFERENCES Artistas(id_artista) ON DELETE CASCADE,
    CONSTRAINT fk_api FOREIGN KEY (api_id) REFERENCES Apis(id_api) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Canciones_Identificadores(
    codigo_ext   TEXT NOT NULL,
    cancion_id          INTEGER,
    api_id              INTEGER,
    PRIMARY KEY (codigo_ext, cancion_id, api_id),
    CONSTRAINT fk_cancion FOREIGN KEY (cancion_id) REFERENCES Canciones(id_cancion) ON DELETE CASCADE,
    CONSTRAINT fk_api FOREIGN KEY (api_id) REFERENCES Apis(id_api) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Albumes_Identificadores(
    codigo_ext   TEXT NOT NULL,
    album_id            INTEGER,
    api_id              INTEGER,
    PRIMARY KEY (codigo_ext, album_id, api_id),
    CONSTRAINT fk_album FOREIGN KEY (album_id) REFERENCES Albumes(id_album) ON DELETE CASCADE,
    CONSTRAINT fk_api FOREIGN KEY (api_id) REFERENCES Apis(id_api) ON DELETE CASCADE
);

-- ÍNDICES
CREATE INDEX IF NOT EXISTS idx_albumes_artista ON Albumes(artista_principal_id);
CREATE INDEX IF NOT EXISTS idx_canciones_album ON Canciones_Albumes(id_album);
CREATE INDEX IF NOT EXISTS idx_artistas_canciones_reverse ON Artistas_Canciones(id_artista);
CREATE INDEX IF NOT EXISTS idx_generos_canciones_reverse ON Generos_Canciones(id_genero);