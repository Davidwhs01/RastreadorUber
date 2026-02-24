"""
╔══════════════════════════════════════════════════════════╗
║           RASTREADOR UBER  - Versão 3.0 Premium          ║
║  Placa · Motorista · Modelo · Cor · Chegada · Entrega    ║
╚══════════════════════════════════════════════════════════╝
Dependências: pip install selenium plyer colorama

  → Digite DEBUG no lugar do link para testar todas as funções
    sem precisar abrir o navegador.
"""

import time
import os
import re
import sys
import signal
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

# Pasta onde o script está — log e arquivos vão sempre para cá
_PASTA_SCRIPT = Path(__file__).resolve().parent

# ─── DEPENDÊNCIAS OPCIONAIS ───────────────────────────────────────────────────
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    TEM_COR = True
except ImportError:
    TEM_COR = False
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""

try:
    from plyer import notification
    TEM_PLYER = True
except ImportError:
    TEM_PLYER = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    TEM_SELENIUM = True
except ImportError:
    TEM_SELENIUM = False

# ─── CONFIGURAÇÕES ─────────────────────────────────────────────────────────────
CONFIG = {
    "CAMINHO_NAVEGADOR": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "MINUTOS_ALERTA":    3,
    "INTERVALO_NORMAL":  30,
    "INTERVALO_URGENTE": 10,
    "SALVAR_LOG":        True,
    "ARQUIVO_LOG":       str(_PASTA_SCRIPT / "uber_tracker.log"),

    # Debug: segundos reais por etapa simulada (2s = rápido para teste)
    "DEBUG_VELOCIDADE":  2,
}

# ─── ESTRUTURA DE DADOS DA VIAGEM ─────────────────────────────────────────────
@dataclass
class DadosViagem:
    placa:     Optional[str] = None
    motorista: Optional[str] = None
    modelo:    Optional[str] = None
    cor:       Optional[str] = None
    chegada:   Optional[str] = None
    minutos:   Optional[int] = None
    origem:    Optional[str] = None
    destino:   Optional[str] = None
    tipo_veiculo: Optional[str] = None
    modalidade: Optional[str] = None
    status:    str = "aguardando"
    historico: list = field(default_factory=list)

    def resumo(self) -> str:
        partes = []
        if self.modalidade: partes.append(f"Modo: {self.modalidade}")
        if self.tipo_veiculo: partes.append(f"Tipo: {self.tipo_veiculo}")
        if self.placa:     partes.append(f"Placa: {self.placa}")
        if self.motorista: partes.append(f"Motorista: {self.motorista}")
        if self.modelo:    partes.append(f"Veículo: {self.modelo}")
        if self.cor:       partes.append(f"Cor: {self.cor}")
        if self.chegada:   partes.append(f"Chegada: {self.chegada}")
        return " | ".join(partes) if partes else "Dados ainda não detectados"


# ─── LOGGER ───────────────────────────────────────────────────────────────────
class Logger:
    def __init__(self, salvar: bool, arquivo: str):
        self.salvar  = salvar
        self.arquivo = arquivo

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _gravar(self, linha: str):
        if not self.salvar:
            return
        try:
            with open(self.arquivo, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {linha}\n")
        except PermissionError:
            # Sem permissão na pasta do script → tenta %TEMP% / /tmp
            fallback = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))) / "uber_tracker.log"
            try:
                with open(fallback, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {linha}\n")
                self.arquivo = str(fallback)   # usa fallback daqui pra frente
                print(f"{Fore.YELLOW}  [log] Sem permissão na pasta do script. "
                      f"Salvando em: {fallback}{Style.RESET_ALL}")
            except Exception:
                self.salvar = False            # desiste silenciosamente
        except Exception:
            self.salvar = False

    def info(self, msg: str):
        print(f"{Fore.CYAN}[{self._ts()}]{Style.RESET_ALL} {msg}")
        self._gravar(msg)

    def ok(self, msg: str):
        print(f"{Fore.GREEN}[{self._ts()}] ✔ {msg}{Style.RESET_ALL}")
        self._gravar(f"[OK] {msg}")

    def alerta(self, msg: str):
        print(f"{Fore.YELLOW}{Style.BRIGHT}[{self._ts()}] ⚠  {msg}{Style.RESET_ALL}")
        self._gravar(f"[ALERTA] {msg}")

    def urgente(self, msg: str):
        print(f"{Fore.RED}{Style.BRIGHT}[{self._ts()}] 🚨 {msg}{Style.RESET_ALL}")
        self._gravar(f"[URGENTE] {msg}")

    def entregue(self, msg: str):
        print(f"{Fore.GREEN}{Style.BRIGHT}[{self._ts()}] 📦 {msg}{Style.RESET_ALL}")
        self._gravar(f"[ENTREGUE] {msg}")

    def debug(self, msg: str):
        print(f"{Fore.MAGENTA}[{self._ts()}] 🛠  [DEBUG] {msg}{Style.RESET_ALL}")

    def ponto(self):
        print(f"{Style.DIM}.{Style.RESET_ALL}", end="", flush=True)


logger = Logger(CONFIG["SALVAR_LOG"], CONFIG["ARQUIVO_LOG"])


# ─── SOM ───────────────────────────────────────────────────────────────────────
import queue
import threading

tts_queue = queue.Queue()

def _tts_worker():
    import pythoncom
    pythoncom.CoInitialize()
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)  # Falar ligeiramente mais rápido
    except Exception as e:
        print("Erro init pyttsx3:", e)
        return
        
    while True:
        try:
            texto = tts_queue.get()
            if texto:
                engine.say(texto)
                engine.runAndWait()
            tts_queue.task_done()
        except Exception as e:
            print("Erro tts worker:", e)
            try:
                tts_queue.task_done()
            except:
                pass

