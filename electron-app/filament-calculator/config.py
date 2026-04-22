import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

is_packaged = 'resources' in BASE_DIR.lower() or getattr(sys, 'frozen', False)

if is_packaged:
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    DATA_DIR = os.path.join(app_data, "PrintPAL", "data")
    LOG_DIR = os.path.join(app_data, "PrintPAL", "logs")
else:
    DATA_DIR = os.environ.get("FLASK_DATA_DIR", BASE_DIR)
    LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, "filament.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOG_FILE = os.path.join(LOG_DIR, "printpal.log")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_ELECTRICITY_RATE = 5.0
DEFAULT_BASE_RATE = 50.0
DEFAULT_MARKUP_PERCENT = 20.0

HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
