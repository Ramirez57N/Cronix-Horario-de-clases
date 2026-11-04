"""Lógica de negocio del horario. No depende de FastAPI, así se puede probar sola."""
import re
import sqlite3
from datetime import datetime

CATALOGOS = {"profesores", "materias", "grupos", "salones"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes"]
FORMATO_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ErrorDeNegocio(Exception):
    """Datos inválidos (400)."""


class NoEncontrado(ErrorDeNegocio):
    """El registro no existe (404)."""


class Conflicto(ErrorDeNegocio):
    """Choque de horario o duplicado (409)."""


# ---------- Catálogos: profesores, materias, grupos, salones ----------

def _validar_tabla(tabla):
    if tabla not in CATALOGOS:
        raise NoEncontrado(f"Catálogo desconocido: {tabla}")


def crear_catalogo(conn, tabla, nombre):
    _validar_tabla(tabla)
    nombre = (nombre or "").strip()
    if not nombre:
        raise ErrorDeNegocio("El nombre no puede estar vacío")
    try:
        cur = conn.execute(f"INSERT INTO {tabla} (nombre) VALUES (?)", (nombre,))
    except sqlite3.IntegrityError:
        raise Conflicto(f"Ya existe '{nombre}' en {tabla}")
    conn.commit()
    return {"id": cur.lastrowid, "nombre": nombre}


def listar_catalogo(conn, tabla):
    _validar_tabla(tabla)
    filas = conn.execute(f"SELECT id, nombre FROM {tabla} ORDER BY nombre").fetchall()
    return [dict(f) for f in filas]


# ---------- Franjas horarias ----------

def crear_franja(conn, orden, inicio, fin):
    if not (FORMATO_HORA.match(inicio) and FORMATO_HORA.match(fin)):
        raise ErrorDeNegocio("Las horas deben tener formato HH:MM")
    if inicio >= fin:
        raise ErrorDeNegocio("La hora de inicio debe ser menor que la de fin")
    try:
        cur = conn.execute(
            "INSERT INTO franjas (orden, inicio, fin) VALUES (?, ?, ?)",
            (orden, inicio, fin),
        )
    except sqlite3.IntegrityError:
        raise Conflicto(f"Ya existe una franja con orden {orden}")
    conn.commit()
    return {"id": cur.lastrowid, "orden": orden, "inicio": inicio, "fin": fin}


def listar_franjas(conn):
    filas = conn.execute("SELECT * FROM franjas ORDER BY orden").fetchall()
    return [dict(f) for f in filas]


# ---------- Clases ----------

_SELECT_CLASES = """
SELECT c.id, c.dia, c.franja_id, f.inicio, f.fin,
       m.id AS materia_id, m.nombre AS materia,
       p.id AS profesor_id, p.nombre AS profesor,
       g.id AS grupo_id, g.nombre AS grupo,
       s.id AS salon_id, s.nombre AS salon
FROM clases c
JOIN franjas f ON f.id = c.franja_id
JOIN materias m ON m.id = c.materia_id
JOIN profesores p ON p.id = c.profesor_id
JOIN grupos g ON g.id = c.grupo_id
JOIN salones s ON s.id = c.salon_id
"""


def _existe(conn, tabla, id_, etiqueta):
    if conn.execute(f"SELECT 1 FROM {tabla} WHERE id = ?", (id_,)).fetchone() is None:
        raise NoEncontrado(f"No existe {etiqueta} con id {id_}")


def _verificar(conn, materia_id, profesor_id, grupo_id, salon_id, dia, franja_id,
               excluir_id=None):
    """Valida que existan las referencias y que no haya choques de horario."""
    if dia not in range(5):
        raise ErrorDeNegocio("El día debe ser un número de 0 (lunes) a 4 (viernes)")
    _existe(conn, "materias", materia_id, "la materia")
    _existe(conn, "profesores", profesor_id, "el profesor")
    _existe(conn, "grupos", grupo_id, "el grupo")
    _existe(conn, "salones", salon_id, "el salón")
    _existe(conn, "franjas", franja_id, "la franja")

    reglas = [
        ("profesor_id", profesor_id, "El profesor ya tiene clase"),
        ("grupo_id", grupo_id, "El grupo ya tiene clase"),
        ("salon_id", salon_id, "El salón ya está ocupado"),
    ]
    for campo, valor, mensaje in reglas:
        choque = conn.execute(
            f"SELECT id FROM clases WHERE dia = ? AND franja_id = ? AND {campo} = ? "
            "AND id != ?",
            (dia, franja_id, valor, excluir_id if excluir_id is not None else -1),
        ).fetchone()
        if choque:
            raise Conflicto(f"{mensaje} en ese día y franja (clase #{choque['id']})")


def obtener_clase(conn, clase_id):
    fila = conn.execute(_SELECT_CLASES + " WHERE c.id = ?", (clase_id,)).fetchone()
    if fila is None:
        raise NoEncontrado(f"No existe la clase {clase_id}")
    return dict(fila)


def crear_clase(conn, materia_id, profesor_id, grupo_id, salon_id, dia, franja_id):
    _verificar(conn, materia_id, profesor_id, grupo_id, salon_id, dia, franja_id)
    cur = conn.execute(
        "INSERT INTO clases (materia_id, profesor_id, grupo_id, salon_id, dia, franja_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (materia_id, profesor_id, grupo_id, salon_id, dia, franja_id),
    )
    conn.commit()
    return obtener_clase(conn, cur.lastrowid)


def actualizar_clase(conn, clase_id, materia_id, profesor_id, grupo_id, salon_id,
                     dia, franja_id):
    obtener_clase(conn, clase_id)  # lanza NoEncontrado si no existe
    _verificar(conn, materia_id, profesor_id, grupo_id, salon_id, dia, franja_id,
               excluir_id=clase_id)
    conn.execute(
        "UPDATE clases SET materia_id=?, profesor_id=?, grupo_id=?, salon_id=?, "
        "dia=?, franja_id=? WHERE id=?",
        (materia_id, profesor_id, grupo_id, salon_id, dia, franja_id, clase_id),
    )
    conn.commit()
    return obtener_clase(conn, clase_id)


def eliminar_clase(conn, clase_id):
    obtener_clase(conn, clase_id)
    conn.execute("DELETE FROM clases WHERE id = ?", (clase_id,))
    conn.commit()


def listar_clases(conn, grupo_id=None, profesor_id=None, salon_id=None, dia=None):
    filtros, params = [], []
    for columna, valor in (("c.grupo_id", grupo_id), ("c.profesor_id", profesor_id),
                           ("c.salon_id", salon_id), ("c.dia", dia)):
        if valor is not None:
            filtros.append(f"{columna} = ?")
            params.append(valor)
    where = (" WHERE " + " AND ".join(filtros)) if filtros else ""
    filas = conn.execute(
        _SELECT_CLASES + where + " ORDER BY c.dia, f.orden", params
    ).fetchall()
    return [dict(f) for f in filas]


# ---------- Consultas ----------

def profesores_libres(conn, dia, franja_id):
    """Profesores sin clase en un día y franja dados."""
    if dia not in range(5):
        raise ErrorDeNegocio("El día debe ser un número de 0 (lunes) a 4 (viernes)")
    _existe(conn, "franjas", franja_id, "la franja")
    filas = conn.execute(
        "SELECT id, nombre FROM profesores WHERE id NOT IN "
        "(SELECT profesor_id FROM clases WHERE dia = ? AND franja_id = ?) "
        "ORDER BY nombre",
        (dia, franja_id),
    ).fetchall()
    return [dict(f) for f in filas]


def estado_ahora(conn, momento=None):
    """Qué profesores están en clase y cuáles están libres en este momento."""
    momento = momento or datetime.now()
    dia = momento.weekday()
    hora = momento.strftime("%H:%M")
    vacio = {"momento": momento.isoformat(timespec="minutes"), "franja": None,
             "en_clase": [], "libres": []}
    if dia > 4:
        return vacio
    franja = conn.execute(
        "SELECT * FROM franjas WHERE inicio <= ? AND ? < fin", (hora, hora)
    ).fetchone()
    if franja is None:
        return vacio
    en_clase = conn.execute(
        _SELECT_CLASES + " WHERE c.dia = ? AND c.franja_id = ? ORDER BY p.nombre",
        (dia, franja["id"]),
    ).fetchall()
    return {
        "momento": vacio["momento"],
        "franja": dict(franja),
        "en_clase": [dict(f) for f in en_clase],
        "libres": profesores_libres(conn, dia, franja["id"]),
    }