threading.Thread(target=_tts_worker, daemon=True).start()

def tocar_alerta(urgente: bool = False, entregue: bool = False, minutos: int = None):
    texto = ""
    if entregue:
        texto = "A entrega foi concluída!"
    elif urgente:
        texto = "Atenção: O Uber está chegando!"
    elif minutos == 3:
        texto = "Atenção: Uber a 3 minutos."
        
    if texto:
        with tts_queue.mutex:
            tts_queue.queue.clear()
        tts_queue.put(texto)


# ─── NOTIFICAÇÃO ───────────────────────────────────────────────────────────────
def notificar(titulo: str, mensagem: str):
    if TEM_PLYER:
        try:
            notification.notify(
                title=titulo,
                message=mensagem,
                app_name="Uber Tracker 3.0",
                timeout=10,
            )
        except Exception as e:
            print("Erro tts worker:", e)
            try:
                tts_queue.task_done()
            except:
                pass


# ─── EXTRAÇÃO DE DADOS DA PÁGINA ──────────────────────────────────────────────
def extrair_dados(texto_bruto: str) -> DadosViagem:
    dados = DadosViagem()
    texto = texto_bruto.upper()

    # ORIGEM E DESTINO
    for linha in texto_bruto.split('\n'):
        linha = linha.strip()
        if linha.upper().startswith("DE ") and not dados.origem:
            dados.origem = linha[3:].strip()
        elif linha.upper().startswith("PARA ") and not dados.destino:
            dados.destino = linha[5:].strip()

    # MODALIDADE E TIPO VEÍCULO
    if any(k in texto for k in ["ITEM", "ENTREGA", "PEDIDO", "DELIVERY", "PACOTE"]):
        dados.modalidade = "Entrega"
    else:
        dados.modalidade = "Viagem"

    motos = ["HONDA CG", "YAMAHA", "TITAN", "BROS", "BIZ", "TWISTER", "FAZER", "NMAX", "PCX", "XRE"]
    if any(m in texto for m in motos) or "MOTO" in texto:
        dados.tipo_veiculo = "Moto"
    elif "BICICLETA" in texto or "BIKE" in texto:
        dados.tipo_veiculo = "Bicicleta"
    elif any(k in texto for k in ["UBER FLASH", "UBERX", "UBER BLACK"]):
        dados.tipo_veiculo = "Carro"

    # 1. PLACA — Mercosul (ABC1D23) ou Antigo (ABC1234)
    for padrao in [
        r'\b([A-Z]{3}\d[A-Z]\d{2})\b',
        r'\b([A-Z]{3}[-]?\d{4})\b',
    ]:
        m = re.search(padrao, texto)
        if m:
            dados.placa = m.group(1).replace("-", "")
            break

    # 2. HORÁRIO DE CHEGADA
    m = re.search(r'\b(\d{1,2}:\d{2})\s*(PM|AM)?\b', texto)
    if m:
        dados.chegada = f"{m.group(1)} {m.group(2) or ''}".strip()

    # 3. MINUTOS RESTANTES
    m = re.search(r'\b(\d{1,3})\s*MIN(?:UTO[S]?)?', texto)
    if m:
        dados.minutos = int(m.group(1))

    # 4. STATUS DA VIAGEM — ordem importa: entregue > cancelado > chegando > rota
    frases_entregue = (
        "ITEM FOI ENTREGUE", "FOI ENTREGUE", "ENTREGA CONCLUIDA",
        "ENTREGA CONCLUÍDA", "PEDIDO ENTREGUE", "DELIVERY COMPLETE",
        "DELIVERED", "ENTREGUE COM SUCESSO", "SUA ENTREGA FOI CONCLUIDA",
        "SUA ENTREGA FOI CONCLUÍDA",
    )
    frases_chegando = (
        "CHEGANDO", "ARRIVING", "CHEGOU", "ARRIVED",
        "MOTORISTA CHEGOU", "DRIVER HAS ARRIVED", "AQUI",
    )

    if any(k in texto for k in frases_entregue):
        dados.status = "entregue"
    elif any(k in texto for k in ("CANCELAD", "CANCELED")):
        dados.status = "cancelado"
    elif any(k in texto for k in frases_chegando):
        if dados.minutos is not None and dados.minutos > 3:
            dados.status = "em_rota"
        else:
            dados.status = "chegando"
    elif dados.minutos is not None:
        dados.status = "em_rota"
    else:
        dados.status = "aguardando"

    # 5. COR DO VEÍCULO
    for cor in ["BRANCO", "PRETO", "PRATA", "CINZA", "VERMELHO", "AZUL",
                "VERDE", "AMARELO", "MARROM", "BEGE", "LARANJA", "ROXO",
                "WHITE", "BLACK", "SILVER", "GRAY", "RED", "BLUE"]:
        if cor in texto:
            dados.cor = cor.capitalize()
            break

    # 6. MODELO DO VEÍCULO
    for modelo in ["FIAT UNO", "FIAT MOBI", "FIAT ARGO", "FIAT CRONOS",
                   "HB20", "ONIX", "GOL", "POLO", "VOYAGE", "CLIO",
                   "SANDERO", "LOGAN", "KWID", "CORSA", "PRISMA", "COBALT",
                   "TRACKER", "SPIN", "CIVIC", "FIT", "CITY", "HR-V",
                   "ETIOS", "YARIS", "COROLLA", "HILUX", "COMPASS",
                   "RENEGADE", "TORO", "KICKS", "MARCH", "VERSA",
                   "FUSION", "ECOSPORT", "KA"]:
        if modelo in texto:
            dados.modelo = modelo.title()
            break

    # 7. NOME DO MOTORISTA
    palavras_ignorar = {
        "MIN", "PM", "AM", "UBER", "VIAGEM", "CHEGADA", "ITEM", "PARA",
        "COM", "NAO", "SIM", "RUA", "AV", "AVE", "STATUS", "BRANCO",
        "PRETO", "PRATA", "CINZA", "DEBUG", "ENTREGUE", "ENTREGA",
    }
    for linha in texto_bruto.split("\n"):
        linha = linha.strip()
        if (3 <= len(linha) <= 20
                and linha.isupper()
                and linha not in palavras_ignorar
                and not re.search(r'\d', linha)
                and not any(k in linha for k in ["RUA", "AV.", "MIN", "PM", "AM"])):
            dados.motorista = linha.title()
            break

    return dados


