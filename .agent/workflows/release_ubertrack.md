---
description: Como fazer o release completo do UberTrack (Build, InnoSetup e GitHub)
---

# Passo a passo para o Release Oficial do UberTrack

Siga estas etapas para compilar, empacotar e mandar atualizações para todos os usuários através do GitHub Auto Update sem nenhum erro.

## 1. Atualizar as Versões
Antes de "buildar", todas as referências da nova versão precisam estar alinhadas (ex: `3.2.0`).

Edite o arquivo `version.json` na raiz da pasta `RastreadorUber`:
```json
{
    "version": "3.2.0",
    "github_repo": "Davidwhs01/RastreadorUber",
    "changelog": "Novidade incrível e correções."
}
```

Edite o topo do arquivo `installer.iss`:
```inno
#define MyAppVersion "3.2.0"
```

---

## 2. Limpar a poeira
Certifique-se de que nenhum cache velho influencie o build novo executando o script para remover vestígios passados:

// turbo
```powershell
Remove-Item -Recurse -Force build, dist, __pycache__ -ErrorAction SilentlyContinue
```

---

## 3. Buildar o Executável (Backend Python)
Use o seu `build.py` automatizado. Ele vai coletar o customtkinter, bibliotecas, criar a estrutura e embutir o ícone (certifique-se de ter um `icon.ico` nativo na raiz).

// turbo
```powershell
python build.py
```
*O executável do app já compilado com todas as dependências do Chrome será cuspido dentro da pasta `dist/UberTrack`.*

---

## 4. Empacotar o Instalador Novo (.exe de Setup)
Com o sistema pronto, compile a magia em uma "setup" bonita para facilitar quem for instalar o software do zero pela primeira vez, usando o Inno Setup.

*Atenção para não errar o caminho do compilador `ISCC.exe`.*

// turbo
```powershell
& "C:\Users\doug_\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
```
*O novo `UberTrack_Setup.exe` brotará dentro da pasta `installer_output/`.*

---

## 5. Zipar os Arquivos para o Auto-Updater
Como o seu próprio código-fonte atualiza o aplicativo buscando um arquivo `.zip` para baixar escondido (em vez do instalador), é preciso ZIPAR obrigatoriamente a pasta `dist` gerada lá no passo 3.

// turbo
```powershell
Get-ChildItem -Path dist\UberTrack\* | Compress-Archive -DestinationPath installer_output\UberTrack_3.2.0.zip -Force
```

---

## 6. Lançar o Foguete no GitHub (Releases)

Com o `Setup.exe` (para pessoas novas) e o `.zip` (para quem for clicar em "Atualizar" no app) prontos, mande e crie a Release Oficial na nuvem.

Gere a página do Release oficial lá no Github (mude o **v3.2.0** para o número correto e escreva as notas de atualização reais entre as aspas):

// turbo
```powershell
gh release create v3.2.0 installer_output/UberTrack_Setup.exe --title "UberTrack v3.2.0" --notes "Aqui as notas de update. O app atualiza auto!"
```

Logo depois, para terminar de engatilhar os atualizadores silenciosos, faça "upload" (anexo extra) do arquivo .zip também nessa Release criada acima para ela ter as duas opções:

// turbo
```powershell
gh release upload v3.2.0 installer_output/UberTrack_3.2.0.zip --clobber
```

> ⚠️ **Atenção Máxima com o Upload do ZIP!**
> Se a sua internet oscilar ou o comando de `upload` do `.zip` for interrompido pela metade, o arquivo corrompido ou inexistente no GitHub fará o **botão "Atualizar" do aplicativo retornar "❌ Falha"** para os clientes! 
> Sempre observe o terminal e garanta que ele imprimiu "100% complete" explícito antes de fechar a janela. Caso falhe, rode o `upload --clobber` de novo tranquilamente.

## Conclusão
E pronto! Com isso, o GitHub tem a nova "Tag" Oficial, novas atualizações para auto-update e o arquivo EXE para primeira viagem. Tudo amarrado sem risco de esquecer dependências!
