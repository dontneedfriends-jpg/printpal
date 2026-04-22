import os

app_path = r"C:\Users\annenskei\Documents\GitHub\printpal\electron-app\filament-calculator\app.py"

with open(app_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find start line (0-indexed) containing PRESETS = {
start_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("PRESETS = {"):
        start_idx = i
        break

if start_idx is None:
    print("PRESETS start not found")
    exit(1)

# Find end line: matching closing brace
brace_count = 0
in_string = None
escape = False
end_idx = None
for i in range(start_idx, len(lines)):
    line = lines[i]
    for j, ch in enumerate(line):
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
                end_idx = i
                break
    if end_idx is not None:
        break

if end_idx is None:
    print("PRESETS end not found")
    exit(1)

replacement = '''_PRESETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes.json")
with open(_PRESETS_PATH, "r", encoding="utf-8") as f:
    PRESETS = json.load(f)
'''

new_lines = lines[:start_idx] + [replacement] + lines[end_idx+1:]

with open(app_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Removed PRESETS block lines {start_idx+1}..{end_idx+1}")
print(f"Total lines before: {len(lines)}, after: {len(new_lines)}")