# ─── EXIBIÇÃO ─────────────────────────────────────────────────────────────────
def exibir_banner(modo_debug: bool = False):
    os.system("cls" if os.name == "nt" else "clear")
    tag = f"  {Fore.MAGENTA}[DEBUG]{Fore.CYAN}" if modo_debug else "       "
    print(f"""
{Fore.CYAN}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════╗
║       🚗  RASTREADOR UBER 3.0  —  São Paulo  🗺️  {tag}  ║
║  Placa · Motorista · Modelo · Cor · Chegada · Entrega   ║
╚══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}""")


def exibir_painel(viagem: DadosViagem):
    print(f"""
{Fore.CYAN}┌──────────────────────────────────────────────┐
│  🚘  DADOS DO VEÍCULO                        │
├──────────────────────────────────────────────┤
│  Serviço:    {Fore.WHITE}{Style.BRIGHT}{(viagem.modalidade or '---'):20}{Style.RESET_ALL}{Fore.CYAN}  │
│  Tipo:       {Fore.WHITE}{(viagem.tipo_veiculo or '---'):20}{Fore.CYAN}  │
│  Placa:      {Fore.WHITE}{Style.BRIGHT}{(viagem.placa or 'Detectando...'):20}{Style.RESET_ALL}{Fore.CYAN}  │
│  Motorista:  {Fore.WHITE}{Style.BRIGHT}{(viagem.motorista or 'Detectando...'):20}{Style.RESET_ALL}{Fore.CYAN}  │
│  Modelo:     {Fore.WHITE}{(viagem.modelo or 'Detectando...'):20}{Fore.CYAN}  │
│  Cor:        {Fore.WHITE}{(viagem.cor or 'Detectando...'):20}{Fore.CYAN}  │
│  Origem:     {Fore.WHITE}{(viagem.origem[:18]+'...' if viagem.origem and len(viagem.origem)>18 else viagem.origem or '---'):20}{Fore.CYAN}  │
│  Destino:    {Fore.WHITE}{(viagem.destino[:18]+'...' if viagem.destino and len(viagem.destino)>18 else viagem.destino or '---'):20}{Fore.CYAN}  │
│  Chegada:    {Fore.GREEN}{Style.BRIGHT}{(viagem.chegada or 'Detectando...'):20}{Style.RESET_ALL}{Fore.CYAN}  │
└──────────────────────────────────────────────┘{Style.RESET_ALL}""")


