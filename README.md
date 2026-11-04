# Horario escolar

API para que un colegio organice su horario de clases, vea profesores libres,
sepa quién está en clase ahora y modifique clases validando choques.

## Instalación

```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar

```bash
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/docs para probar todos los endpoints desde el navegador.
La base de datos `horarios.db` se crea sola la primera vez.

## Pruebas

```bash
python -m unittest -v
```

## Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| POST/GET | `/catalogos/{profesores\|materias\|grupos\|salones}` | Crear y listar datos base |
| POST/GET | `/franjas` | Franjas horarias (`inicio`/`fin` en HH:MM) |
| POST/GET | `/clases` | Crear clase / listar (filtros: `grupo_id`, `profesor_id`, `salon_id`, `dia`) |
| PUT/DELETE | `/clases/{id}` | Modificar o eliminar una clase |
| GET | `/profesores/libres?dia=0&franja_id=1` | Profesores libres (día 0=lunes ... 4=viernes) |
| GET | `/ahora` | Quién está en clase y quién está libre ahora |

## Estructura

- `app/db.py`: esquema SQLite y conexión
- `app/servicio.py`: reglas de negocio y consultas (sin FastAPI)
- `app/main.py`: endpoints
- `tests/`: pruebas de las reglas de choques y consultas

## Siguientes etapas

Interfaz web con la cuadrícula semanal, editar/borrar datos base, roles
(administrador / profesor) con login, y exportar a PDF o Excel.
