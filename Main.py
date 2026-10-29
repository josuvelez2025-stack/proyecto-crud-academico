from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3

# Inicializamos la aplicación de FastAPI
app = FastAPI(title="CRUD Académico Relacional - UCE")

# Nombre del archivo local de la base de datos SQLite
DB_NAME = "academico.db"

# ---------------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS Y RELACIONES
# ---------------------------------------------------------
def init_db():
    """
    Crea la base de datos local SQLite y define las tablas con sus 
    respectivas restricciones, llaves primarias y llaves foráneas.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Activamos el soporte de claves foráneas en SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Tabla PARALELOS (Relación 1 a Muchos con Usuarios)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paralelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_paralelo TEXT NOT NULL,
            aula TEXT NOT NULL
        )
    """)
    
    # 2. Tabla USUARIOS (Con cédula, nombre, apellido, edad, sexo y FK a paralelo)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            edad INTEGER NOT NULL,
            sexo TEXT NOT NULL,
            paralelo_id INTEGER,
            FOREIGN KEY (paralelo_id) REFERENCES paralelos(id) ON DELETE SET NULL
        )
    """)
    
    # 3. Tabla MATERIAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            codigo TEXT NOT NULL UNIQUE
        )
    """)
    
    # 4. Tabla Intermedia USUARIO_MATERIAS (Relación Muchos a Muchos: un usuario muchas materias)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuario_materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            materia_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (materia_id) REFERENCES materias(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# Ejecutamos la función al arrancar
init_db()


# ---------------------------------------------------------
# MODELOS PYDANTIC (Validación de Datos)
# ---------------------------------------------------------
class ParaleloModel(BaseModel):
    nombre_paralelo: str
    aula: str

class UsuarioModel(BaseModel):
    cedula: str
    nombre: str
    apellido: str
    edad: int
    sexo: str
    paralelo_id: int | None = None  # Opcional por si se crea sin paralelo asignado

class MateriaModel(BaseModel):
    nombre: str
    codigo: str

class InscribirMateriaModel(BaseModel):
    usuario_id: int
    materia_id: int


# =========================================================
# CRUD 1: PARALELOS
# =========================================================
@app.get("/paralelos", summary="Listar paralelos")
def obtener_paralelos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre_paralelo, aula FROM paralelos")
    filas = cursor.fetchall()
    conn.close()
    return [{"id": f[0], "nombre_paralelo": f[1], "aula": f[2]} for f in filas]

@app.post("/paralelos", status_code=201, summary="Crear un paralelo")
def crear_paralelo(paralelo: ParaleloModel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO paralelos (nombre_paralelo, aula) VALUES (?, ?)", (paralelo.nombre_paralelo, paralelo.aula))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **paralelo.dict()}


# =========================================================
# CRUD 2: USUARIOS
# =========================================================
@app.get("/usuarios", summary="Listar usuarios")
def obtener_usuarios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cedula, nombre, apellido, edad, sexo, paralelo_id FROM usuarios")
    filas = cursor.fetchall()
    conn.close()
    return [{"id": f[0], "cedula": f[1], "nombre": f[2], "apellido": f[3], "edad": f[4], "sexo": f[5], "paralelo_id": f[6]} for f in filas]

@app.post("/usuarios", status_code=201, summary="Crear un usuario")
def crear_usuario(usuario: UsuarioModel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (cedula, nombre, apellido, edad, sexo, paralelo_id) VALUES (?, ?, ?, ?, ?, ?)",
            (usuario.cedula, usuario.nombre, usuario.apellido, usuario.edad, usuario.sexo, usuario.paralelo_id)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="La cédula ya está registrada o el paralelo no existe.")
    conn.close()
    return {"id": nuevo_id, **usuario.dict()}

@app.put("/usuarios/{usuario_id}", summary="Actualizar usuario")
def actualizar_usuario(usuario_id: int, usuario: UsuarioModel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    cursor.execute(
        "UPDATE usuarios SET cedula = ?, nombre = ?, apellido = ?, edad = ?, sexo = ?, paralelo_id = ? WHERE id = ?",
        (usuario.cedula, usuario.nombre, usuario.apellido, usuario.edad, usuario.sexo, usuario.paralelo_id, usuario_id)
    )
    conn.commit()
    conn.close()
    return {"id": usuario_id, **usuario.dict()}

@app.delete("/usuarios/{usuario_id}", summary="Eliminar usuario")
def eliminar_usuario(usuario_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()
    return {"mensaje": f"Usuario con ID {usuario_id} eliminado exitosamente"}


# =========================================================
# CRUD 3: MATERIAS
# =========================================================
@app.get("/materias", summary="Listar materias")
def obtener_materias():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, codigo FROM materias")
    filas = cursor.fetchall()
    conn.close()
    return [{"id": f[0], "nombre": f[1], "codigo": f[2]} for f in filas]

@app.post("/materias", status_code=201, summary="Crear una materia")
def crear_materia(materia: MateriaModel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO materias (nombre, codigo) VALUES (?, ?)", (materia.nombre, materia.codigo))
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="El código de la materia ya existe.")
    conn.close()
    return {"id": nuevo_id, **materia.dict()}


# =========================================================
# RELACIÓN: INSCRIBIR MATERIAS A USUARIOS (Muchos a Muchos)
# =========================================================
@app.post("/usuario-materias", status_code=201, summary="Asignar materia a un usuario")
def inscribir_materia(data: InscribirMateriaModel):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuario_materias (usuario_id, materia_id) VALUES (?, ?)",
            (data.usuario_id, data.materia_id)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Usuario o materia inválidos.")
    conn.close()
    return {"id": nuevo_id, "usuario_id": data.usuario_id, "materia_id": data.materia_id}

@app.get("/usuario-materias", summary="Ver materias inscritas por los usuarios")
def listar_inscripciones():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT um.id, u.nombre, u.apellido, m.nombre 
        FROM usuario_materias um
        JOIN usuarios u ON um.usuario_id = u.id
        JOIN materias m ON um.materia_id = m.id
    """)
    filas = cursor.fetchall()
    conn.close()
    return [{"inscripcion_id": f[0], "estudiante": f[1] + " " + f[2], "materia": f[3]} for f in filas]