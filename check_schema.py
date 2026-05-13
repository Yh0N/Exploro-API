"""Script temporal para verificar el esquema de la tabla lugares."""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = 'lugares' "
        "ORDER BY ordinal_position"
    ))
    for row in result:
        print(row)
