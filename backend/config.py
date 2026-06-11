import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///audit.db")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "credit-decisions")

MODEL_PATH = os.getenv("MODEL_PATH", "models/credit_model.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "models/scaler.pkl")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

LEGACY_DB_HOST = os.getenv("LEGACY_DB_HOST", "localhost")
LEGACY_DB_PORT = int(os.getenv("LEGACY_DB_PORT", 5432))
LEGACY_DB_NAME = os.getenv("LEGACY_DB_NAME", "legacy_bank")
LEGACY_DB_USER = os.getenv("LEGACY_DB_USER", "admin")
LEGACY_DB_PASSWORD = os.getenv("LEGACY_DB_PASSWORD", "admin123")

FAIRNESS_WINDOW_SIZE = int(os.getenv("FAIRNESS_WINDOW_SIZE", 500))
DEMOGRAPHIC_PARITY_THRESHOLD = float(os.getenv("DEMOGRAPHIC_PARITY_THRESHOLD", 0.80))
