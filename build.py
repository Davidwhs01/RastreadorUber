"""
╔══════════════════════════════════════════════════════════════╗
║            BUILD — Rastreador Uber 3.0 (Único .exe)         ║
║            Criado por Delta Silk Print                       ║
╚══════════════════════════════════════════════════════════════╝

Gera um único executável .exe com interface gráfica nativa.
Sem terminal, sem browser.

Uso: python build.py
"""

import os
import subprocess
import sys
import shutil
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
APP_FILE = BASE_DIR / "app.py"
VERSION_FILE = BASE_DIR / "version.json"
DIST_DIR = BASE_DIR / "dist"

APP_NAME = "RastreadorUber3"


def print_header():
    print("""
╔══════════════════════════════════════════════════════════╗
║     🚗  BUILD — Rastreador Uber 3.0                     ║
║     Gera um único .exe com interface gráfica             ║
║     Delta Silk Print                                     ║
╚══════════════════════════════════════════════════════════╝
    """)


def read_version() -> str:
    if VERSION_FILE.exists():
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "3.1.0")
    return "3.1.0"


def run_cmd(cmd: str, cwd=None, label=""):
    if label:
        print(f"\n{'─' * 50}")
        print(f"  {label}")
        print(f"{'─' * 50}")
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"\n  ❌ Falhou: {cmd}")
        sys.exit(result.returncode)
    print(f"  ✔ Concluído")


def create_desktop_shortcut(exe_path: Path):
    """Cria atalho .lnk na Área de Trabalho via PowerShell."""
    if os.name != "nt":
        return

    # Detecta Desktop
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '[Environment]::GetFolderPath("Desktop")'],
            capture_output=True, text=True
        )
        desktop = Path(result.stdout.strip())
    except Exception:
        desktop = Path(os.environ.get("USERPROFILE", "~")) / "Desktop"

    shortcut_path = desktop / "Rastreador Uber 3.0.lnk"

    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{exe_path}"
$s.WorkingDirectory = "{exe_path.parent}"
$s.Description = "Rastreador Uber 3.0 - Delta Silk Print"
$s.WindowStyle = 1
$s.Save()
Write-Host "OK"
'''
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True
    )
    return "OK" in result.stdout


def main():
    print_header()
    version = read_version()
    print(f"  Versão: {version}")

    if not APP_FILE.exists():
        print(f"❌ Arquivo 'app.py' não encontrado em {BASE_DIR}")
        sys.exit(1)

    # ─── Dados a incluir ──────────────────────────────────────────────────
    separator = ";" if os.name == "nt" else ":"
    add_data = []

    # ─── Ícone ────────────────────────────────────────────────────────────
    icon_path = BASE_DIR / "icon.ico"
    icon_arg = f'--icon="{icon_path}"' if icon_path.exists() else ""

    if VERSION_FILE.exists():
        add_data.append(f'--add-data="{VERSION_FILE}{separator}."')

    if icon_path.exists():
        add_data.append(f'--add-data="{icon_path}{separator}."')

    # RASTREAR UBER.py também precisa estar junto
    tracker = BASE_DIR / "RASTREAR UBER.py"
    if tracker.exists():
        add_data.append(f'--add-data="{tracker}{separator}."')

    # ─── Hidden imports ───────────────────────────────────────────────────
    hidden = [
        "--hidden-import=customtkinter",
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver",
        "--hidden-import=selenium.webdriver.chrome",
        "--hidden-import=selenium.webdriver.chrome.service",
        "--hidden-import=selenium.webdriver.common.by",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
    ]

    # ─── Collect customtkinter data ───────────────────────────────────────
    # customtkinter precisa que seus assets sejam incluídos
    collect = [
        "--collect-all=customtkinter",
    ]

    # ─── PyInstaller command ──────────────────────────────────────────────
    cmd_parts = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",           # onedir é mais confiável que onefile para customtkinter
        "--windowed",          # SEM TERMINAL!
        f'"{APP_FILE}"',
        *add_data,
        *hidden,
        *collect,
        f"-n {APP_NAME}",
        icon_arg,
    ]

    cmd = " ".join(filter(None, cmd_parts))
    run_cmd(cmd, cwd=BASE_DIR, label="⚙️  Empacotando com PyInstaller")

    # ─── Copiar version.json para dist ────────────────────────────────────
    dist_app = DIST_DIR / APP_NAME
    if dist_app.exists() and VERSION_FILE.exists():
        shutil.copy2(VERSION_FILE, dist_app / "version.json")
        print("  ✔ version.json copiado para dist")

    # ─── Criar atalho ─────────────────────────────────────────────────────
    exe_path = dist_app / f"{APP_NAME}.exe"
    print(f"\n{'─' * 50}")
    print(f"  🖥️  Criando atalho na Área de Trabalho")
    print(f"{'─' * 50}")

    if create_desktop_shortcut(exe_path):
        print("  ✔ Atalho 'Rastreador Uber 3.0' criado!")
    else:
        print("  ⚠ Não foi possível criar atalho automaticamente")

    # ─── Resultado ────────────────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════════════════════════╗
║     ✅  BUILD FINALIZADO COM SUCESSO!                    ║
╠══════════════════════════════════════════════════════════╣
║  App:     {APP_NAME}.exe
║  Versão:  {version}
║  Pasta:   {dist_app}
║  Atalho:  Área de Trabalho → Rastreador Uber 3.0
║  Terminal: NÃO (windowed mode)
╚══════════════════════════════════════════════════════════╝

  Para distribuir: compartilhe a pasta '{APP_NAME}/' inteira.
  Os clientes precisam de Chrome ou Brave instalado.
    """)


if __name__ == "__main__":
    main()
