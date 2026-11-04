"""API REST del horario escolar (FastAPI)."""
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import servicio
from .db import conectar, iniciar_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = conectar()
    iniciar_db(conn)
    conn.close()
    yield


app = FastAPI(title="Horario escolar", lifespan=lifespan)


def get_conn():
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


@app.exception_handler(servicio.ErrorDeNegocio)
async def manejar_error(request, exc: servicio.ErrorDeNegocio):
    if isinstance(exc, servicio.NoEncontrado):
        codigo = 404
    elif isinstance(exc, servicio.Conflicto):
        codigo = 409
    else:
        codigo = 400
    return JSONResponse(status_code=codigo, content={"detalle": str(exc)})


class NombreIn(BaseModel):
    nombre: str


class FranjaIn(BaseModel):
    orden: int
    inicio: str  # "HH:MM"
    fin: str     # "HH:MM"


class ClaseIn(BaseModel):
    materia_id: int
    profesor_id: int
    grupo_id: int
    salon_id: int
    dia: int  # 0=lunes ... 4=viernes
    franja_id: int


# ----- Catálogos: /catalogos/profesores | materias | grupos | salones -----

@app.post("/catalogos/{tabla}", status_code=201)
def crear_catalogo(tabla: str, datos: NombreIn, conn=Depends(get_conn)):
    return servicio.crear_catalogo(conn, tabla, datos.nombre)


@app.get("/catalogos/{tabla}")
def listar_catalogo(tabla: str, conn=Depends(get_conn)):
    return servicio.listar_catalogo(conn, tabla)


# ----- Franjas -----

@app.post("/franjas", status_code=201)
def crear_franja(datos: FranjaIn, conn=Depends(get_conn)):
    return servicio.crear_franja(conn, datos.orden, datos.inicio, datos.fin)


@app.get("/franjas")
def listar_franjas(conn=Depends(get_conn)):
    return servicio.listar_franjas(conn)


# ----- Clases -----

@app.post("/clases", status_code=201)
def crear_clase(datos: ClaseIn, conn=Depends(get_conn)):
    return servicio.crear_clase(conn, **datos.model_dump())


@app.get("/clases")
def listar_clases(grupo_id: Optional[int] = None, profesor_id: Optional[int] = None,
                  salon_id: Optional[int] = None, dia: Optional[int] = None,
                  conn=Depends(get_conn)):
    return servicio.listar_clases(conn, grupo_id, profesor_id, salon_id, dia)


@app.put("/clases/{clase_id}")
def actualizar_clase(clase_id: int, datos: ClaseIn, conn=Depends(get_conn)):
    return servicio.actualizar_clase(conn, clase_id, **datos.model_dump())


@app.delete("/clases/{clase_id}", status_code=204)
def eliminar_clase(clase_id: int, conn=Depends(get_conn)):
    servicio.eliminar_clase(conn, clase_id)


# ----- Consultas -----

@app.get("/profesores/libres")
def profesores_libres(dia: int = Query(..., ge=0, le=4), franja_id: int = Query(...),
                      conn=Depends(get_conn)):
    return servicio.profesores_libres(conn, dia, franja_id)


@app.get("/ahora")
def ahora(momento: Optional[datetime] = None, conn=Depends(get_conn)):
    """Quién está en clase ahora. `momento` (ISO) sirve para probar otra hora."""
    return servicio.estado_ahora(conn, momento)
