import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.environ.get("FLASK_DATA_DIR", BASE_DIR)
DATABASE = os.path.join(DATA_DIR, "filament.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

DEFAULT_ELECTRICITY_RATE = 5.0
DEFAULT_BASE_RATE = 50.0
DEFAULT_MARKUP_PERCENT = 20.0
