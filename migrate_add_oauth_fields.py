"""
Script de migración manual para agregar los campos OAuth2 a la tabla 'usuarios'.

Uso (ejecutar desde la raíz del proyecto, con el contenedor de BD activo):
    python migrate_add_oauth_fields.py

Este script es idempotente: verifica si cada columna ya existe antes de agregarla,
por lo que es seguro ejecutarlo múltiples veces sin romper datos existentes.
Para producción se recomienda migrar a Alembic (alembic revision --autogenerate).
"""

import sys
from sqlalchemy import text, inspect
from app.database.connection import engine


COLUMNAS_OAUTH = [
    # (nombre_columna, definición SQL)
    ("proveedor_auth",   "VARCHAR(20)  NOT NULL DEFAULT 'local'"),
    ("proveedor_id",     "VARCHAR(255) NULL"),
    ("email_verificado", "BOOLEAN      NOT NULL DEFAULT FALSE"),
    ("foto_perfil",      "VARCHAR(500) NULL"),
    ("hashed_password",  "VARCHAR(255) NULL"),
    ("refresh_token",    "VARCHAR(512) NULL"),
    ("activo",           "BOOLEAN      NOT NULL DEFAULT TRUE"),
    ("updated_at",       "TIMESTAMP    NULL"),
]


def columnas_existentes(conn, tabla: str) -> set:
    """Retorna el conjunto de nombres de columnas actuales de la tabla."""
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :tabla"
        ),
        {"tabla": tabla}
    )
    return {row[0] for row in result}


def migrar():
    """
    Agrega las columnas OAuth2 a la tabla 'usuarios' si no existen.
    También crea el índice en proveedor_id para búsquedas eficientes.
    """
    print("═" * 60)
    print("  EXPLORO — Migración: campos OAuth2 en tabla 'usuarios'")
    print("═" * 60)

    with engine.begin() as conn:
        existentes = columnas_existentes(conn, "usuarios")
        print(f"\nColumnas actuales encontradas: {len(existentes)}")

        agregadas = 0
        for nombre, definicion in COLUMNAS_OAUTH:
            if nombre in existentes:
                print(f"  [SKIP]  {nombre} — ya existe")
            else:
                sql = f"ALTER TABLE usuarios ADD COLUMN {nombre} {definicion};"
                conn.execute(text(sql))
                print(f"  [OK]    {nombre} — agregada ({definicion})")
                agregadas += 1

        # Crear índice en proveedor_id si no existe (consultas OAuth por sub/id)
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_usuarios_proveedor_id
            ON usuarios (proveedor_id)
            WHERE proveedor_id IS NOT NULL;
        """))
        print("\n  [OK]    Índice ix_usuarios_proveedor_id — verificado/creado")

        # Asegurar que los usuarios existentes tengan proveedor_auth='local'
        result = conn.execute(
            text("UPDATE usuarios SET proveedor_auth = 'local' WHERE proveedor_auth IS NULL")
        )
        if result.rowcount > 0:
            print(f"  [OK]    {result.rowcount} usuarios existentes actualizados con proveedor_auth='local'")

    print(f"\n{'═' * 60}")
    print(f"  Migración completada: {agregadas} columna(s) nueva(s) agregada(s).")
    print("═" * 60)


if __name__ == "__main__":
    try:
        migrar()
    except Exception as e:
        print(f"\n[ERROR] La migración falló: {e}", file=sys.stderr)
        sys.exit(1)