def exibir_historico(viagem: DadosViagem):
    if not viagem.historico:
        return
    print(f"\n{Fore.CYAN}{'═'*52}")
    print(f"  📋  HISTÓRICO DA VIAGEM")
    print(f"{'═'*52}")
    for ts, mins in viagem.historico:
        print(f"  [{ts}]  {mins} min restantes")
    print(f"{'═'*52}{Style.RESET_ALL}\n")


# ─── MODO DEBUG — SIMULAÇÃO COMPLETA ──────────────────────────────────────────
def gerar_pagina_simulada(etapa: int) -> str:
    """
    Cada etapa retorna um texto simulando o conteúdo da página da Uber.

    Etapa 0  → Página carregando (sem dados)
    Etapa 1  → Carro identificado + 15 min
    Etapa 2  → 10 min  (notificação)
    Etapa 3  → 5 min   (notificação)
    Etapa 4  → 3 min   (alerta sonoro)
    Etapa 5  → 2 min   (urgente)
    Etapa 6  → 1 min   (urgente)
    Etapa 7  → Motorista chegando (CHEGANDO)
    Etapa 8  → Item foi entregue  (ENTREGUE)
    """
    base = "Uber\nDe Moda Saza\nPara Rua Galeão, 439 – Sapopemba\nInformações da viagem\n"

    etapas = [
        # 0 – carregando
        base + "Carregando informações da viagem...",

        # 1 – dados do carro + 15 min
        base + (
            "Chegada em 3:22 pm\n"
            "O item está a caminho e deve chegar na calçada às 15:22\n"
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "4.94\n"
            "15 min"
        ),

        # 2 – 10 min
        base + (
            "Chegada em 3:22 pm\n"
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "10 min"
        ),

        # 3 – 5 min
        base + (
            "Chegada em 3:22 pm\n"
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "5 min"
        ),

        # 4 – 3 min (começa alertas)
        base + (
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "3 min"
        ),

        # 5 – 2 min
        base + (
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "2 min"
        ),

        # 6 – 1 min
        base + (
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "1 min"
        ),

        # 7 – chegando
        base + (
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "Motorista chegou – aguardando na calçada\n"
            "CHEGANDO"
        ),

        # 8 – entregue
        base + (
            "GFA3F79\n"
            "Branco Fiat Uno\n"
            "BRENO\n"
            "Item foi entregue\n"
            "Obrigado por usar a Uber!"
        ),
    ]
    return etapas[min(etapa, len(etapas) - 1)]


