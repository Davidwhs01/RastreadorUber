import sys
import os
from pathlib import Path

app_path = Path("app.py")
new_classes_path = Path("classes_v4.py")

with open(app_path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

idx = -1
for i, line in enumerate(lines):
    if line.startswith("class RastreadorApp("):
        idx = i
        break

if idx == -1:
    print("Erro: não achou a classe RastreadorApp no app.py atual")
    sys.exit(1)

top_half = "\n".join(lines[:idx])

with open(new_classes_path, "r", encoding="utf-8") as f:
    bottom_half = f.read()

new_app = top_half + "\n" + bottom_half

with open(app_path, "w", encoding="utf-8") as f:
    f.write(new_app)

print("SUCESSO: app.py foi sobrescrito com a nova arquitetura v4.0.0")
