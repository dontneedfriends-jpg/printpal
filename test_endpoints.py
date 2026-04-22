import sys
sys.path.insert(0, r"C:\Users\annenskei\Documents\GitHub\printpal\electron-app\filament-calculator")

from app import app

print("Registered endpoints:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.endpoint:30s} -> {rule.rule}")

print("\nChecking aliases:")
for ep in ['printers', 'filaments', 'calculator', 'history', 'settings', 'shpoolken', 'about', 'index']:
    print(f"  {ep}: {'OK' if ep in app.view_functions else 'MISSING'}")
