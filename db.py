# """
# Single shared SQLAlchemy engine. Everything else (order_service.py, main.py)
# imports `engine` from here instead of creating its own connection.
# """

# from sqlalchemy import create_engine

# USERNAME = "postgres"
# PASSWORD = "MSS123"
# HOST = "localhost"
# PORT = "5432"
# DB_NAME = "orders"

# engine = create_engine(f"postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}")

"""
Single shared SQLAlchemy engine. Everything else (order_service.py, main.py)
imports `engine` from here instead of creating its own connection.
 
Reads the connection string from the DATABASE_URL environment variable
(this is how Railway, Render, Heroku, etc. all hand you your DB credentials).
Falls back to a local Postgres instance for local development, so nothing
changes for you when running on your own machine.
"""
 
import os
from sqlalchemy import create_engine
 
DEFAULT_LOCAL_URL = "postgresql+psycopg2://postgres:MSS123@localhost:5432/orders"
 
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_LOCAL_URL)
 
# Railway/Render/Heroku often hand back "postgres://..." -- SQLAlchemy needs
# the "postgresql+psycopg2://..." form, so normalize it if needed.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
 
engine = create_engine(DATABASE_URL)