import sys
sys.path.insert(0, r"C:\Users\annenskei\Documents\GitHub\printpal\electron-app\filament-calculator")

from app import app, _BLUEPRINTS

print("view_functions keys sample:")
for k in list(app.view_functions.keys())[:10]:
    print(f"  {k}")

for _bp in _BLUEPRINTS:
    for _endpoint in _bp.view_functions:
        _aliased = f"{_bp.name}.{_endpoint}"
        print(f"Checking alias: {_endpoint} -> {_aliased}")
        print(f"  _aliased in app.view_functions: {_aliased in app.view_functions}")
        if _aliased in app.view_functions:
            print(f"  adding alias")
            app.view_functions[_endpoint] = app.view_functions[_aliased]
        else:
            print(f"  SKIPPED")

print("\nAfter aliases:")
for ep in ['printers', 'filaments']:
    print(f"  {ep}: {'OK' if ep in app.view_functions else 'MISSING'}")
