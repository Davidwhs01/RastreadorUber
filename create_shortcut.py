"""
╔══════════════════════════════════════════════════════════════╗
║     CRIAR ATALHO — UberTrack by Delta                         ║
║     Delta Silk Print                                         ║
╚══════════════════════════════════════════════════════════════╝

Cria atalho na Área de Trabalho apontando para o app.

Uso: python create_shortcut.py
"""

import os
import sys
import subprocess
from pathlib import Path


def get_desktop() -> Path:
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '[Environment]::GetFolderPath("Desktop")'],
            capture_output=True, text=True
        )
        desktop = Path(result.stdout.strip())
        if desktop.exists():
            return desktop
    except Exception:
        pass
    home = Path(os.environ.get("USERPROFILE", Path.home()))
    for name in ["Desktop", "Área de Trabalho"]:
        p = home / name
        if p.exists():
            return p
    return home / "Desktop"


def find_target() -> Path:
    base = Path(__file__).resolve().parent
    # Prioridade 1: .exe compilado
    for p in [
        base / "dist" / "RastreadorUber3" / "RastreadorUber3.exe",
        base / "dist" / "RastreadorUber3.exe",
    ]:
        if p.exists():
            return p
    # Fallback: .bat launcher
    bat = base / "RastreadorUber.bat"
    if bat.exists():
        return bat
    # Fallback: .exe esperado
    return base / "dist" / "RastreadorUber3" / "RastreadorUber3.exe"


def create_shortcut():
    if os.name != "nt":
        print("❌ Só funciona no Windows.")
        sys.exit(1)

    target = find_target()
    desktop = get_desktop()
    shortcut_path = desktop / "UberTrack.lnk"

    print(f"📁 Alvo:      {target}")
    print(f"🖥️  Desktop:   {desktop}")

    ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{target}"
$s.WorkingDirectory = "{target.parent}"
$s.Description = "UberTrack by Delta"
$s.WindowStyle = 1
$s.Save()
Write-Host "OK"
'''
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True
    )

    if "OK" in result.stdout:
        print(f"\u2705 Atalho criado: 'UberTrack' na \u00c1rea de Trabalho")
    else:
        print(f"❌ Falha: {result.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    create_shortcut()
