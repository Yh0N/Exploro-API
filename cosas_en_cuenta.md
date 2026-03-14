1️⃣ .env.example

Plantilla pública (esto sí se sube a Git):

POSTGRES_USER=exploro_user
POSTGRES_PASSWORD=exploro_password
POSTGRES_DB=exploro_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgresql://exploro_user:exploro_password@db:5432/exploro_db

SECRET_KEY=supersecretkey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
2️⃣ .env

Archivo privado (NO subir a Git):

POSTGRES_USER=exploro_user
POSTGRES_PASSWORD=exploro_password
POSTGRES_DB=exploro_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgresql://exploro_user:exploro_password@db:5432/exploro_db

SECRET_KEY=exploro_secret_key_2025
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
3️⃣ requirements.txt
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-dotenv
geoalchemy2
python-jose[cryptography]
passlib[bcrypt]
pydantic-settings
pytest
httpx
4️⃣ docker-compose.yml

Aquí levantamos API + PostGIS juntos.

version: "3.9"

services:

  db:
    image: postgis/postgis:15-3.3
    container_name: exploro_db
    restart: always
    env_file:
      - .env
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    container_name: exploro_api
    depends_on:
      - db
    env_file:
      - .env
    ports:
      - "8000:8000"
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app

volumes:
  postgres_data: