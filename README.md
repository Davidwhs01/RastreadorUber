# UberTrack

**UberTrack** é um aplicativo desktop projetado para monitorar corridas da Uber em tempo real, focado em agilidade e precisão. Ele automatiza a extração de dados do link de acompanhamento de viagem e exibe informações vitais como nome do motorista, placa, modelo do carro e tempo estimado de chegada.

## Principais Recursos

- **Monitoramento em Tempo Real:** Acompanha continuamente o tempo restante da viagem.
- **Alertas de Voz:** Notificações em áudio informando quando faltam 10, 5 e 3 minutos para a chegada do motorista.
- **Interface Moderna:** Construída com `customtkinter` para um visual elegante, "Dark Mode" por padrão, com design responsivo.
- **Auto-Update:** Sistema integrado que verifica novas versões no GitHub e as instala automaticamente, ou abre o navegador em caso de falha.
- **Portabilidade:** Empacotado em um único `.exe` via PyInstaller, facilitando a distribuição e a instalação para usuários locais.

## Tecnologias Utilizadas

- **Linguagem Principal:** Python 3.11/3.13
- **Interface Gráfica (GUI):** `customtkinter`
- **Scraping/Automação:** `selenium` (Chrome WebDriver)
- **Text-to-Speech:** `pyttsx3`
- **Build / Deploy:** `PyInstaller` e `Inno Setup Compiler`

## Instalação e Uso

### Para Usuários Finais:
Baixe a versão mais recente na aba [Releases](https://github.com/Davidwhs01/RastreadorUber/releases) do repositório. O instalador (`UberTrack_Setup.exe`) cuidará de extrair os arquivos e criar um atalho na Área de Trabalho.

### Para Desenvolvedores:

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/Davidwhs01/RastreadorUber.git
   cd RastreadorUber
   ```

2. **Crie um ambiente virtual (Recomendado Python 3.11 para build):**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install customtkinter selenium pyttsx3 pypiwin32 pillow
   ```

4. **Execute localmente:**
   ```bash
   python app.py
   ```

## Compilando o Projeto

O projeto usa um script próprio `build.py` para automatizar o empacotamento com o PyInstaller. A compilação *deve* ser feita no Python 3.11 para evitar problemas de compatibilidade ou crashes relacionados a threads/CTypes no empacotamento.

Para realizar a build:
```bash
python build.py
```
Isso gerará os arquivos na pasta `dist/UberTrack/`.

Para compilar o Instalador (necessita Inno Setup 6 instalado):
Abra o `installer.iss` no Inno Setup ou rode via linha de comando local.

---

**Criado por Delta Silk Print**
