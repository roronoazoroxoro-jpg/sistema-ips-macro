import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DATABASE_PATH


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    import os

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS farmacias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_ips TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                localidad TEXT NOT NULL,
                cuit TEXT,
                cbu_farmacia TEXT,
                activa INTEGER DEFAULT 1,
                creada_en TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS depositos_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_deposito TEXT UNIQUE NOT NULL,
                farmacia_id INTEGER NOT NULL,
                periodo_desde TEXT NOT NULL,
                periodo_hasta TEXT NOT NULL,
                cantidad_recetas INTEGER NOT NULL DEFAULT 0,
                monto_total REAL NOT NULL,
                monto_efectivo REAL DEFAULT 0,
                monto_transferencia REAL DEFAULT 0,
                metodo_deposito TEXT NOT NULL DEFAULT 'ventanilla_macro',
                estado TEXT NOT NULL DEFAULT 'pendiente',
                referencia_banco TEXT,
                observaciones TEXT,
                creado_en TEXT NOT NULL,
                confirmado_en TEXT,
                FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
            );

            CREATE INDEX IF NOT EXISTS idx_depositos_estado ON depositos_caja(estado);
            CREATE INDEX IF NOT EXISTS idx_depositos_farmacia ON depositos_caja(farmacia_id);

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                farmacia_id INTEGER,
                activo INTEGER DEFAULT 1,
                creado_en TEXT NOT NULL,
                ultimo_login_en TEXT,
                FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
            );

            CREATE INDEX IF NOT EXISTS idx_usuarios_role ON usuarios(role);

            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                role TEXT NOT NULL,
                accion TEXT NOT NULL,
                entidad TEXT,
                entidad_id TEXT,
                detalle TEXT,
                ip_origen TEXT,
                creado_en TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_auditoria_creado_en ON auditoria(creado_en);
            """
        )
        _migrate_schema(conn)
        _seed_farmacias(conn)
        _seed_usuarios(conn)


def _migrate_schema(conn):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(depositos_caja)").fetchall()}
    for name, col_type in (
        ("archivo_recaudacion_en", "TEXT"),
        ("referencia_macro", "TEXT"),
        ("conciliado_en", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE depositos_caja ADD COLUMN {name} {col_type}")


def _seed_farmacias(conn):
    count = conn.execute("SELECT COUNT(*) FROM farmacias").fetchone()[0]
    if count > 0:
        return
    demo = [
        ("F-001", "Farmacia Alfa", "Posadas", "30-71234567-1"),
        ("F-002", "Macro Farma", "Puerto Iguazú", "30-72345678-2"),
        ("F-003", "Farmacia Integral", "Posadas", "30-73456789-3"),
        ("F-004", "Grobli San Martín", "Posadas", "30-74567890-4"),
        ("F-005", "Farmacia Oberá Centro", "Oberá", "30-75678901-5"),
    ]
    now = _utc_now()
    conn.executemany(
        "INSERT INTO farmacias (codigo_ips, nombre, localidad, cuit, creada_en) VALUES (?, ?, ?, ?, ?)",
        [(c, n, l, cu, now) for c, n, l, cu in demo],
    )


def _seed_usuarios(conn):
    from werkzeug.security import generate_password_hash
    from config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USER, DEFAULT_FARMACIA_PASSWORD

    count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if count > 0:
        return

    now = _utc_now()
    conn.execute(
        """
        INSERT INTO usuarios (username, password_hash, role, farmacia_id, activo, creado_en)
        VALUES (?, ?, 'admin', NULL, 1, ?)
        """,
        (DEFAULT_ADMIN_USER, generate_password_hash(DEFAULT_ADMIN_PASSWORD), now),
    )

    farmacias = conn.execute("SELECT id, codigo_ips FROM farmacias WHERE activa = 1").fetchall()
    for farmacia in farmacias:
        username = farmacia["codigo_ips"].lower().replace("-", "")
        conn.execute(
            """
            INSERT INTO usuarios (username, password_hash, role, farmacia_id, activo, creado_en)
            VALUES (?, ?, 'farmacia', ?, 1, ?)
            """,
            (username, generate_password_hash(DEFAULT_FARMACIA_PASSWORD), farmacia["id"], now),
        )


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