def processar_ciclo(viagem: DadosViagem, texto: str,
                    painel_mostrado: bool, ultimo_minuto: int,
                    modo_debug: bool = False,
                    on_update=None):
    """
    Processa um ciclo de leitura (real ou simulado).
    Retorna (painel_mostrado, ultimo_minuto, deve_encerrar).
    """
    novo = extrair_dados(texto)

    # Mescla dados novos
    viagem.minutos = novo.minutos  if novo.minutos is not None else viagem.minutos
    viagem.status  = novo.status
    viagem.chegada = novo.chegada  or viagem.chegada
    if novo.placa:     viagem.placa     = novo.placa
    if novo.motorista: viagem.motorista = novo.motorista
    if novo.modelo:    viagem.modelo    = novo.modelo
    if novo.cor:       viagem.cor       = novo.cor
    if novo.origem:    viagem.origem    = novo.origem
    if novo.destino:   viagem.destino   = novo.destino
    if novo.modalidade: viagem.modalidade = novo.modalidade
    if novo.tipo_veiculo: viagem.tipo_veiculo = novo.tipo_veiculo

    if modo_debug:
        logger.debug(f"status={viagem.status} | minutos={viagem.minutos} | placa={viagem.placa}")
        
    if on_update:
        on_update(viagem)

    # Exibe painel ao detectar a placa pela primeira vez
    if viagem.placa and not painel_mostrado:
        exibir_painel(viagem)
        painel_mostrado = True
        notificar("Veículo Identificado 🚘",
                  f"Placa: {viagem.placa} | {viagem.modelo or ''} {viagem.cor or ''}")

    # ── ENTREGUE ─────────────────────────────────────────────────────────────
    if viagem.status == "entregue":
        logger.entregue(f"ITEM ENTREGUE! | {viagem.resumo()}")
        tocar_alerta(entregue=True)
        notificar("📦 Item Entregue!", viagem.resumo())
        exibir_historico(viagem)
        print(f"{Fore.GREEN}{Style.BRIGHT}✅ Entrega concluída. Rastreador encerrado.{Style.RESET_ALL}\n")
        return painel_mostrado, ultimo_minuto, True

    # ── CHEGANDO ─────────────────────────────────────────────────────────────
    elif viagem.status == "chegando":
        logger.urgente(f"MOTORISTA NO LOCAL! | {viagem.resumo()}")
        tocar_alerta(urgente=True)
        tocar_alerta(urgente=True)
        notificar("🚨 UBER CHEGOU!", viagem.resumo())
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✅ Motorista chegou. Aguardando entrega...{Style.RESET_ALL}")
        # Não encerra: aguarda a confirmação de entrega
        return painel_mostrado, ultimo_minuto, False

    # ── CANCELADO ────────────────────────────────────────────────────────────
    elif viagem.status == "cancelado":
        logger.urgente("Viagem CANCELADA detectada!")
        notificar("⚠ Viagem Cancelada", "Verifique o app da Uber.")
        exibir_historico(viagem)
        return painel_mostrado, ultimo_minuto, True

    # ── EM ROTA ──────────────────────────────────────────────────────────────
    elif viagem.status == "em_rota" and viagem.minutos is not None:
        m = viagem.minutos
        if m != ultimo_minuto:
            viagem.historico.append((datetime.now().strftime("%H:%M:%S"), m))
            if m <= CONFIG["MINUTOS_ALERTA"]:
                logger.urgente(f"{m} min restantes! | {viagem.resumo()}")
                tocar_alerta(urgente=False, minutos=m)
                notificar(f"⚡ CORRE! {m} min!", viagem.resumo())
            else:
                logger.ok(f"{m} min restantes | Chegada: {viagem.chegada or '--:--'}")
                if m in (10, 5):
                    notificar(f"⏱ {m} minutos", viagem.resumo())
            ultimo_minuto = m
        else:
            logger.ponto()
    else:
        logger.ponto()

    return painel_mostrado, ultimo_minuto, False


# ─── MODO DEBUG ───────────────────────────────────────────────────────────────
def rodar_debug(on_update=None):
    VEL = CONFIG["DEBUG_VELOCIDADE"]
    exibir_banner(modo_debug=True)
    print(f"{Fore.MAGENTA}  Simulação de viagem completa em andamento...")
    print(f"  Cada etapa dura {VEL}s (representa ~1 min de viagem real)")
    print(f"  Etapas: carregando → 15min → 10min → 5min → 3min → 2min → 1min → chegando → entregue\n{Style.RESET_ALL}")

    notificar("🛠 DEBUG Ativado", "Simulando viagem Uber completa...")
    logger.debug(f"Iniciado | velocidade={VEL}s por etapa\n")

    viagem          = DadosViagem()
    painel_mostrado = False
    ultimo_minuto   = -1

    for etapa in range(9):
        texto = gerar_pagina_simulada(etapa)
        painel_mostrado, ultimo_minuto, encerrar = processar_ciclo(
            viagem, texto, painel_mostrado, ultimo_minuto, modo_debug=True, on_update=on_update
        )
        if encerrar:
            break
        time.sleep(VEL)

    # Remove the input blockage since it's going via Web
    if not on_update:
        input("Pressione Enter para fechar...")


