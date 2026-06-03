import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load env variables from backend/.env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_scheduler.db")

# Ensure relative SQLite path is resolved relative to the workspace root directory
if DATABASE_URL.startswith("sqlite:///."):
    workspace_root = os.path.dirname(backend_dir)
    db_file_name = DATABASE_URL.replace("sqlite:///./", "")
    db_absolute_path = os.path.join(workspace_root, db_file_name)
    DATABASE_URL = f"sqlite:///{db_absolute_path}"

# SQLite needs check_same_thread set to False
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
