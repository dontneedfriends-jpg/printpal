import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In packaged mode, script runs from resources/ which is read-only in asar
# Check if we're running from a resources path (packaged Electron)
is_packaged = 'resources' in BASE_DIR.lower() or getattr(sys, 'frozen', False)

if is_packaged:
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    DATA_DIR = os.path.join(app_data, "PrintPAL", "data")
else:
    DATA_DIR = os.environ.get("FLASK_DATA_DIR", BASE_DIR)

os.makedirs(DATA_DIR, exist_ok=True)

DATABASE = os.path.join(DATA_DIR, "filament.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_ELECTRICITY_RATE = 5.0
DEFAULT_BASE_RATE = 50.0
DEFAULT_MARKUP_PERCENT = 20.0