# ─── MODO REAL (Selenium) ─────────────────────────────────────────────────────
def rodar_real(link: str, on_update=None):
    if not TEM_SELENIUM:
        print(f"{Fore.RED}❌ Selenium não instalado. Execute: pip install selenium{Style.RESET_ALL}")
        sys.exit(1)

    logger.info(f"Link: {link}")
    logger.info("Iniciando navegador...")

    options = Options()
    options.binary_location = CONFIG["CAMINHO_NAVEGADOR"]
    options.add_experimental_option("detach", True)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        logger.urgente(f"Falha ao abrir navegador: {e}")
        print(f"\n{Fore.YELLOW}Dicas:{Style.RESET_ALL}")
        print("  1. Verifique CONFIG['CAMINHO_NAVEGADOR']")
        print("  2. Instale o ChromeDriver compatível com seu browser")
        sys.exit(1)

    def encerrar(sig, frame):
        print(f"\n{Fore.YELLOW}[!] Encerrado pelo usuário.{Style.RESET_ALL}")
        try: driver.quit()
        except Exception: pass
        sys.exit(0)

    signal.signal(signal.SIGINT, encerrar)

    driver.get(link)
    logger.info("Aguardando carregamento da página (5s)...")
    time.sleep(5)
    notificar("Rastreador Uber Iniciado", "Monitoramento ativo ✔")
    logger.ok("Monitoramento iniciado! Pressione Ctrl+C para encerrar.\n")

    viagem          = DadosViagem()
    painel_mostrado = False
    ultimo_minuto   = -1

    while True:
        try:
            texto_bruto = driver.find_element(By.TAG_NAME, "body").text
        except Exception as e:
            logger.alerta(f"Erro de leitura: {e}. Tentando em 3s...")
            time.sleep(3)
            continue

        painel_mostrado, ultimo_minuto, encerrar = processar_ciclo(
            viagem, texto_bruto, painel_mostrado, ultimo_minuto, on_update=on_update
        )

        if encerrar:
            try: driver.quit()
            except Exception: pass
            break

        intervalo = (CONFIG["INTERVALO_URGENTE"]
                     if viagem.minutos and viagem.minutos <= CONFIG["MINUTOS_ALERTA"]
                     else CONFIG["INTERVALO_NORMAL"])
        time.sleep(intervalo)

    if CONFIG["SALVAR_LOG"]:
        logger.info(f"Log salvo em: {CONFIG['ARQUIVO_LOG']}")
        
    if not on_update:
        input("Pressione Enter para fechar...")


# ─── EXTRAÇÃO DE LINK ─────────────────────────────────────────────────────────
def extrair_link(texto: str) -> Optional[str]:
    m = re.search(r'(https?://(?:trip|m)\.uber\.com/[^\s]+)', texto)
    return m.group(1) if m else None


# ─── ENTRADA PRINCIPAL ────────────────────────────────────────────────────────
def iniciar():
    exibir_banner()
    entrada = input(
        f"{Fore.WHITE}📩 Cole o link ou mensagem da Uber"
        f" {Fore.YELLOW}(ou digite DEBUG para simular){Fore.WHITE}:\n"
        f"{Fore.CYAN}> {Style.RESET_ALL}"
    ).strip()

    if entrada.upper() == "DEBUG":
        rodar_debug()
        return

    link = extrair_link(entrada)
    if not link:
        print(f"{Fore.RED}❌ Nenhum link da Uber encontrado.{Style.RESET_ALL}")
        print("   Esperado: https://trip.uber.com/...  ou  https://m.uber.com/...")
        print(f"   {Fore.YELLOW}Dica: Digite DEBUG para testar sem link.{Style.RESET_ALL}")
        sys.exit(1)

    exibir_banner()
    rodar_real(link)


if __name__ == "__main__":
    iniciar()
