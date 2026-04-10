import os
import sys

if hasattr(sys, 'frozen'):
    app_dir = os.path.dirname(sys.executable)
    resources = os.path.join(app_dir, 'resources')
    python_dir = os.path.join(app_dir, 'python')
    flask_dir = os.path.join(resources, 'filament-calculator')
    sys.path.insert(0, os.path.join(app_dir, 'python'))
    sys.path.insert(0, flask_dir)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    flask_dir = os.path.join(app_dir, 'filament-calculator')
    sys.path.insert(0, flask_dir)

os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

from app import app
app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)