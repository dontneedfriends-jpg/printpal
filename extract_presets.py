import ast
import json
import os

app_path = r"C:\Users\annenskei\Documents\GitHub\printpal\electron-app\filament-calculator\app.py"
themes_path = r"C:\Users\annenskei\Documents\GitHub\printpal\electron-app\filament-calculator\themes.json"

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "PRESETS = {"
start = content.find(start_marker)
if start == -1:
    print("PRESETS not found")
    exit(1)

# Find the matching closing brace
brace_count = 0
in_string = None
escape = False
i = start + len(start_marker) - 1  # start at the '{'
for i in range(start + len(start_marker) - 1, len(content)):
    ch = content[i]
    if escape:
        escape = False
        continue
    if ch == '\\' and in_string:
        escape = True
        continue
    if in_string:
        if ch == in_string:
            in_string = None
        continue
    if ch in ('"', "'"):
        in_string = ch
        continue
    if ch == '{':
        brace_count += 1
    elif ch == '}':
        brace_count -= 1
        if brace_count == 0:
            break

end = i + 1
presets_text = content[start + len("PRESETS = "):end]
presets = ast.literal_eval(presets_text)

with open(themes_path, "w", encoding="utf-8") as f:
    json.dump(presets, f, ensure_ascii=False, indent=2)

print("themes.json created successfully")
print(f"Bytes written: {os.path.getsize(themes_path)}")
