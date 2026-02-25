# 🧠 Memória do Projeto UberTrack

## Ambiente de Desenvolvimento

| Item | Valor |
|------|-------|
| **Python para BUILD** | `C:\Users\doug_\AppData\Local\Programs\Python\Python311\python.exe` (Python **3.11.9**) |
| **Python do sistema (CLI)** | `C:\Python313\python.exe` (Python **3.13.7**) |
| **PyInstaller** | Instalado no Python **3.11** (`pip install pyinstaller` no 3.11) |
| **pyttsx3** | Instalado no Python **3.11** (`pip install pyttsx3 pypiwin32`) e **3.13** |
| **Inno Setup Compiler** | `C:\Users\doug_\AppData\Local\Programs\Inno Setup 6\ISCC.exe` |
| **GitHub CLI (gh)** | Disponível globalmente no PATH |

## Caminhos Importantes

| Arquivo/Pasta | Caminho |
|--------------|---------|
| **Código-fonte** | `D:\Downloads\DeltaCentral\RastreadorUber\` |
| **app.py** (principal) | `D:\Downloads\DeltaCentral\RastreadorUber\app.py` |
| **build.py** (empacotador) | `D:\Downloads\DeltaCentral\RastreadorUber\build.py` |
| **installer.iss** (Inno Setup) | `D:\Downloads\DeltaCentral\RastreadorUber\installer.iss` |
| **version.json** | `D:\Downloads\DeltaCentral\RastreadorUber\version.json` |
| **Ícone** | `D:\Downloads\DeltaCentral\RastreadorUber\icon.ico` |
| **Output dist** | `D:\Downloads\DeltaCentral\RastreadorUber\dist\UberTrack\` |
| **Output installer** | `D:\Downloads\DeltaCentral\RastreadorUber\installer_output\` |
| **Instalação do usuário** | `C:\Users\doug_\AppData\Local\Programs\UberTrack\` |
| **Workflow de release** | `D:\Downloads\DeltaCentral\RastreadorUber\.agent\workflows\release_ubertrack.md` |
| **GitHub Repo** | `Davidwhs01/RastreadorUber` |

## Regras Críticas de Build

> ⚠️ **SEMPRE use o Python 3.11 para rodar `build.py`!**
> O comando correto é:
> ```powershell
> $env:PYTHONIOENCODING="utf-8"; & 'C:\Users\doug_\AppData\Local\Programs\Python\Python311\python.exe' build.py
> ```
> Se rodar com o Python 3.13 do sistema, o PyInstaller usa o 3.11 por baixo, mas as bibliotecas user site-packages do 3.13 NÃO são encontradas.

> ⚠️ **Novas dependências Python devem ser instaladas no Python 3.11!**
> ```powershell
> & 'C:\Users\doug_\AppData\Local\Programs\Python\Python311\python.exe' -m pip install <pacote>
> ```

> ⚠️ **O upload do ZIP para o GitHub DEVE completar 100%!**
> Se for interrompido, o auto-updater dos clientes vai falhar silenciosamente. Sempre verifique a mensagem "Successfully uploaded" no terminal.

## Processo de Release Completo

1. Atualizar versão em `version.json` e `installer.iss`
2. Limpar: `Remove-Item -Recurse -Force build, dist, __pycache__`
3. Build: `$env:PYTHONIOENCODING="utf-8"; & '...\Python311\python.exe' build.py`
4. Installer: `& "...\Inno Setup 6\ISCC.exe" installer.iss`
5. ZIP: `Get-ChildItem -Path dist\UberTrack\* | Compress-Archive -DestinationPath installer_output\UberTrack_X.Y.Z.zip -Force`
6. GitHub Release: `gh release create vX.Y.Z installer_output/UberTrack_Setup.exe --title "..." --notes "..."`
7. Upload ZIP: `gh release upload vX.Y.Z installer_output/UberTrack_X.Y.Z.zip`
8. Push código: `git add . ; git commit -m "..." ; git push`

## Bugs Conhecidos e Soluções

| Bug | Causa | Solução |
|-----|-------|---------|
| `pyttsx3 not found` no .exe | PyInstaller 3.11 não achava o pacote | Instalado pyttsx3 no Python 3.11 + lazy import |
| "Identificando..." eterno | Regex exigia `.isupper()`, mas Uber mostra nomes capitalizados | Relaxada a regex para aceitar nomes com capitalização normal |
| Voz só falava nos 3 min | `tocar_alerta()` só tinha condição `minutos==3` | Expandido para falar em 10, 5 e ≤3 min |
| Auto-update "❌ Falha" | `.old` files bloqueavam rename; ZIP incompleto no GitHub | UUID no rename + fallback abre navegador |
