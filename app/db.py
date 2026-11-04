"""Conexión y esquema de la base de datos (SQLite)."""
import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).resolve().parent.parent / "horarios.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS profesores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS salones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS franjas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orden INTEGER NOT NULL UNIQUE,
    inicio TEXT NOT NULL,   -- 'HH:MM'
    fin TEXT NOT NULL       -- 'HH:MM'
);
CREATE TABLE IF NOT EXISTS clases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    profesor_id INTEGER NOT NULL REFERENCES profesores(id),
    grupo_id INTEGER NOT NULL REFERENCES grupos(id),
    salon_id INTEGER NOT NULL REFERENCES salones(id),
    dia INTEGER NOT NULL CHECK (dia BETWEEN 0 AND 4),  -- 0=lunes ... 4=viernes
    franja_id INTEGER NOT NULL REFERENCES franjas(id),
    -- Red de seguridad: la base de datos también impide los choques
    UNIQUE (profesor_id, dia, franja_id),
    UNIQUE (grupo_id, dia, franja_id),
    UNIQUE (salon_id, dia, franja_id)
);
"""


def conectar(ruta=RUTA_DB):
    conn = sqlite3.connect(ruta, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def iniciar_db(conn):
    conn.executescript(ESQUEMA)
    conn.commit()
