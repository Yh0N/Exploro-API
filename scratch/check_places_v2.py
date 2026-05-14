from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://exploro_user:exploro_password@localhost:5433/exploro_db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id_lugar, nombre, categoria, aprobado FROM lugares"))
    places = result.fetchall()
    print(f"Found {len(places)} places:")
    for p in places:
        print(f"ID: {p[0]}, Nombre: {p[1]}, Categoria: {p[2]}, Aprobado: {p[3]}")
