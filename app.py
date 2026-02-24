"""
╔══════════════════════════════════════════════════════════════╗
║           UBERTRACK BY DELTA — App Desktop                    ║
║           Criado por Delta Silk Print                         ║
╚══════════════════════════════════════════════════════════════╝

App desktop com interface gráfica nativa premium.
Compila em um único .exe sem terminal, sem browser.

Dependências: pip install customtkinter selenium plyer Pillow
"""

import customtkinter as ctk
import threading
import time
import os
import re
import sys
import json
import pyttsx3
import tempfile
import zipfile
import shutil
import ctypes
import io
import queue
from PIL import Image, ImageTk, ImageDraw
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

# ─── PATHS ────────────────────────────────────────────────────────────────────
def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
VERSION_FILE = BASE_DIR / "version.json"
LOG_FILE = BASE_DIR / "uber_tracker.log"

APP_VERSION = "3.1.3"
APP_TITLE = "UberTrack by Delta"

# ─── Windows: definir AppUserModelId para notificações corretas ───────────────
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "DeltaSilkPrint.RastreadorUber.3.0"
    )
except Exception:
    pass

# ─── VERSION ──────────────────────────────────────────────────────────────────
def read_version() -> dict:
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": APP_VERSION, "update_url": "", "changelog": ""}

# ─── SELENIUM ─────────────────────────────────────────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    TEM_SELENIUM = True
except Exception as e:
    import traceback
    try:
        with open(BASE_DIR / "uber_tracker.log", "a", encoding="utf-8") as _f:
            _f.write(f"\\n--- ERRO SELENIUM ---\\n{traceback.format_exc()}\\n")
    except:
        pass
    TEM_SELENIUM = False

# (plyer removido — usa PowerShell nativo para notificações com nome correto)


# ═══════════════════════════════════════════════════════════════════════════════
# ─── DADOS DA VIAGEM ─────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class DadosViagem:
    placa: Optional[str] = None
    motorista: Optional[str] = None
    modelo: Optional[str] = None
    cor: Optional[str] = None
    chegada: Optional[str] = None
    minutos: Optional[int] = None
    origem: Optional[str] = None
    destino: Optional[str] = None
    tipo_veiculo: Optional[str] = None
    modalidade: Optional[str] = None
    map_image: Optional[bytes] = None
    status: str = "aguardando"
    historico: list = field(default_factory=list)

    def resumo(self) -> str:
        p = []
        if self.modalidade: p.append(self.modalidade)
        if self.tipo_veiculo: p.append(self.tipo_veiculo)
        if self.placa:     p.append(self.placa)
        if self.motorista: p.append(self.motorista)
        if self.modelo:    p.append(self.modelo)
        if self.cor:       p.append(self.cor)
        return " • ".join(p) if p else "Aguardando dados..."


# ═══════════════════════════════════════════════════════════════════════════════
# ─── EXTRAÇÃO DE DADOS ────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
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

    # PLACA
    for padrao in [r'\b([A-Z]{3}\d[A-Z]\d{2})\b', r'\b([A-Z]{3}[-]?\d{4})\b']:
        m = re.search(padrao, texto)
        if m:
            dados.placa = m.group(1).replace("-", "")
            break

    # HORÁRIO
    m = re.search(r'\b(\d{1,2}:\d{2})\s*(PM|AM)?\b', texto)
    if m:
        dados.chegada = f"{m.group(1)} {m.group(2) or ''}".strip()

    # MINUTOS
    m = re.search(r'\b(\d{1,3})\s*MIN(?:UTO[S]?)?', texto)
    if m:
        dados.minutos = int(m.group(1))

    # STATUS
    if any(k in texto for k in ("ITEM FOI ENTREGUE", "FOI ENTREGUE", "ENTREGA CONCLU",
                                  "PEDIDO ENTREGUE", "DELIVERY COMPLETE", "DELIVERED",
                                  "ENTREGUE COM SUCESSO")):
        dados.status = "entregue"
    elif any(k in texto for k in ("CANCELAD", "CANCELED")):
        dados.status = "cancelado"
    elif any(k in texto for k in ("CHEGANDO", "ARRIVING", "CHEGOU", "ARRIVED",
                                    "MOTORISTA CHEGOU", "DRIVER HAS ARRIVED", "AQUI")):
        if dados.minutos is not None and dados.minutos > 3:
            dados.status = "em_rota"
        else:
            dados.status = "chegando"
    elif dados.minutos is not None:
        dados.status = "em_rota"
    else:
        dados.status = "aguardando"

    # COR
    for cor in ["BRANCO", "PRETO", "PRATA", "CINZA", "VERMELHO", "AZUL",
                "VERDE", "AMARELO", "MARROM", "BEGE", "LARANJA", "ROXO",
                "WHITE", "BLACK", "SILVER", "GRAY", "RED", "BLUE"]:
        if cor in texto:
            dados.cor = cor.capitalize()
            break

    # MODELO
    for modelo in ["FIAT UNO", "FIAT MOBI", "FIAT ARGO", "FIAT CRONOS",
                   "HB20", "ONIX", "GOL", "POLO", "VOYAGE", "SANDERO",
                   "LOGAN", "KWID", "CORSA", "PRISMA", "COBALT", "TRACKER",
                   "SPIN", "CIVIC", "FIT", "CITY", "HR-V", "ETIOS",
                   "YARIS", "COROLLA", "HILUX", "COMPASS", "RENEGADE",
                   "TORO", "KICKS", "MARCH", "VERSA", "ECOSPORT", "KA"]:
        if modelo in texto:
            dados.modelo = modelo.title()
            break

    # MOTORISTA
    ignorar = {"MIN", "PM", "AM", "UBER", "VIAGEM", "CHEGADA", "ITEM", "PARA",
               "COM", "NAO", "SIM", "RUA", "AV", "AVE", "STATUS", "BRANCO",
               "PRETO", "PRATA", "CINZA", "DEBUG", "ENTREGUE", "ENTREGA"}
    for linha in texto_bruto.split("\n"):
        linha = linha.strip()
        if (3 <= len(linha) <= 20 and linha.isupper()
                and linha not in ignorar
                and not re.search(r'\d', linha)
                and not any(k in linha for k in ["RUA", "AV.", "MIN", "PM", "AM"])):
            dados.motorista = linha.title()
            break

    return dados


def extrair_link(texto: str) -> Optional[str]:
    m = re.search(r'(https?://(?:trip|m)\.uber\.com/[^\s]+)', texto)
    return m.group(1) if m else None


# ═══════════════════════════════════════════════════════════════════════════════
# ─── SIMULAÇÃO DEBUG ──────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
def gerar_pagina_simulada(etapa: int) -> str:
    base = "Uber\nDe Moda Saza\nPara Rua Galeão, 439 – Sapopemba\nInformações da viagem\n"
    etapas = [
        base + "Carregando informações da viagem...",
        base + "Chegada em 3:22 pm\nO item está a caminho\nGFA3F79\nBranco Fiat Uno\nBRENO\n4.94\n15 min",
        base + "Chegada em 3:22 pm\nGFA3F79\nBranco Fiat Uno\nBRENO\n10 min",
        base + "Chegada em 3:22 pm\nGFA3F79\nBranco Fiat Uno\nBRENO\n5 min",
        base + "GFA3F79\nBranco Fiat Uno\nBRENO\n3 min",
        base + "GFA3F79\nBranco Fiat Uno\nBRENO\n2 min",
        base + "GFA3F79\nBranco Fiat Uno\nBRENO\n1 min",
        base + "GFA3F79\nBranco Fiat Uno\nBRENO\nMotorista chegou\nCHEGANDO",
        base + "GFA3F79\nBranco Fiat Uno\nBRENO\nItem foi entregue\nObrigado por usar a Uber!",
    ]
    return etapas[min(etapa, len(etapas) - 1)]


# ═══════════════════════════════════════════════════════════════════════════════
# ─── ALERTAS E NOTIFICAÇÕES ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

# Fila de TTS para evitar bugs do pyttsx3 rodando em threads avulsas
tts_queue = queue.Queue()

def _tts_worker():
    import pythoncom
    pythoncom.CoInitialize()  # Requisito para rodar SAPI5 (voz do Windows) em thread separada
    try:
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

def tocar_alerta(urgente=False, entregue=False, minutos=None):
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


def notificar(titulo: str, mensagem: str):
    """Notificação in-app: toast no canto da tela com branding correto."""
    def _show():
        try:
            toast = ctk.CTkToplevel()
            toast.title("")
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(fg_color="#111113")
            toast.attributes("-alpha", 0.95)

            # Tamanho e posição (canto inferior direito)
            w, h = 360, 110
            screen_w = toast.winfo_screenwidth()
            screen_h = toast.winfo_screenheight()
            x = screen_w - w - 16
            y = screen_h - h - 80
            toast.geometry(f"{w}x{h}+{x}+{y}")

            # Borda visual
            border = ctk.CTkFrame(toast, fg_color="#10b981", corner_radius=12)
            border.pack(fill="both", expand=True, padx=1, pady=1)

            inner = ctk.CTkFrame(border, fg_color="#111113", corner_radius=11)
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            # Header: nome do app
            hdr = ctk.CTkFrame(inner, fg_color="transparent")
            hdr.pack(fill="x", padx=12, pady=(10, 0))

            ctk.CTkLabel(
                hdr, text="🚗  UberTrack by Delta",
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color="#5a5a66"
            ).pack(side="left")

            # Fechar
            close_btn = ctk.CTkLabel(
                hdr, text="✕", font=ctk.CTkFont(size=11),
                text_color="#5a5a66", cursor="hand2"
            )
            close_btn.pack(side="right")
            close_btn.bind("<Button-1>", lambda e: toast.destroy())

            # Título
            ctk.CTkLabel(
                inner, text=titulo,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#f0f0f0", anchor="w"
            ).pack(fill="x", padx=12, pady=(6, 0))

            # Mensagem
            ctk.CTkLabel(
                inner, text=mensagem[:80],
                font=ctk.CTkFont(size=11),
                text_color="#b0b0b8", anchor="w"
            ).pack(fill="x", padx=12, pady=(2, 10))

            # Auto-fechar em 6 segundos
            toast.after(6000, lambda: toast.destroy() if toast.winfo_exists() else None)

        except Exception:
            pass

    # Precisa rodar na thread principal do Tk
    try:
        import tkinter as tk
        root = tk._default_root
        if root:
            root.after(0, _show)
    except Exception:
        pass


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# ─── AUTO-UPDATE VIA GITHUB RELEASES ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
def check_for_update() -> dict:
    """
    Checa GitHub Releases para updates.
    Espera version.json com: {"version": "3.1.0", "github_repo": "User/Repo"}
    """
    info = read_version()
    result = {**info, "update_available": False, "latest_version": info.get("version", APP_VERSION)}
    repo = info.get("github_repo", "").strip()
    if not repo:
        return result
    try:
        import urllib.request
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "RastreadorUber/3.0",
            "Accept": "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            release = json.loads(resp.read().decode("utf-8"))

        # tag_name pode ser "v3.2.0" ou "3.2.0"
        tag = release.get("tag_name", "0.0.0").lstrip("v")
        rv = tuple(int(x) for x in tag.split("."))
        lv = tuple(int(x) for x in info.get("version", "0").split("."))

        if rv > lv:
            result["update_available"] = True
            result["latest_version"] = tag
            result["changelog"] = release.get("body", "")

            # Procura o primeiro asset .zip
            for asset in release.get("assets", []):
                if asset.get("name", "").endswith(".zip"):
                    result["download_url"] = asset.get("browser_download_url", "")
                    break
    except Exception:
        pass
    return result


def apply_update(download_url: str) -> bool:
    """Baixa o .zip do GitHub Release e substitui os arquivos."""
    try:
        import urllib.request
        tmp = Path(tempfile.mkdtemp(prefix="uber_update_"))
        zp = tmp / "update.zip"
        req = urllib.request.Request(download_url, headers={"User-Agent": "RastreadorUber/3.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(zp, "wb") as f:
                f.write(resp.read())
        ext = tmp / "extracted"
        with zipfile.ZipFile(zp, "r") as z:
            z.extractall(ext)
        # Se o zip contém uma pasta raiz, entra nela
        items = list(ext.iterdir())
        source = items[0] if len(items) == 1 and items[0].is_dir() else ext
        for item in source.iterdir():
            dest = BASE_DIR / item.name
            if item.is_dir():
                if dest.exists():
                    try:
                        shutil.rmtree(dest)
                    except PermissionError:
                        dest.rename(dest.with_name(dest.name + ".old"))
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                if dest.exists():
                    try:
                        dest.unlink()
                    except PermissionError:
                        try:
                            # Tenta renomear o arquivo problemático (comum para .exe rodando)
                            dest.rename(dest.with_name(dest.name + ".old"))
                        except Exception:
                            pass
                shutil.copy2(item, dest)
        shutil.rmtree(tmp, ignore_errors=True)
        return True
    except Exception as e:
        import traceback
        try:
            with open(BASE_DIR / "uber_tracker.log", "a", encoding="utf-8") as _f:
                _f.write(f"\\n--- ERRO AUTO UPDATE ---\\n{traceback.format_exc()}\\n")
        except:
            pass
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ─── CORES & THEME ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
C = {
    "bg":           "#050505",
    "bg2":          "#0c0c0e",
    "card":         "#111113",
    "card_border":  "#1e1e22",
    "card_inner":   "#0a0a0c",
    "text":         "#f0f0f0",
    "text2":        "#b0b0b8",
    "text3":        "#5a5a66",
    "green":        "#10b981",
    "green_dim":    "#065f46",
    "green_glow":   "#0d9668",
    "sky":          "#38bdf8",
    "sky_dim":      "#075985",
    "amber":        "#fbbf24",
    "amber_dim":    "#78350f",
    "rose":         "#fb7185",
    "rose_dim":     "#881337",
    "violet":       "#a78bfa",
    "white":        "#ffffff",
}

STATUS_MAP = {
    "aguardando": {"icon": "⏳", "label": "Aguardando...",        "color": C["text3"], "accent": C["card_border"]},
    "em_rota":    {"icon": "🚗", "label": "A Caminho",           "color": C["sky"],   "accent": C["sky_dim"]},
    "chegando":   {"icon": "🔔", "label": "Motorista Chegou!",   "color": C["amber"], "accent": C["amber_dim"]},
    "entregue":   {"icon": "📦", "label": "Entrega Concluída",   "color": C["green"], "accent": C["green_dim"]},
    "cancelado":  {"icon": "❌", "label": "Cancelada",            "color": C["rose"],  "accent": C["rose_dim"]},
}


# ═══════════════════════════════════════════════════════════════════════════════
# ─── APP ──────────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
class RastreadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("UberTrack — Delta Silk Print")
        
        try:
            self.iconbitmap(BASE_DIR / "icon.ico")
        except Exception:
            pass

        self.geometry("500x780")
        self.minsize(440, 650)
        self.configure(fg_color=C["bg"])

        icon_path = BASE_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
            # Fallback: tentar via PIL para garantir
            try:
                import warnings
                from PIL import Image, ImageTk
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    ico_img = Image.open(str(icon_path))
                    ico_img = ico_img.resize((32, 32), Image.LANCZOS)
                self._icon_photo = ImageTk.PhotoImage(ico_img)
                self.iconphoto(True, self._icon_photo)
            except Exception:
                pass

        # State
        self.viagem = DadosViagem()
        self.is_tracking = False
        self.stop_event = threading.Event()
        self.ultimo_minuto = -1
        self.painel_mostrado = False
        self.max_minutos = 20  # Referência para barra de progresso

        self._build_ui()
        threading.Thread(target=self._check_update_bg, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ════ MAIN SCROLL ════
        self.main = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["card_border"],
            scrollbar_button_hover_color=C["text3"],
        )
        self.main.pack(fill="both", expand=True, padx=20, pady=(0, 0))

        # ════ HEADER ════
        hdr = ctk.CTkFrame(self.main, fg_color="transparent")
        hdr.pack(fill="x", pady=(20, 0))

        # Título principal
        ctk.CTkLabel(
            hdr, text="🚗  UberTrack",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C["text"]
        ).pack(pady=(0, 4))

        # Subtítulo
        ctk.CTkLabel(
            hdr, text="Monitoramento de Entregas em Tempo Real",
            font=ctk.CTkFont(size=11), text_color=C["text3"]
        ).pack()

        # Linha accent
        accent_line = ctk.CTkFrame(hdr, fg_color=C["green"], height=2, corner_radius=1)
        accent_line.pack(pady=(10, 0), ipadx=50)

        # ════ UPDATE BANNER (hidden) ════
        self.update_frame = ctk.CTkFrame(
            self.main, fg_color=C["green_dim"],
            corner_radius=10, border_width=1, border_color=C["green"]
        )
        self.update_label = ctk.CTkLabel(
            self.update_frame, text="", font=ctk.CTkFont(size=11),
            text_color=C["green"]
        )
        self.update_label.pack(side="left", padx=12, pady=8)
        self.update_btn = ctk.CTkButton(
            self.update_frame, text="Atualizar", width=80, height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=C["green"], hover_color=C["green_glow"],
            text_color="#000", command=self._apply_update_action
        )
        self.update_btn.pack(side="right", padx=12, pady=8)

        # ════ INPUT CARD ════
        self.input_card = ctk.CTkFrame(
            self.main, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.input_card.pack(fill="x", pady=(24, 0))

        # Card header
        card_hdr = ctk.CTkFrame(self.input_card, fg_color="transparent")
        card_hdr.pack(fill="x", padx=18, pady=(18, 0))

        ctk.CTkLabel(
            card_hdr, text="📍",
            font=("Segoe UI Emoji", 18)
        ).pack(side="left")

        ctk.CTkLabel(
            card_hdr, text="  Iniciar Rastreamento",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=C["text"]
        ).pack(side="left")

        # Hint
        ctk.CTkLabel(
            self.input_card,
            text="Cole abaixo o link de rastreamento da Uber",
            font=ctk.CTkFont(size=11), text_color=C["text3"], anchor="w"
        ).pack(fill="x", padx=18, pady=(8, 6))

        # Entry
        self.link_entry = ctk.CTkEntry(
            self.input_card, height=46,
            placeholder_text="https://trip.uber.com/...",
            font=ctk.CTkFont(family="Consolas", size=13), corner_radius=10,
            fg_color=C["card_inner"], border_color=C["card_border"],
            text_color=C["text"], placeholder_text_color=C["text3"]
        )
        self.link_entry.pack(fill="x", padx=18, pady=(0, 10))
        self.link_entry.bind("<Return>", lambda e: self._start())

        # Error
        self.err_label = ctk.CTkLabel(
            self.input_card, text="", font=ctk.CTkFont(size=10),
            text_color=C["rose"], anchor="w"
        )

        # Buttons row
        btn_row = ctk.CTkFrame(self.input_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 18))

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶  RASTREAR", height=46, corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["green"], hover_color=C["green_glow"],
            text_color="#000", command=self._start
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.debug_btn = ctk.CTkButton(
            btn_row, text="🛠  DEBUG", height=46, width=110, corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent", hover_color=C["card_border"],
            border_width=1, border_color=C["card_border"],
            text_color=C["text2"], command=self._start_debug
        )
        self.debug_btn.pack(side="right")

        # ════ TRACKING VIEW (hidden initially) ════
        self.track_view = ctk.CTkFrame(self.main, fg_color="transparent")

        # ── Status Banner ──
        self.status_banner = ctk.CTkFrame(
            self.track_view, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.status_banner.pack(fill="x", pady=(0, 10))

        banner_row = ctk.CTkFrame(self.status_banner, fg_color="transparent")
        banner_row.pack(fill="x", padx=18, pady=16)

        # Left: icon + text
        left = ctk.CTkFrame(banner_row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self.st_icon = ctk.CTkLabel(left, text="⏳", font=("Segoe UI Emoji", 32))
        self.st_icon.pack(side="left", padx=(0, 14))

        txt_col = ctk.CTkFrame(left, fg_color="transparent")
        txt_col.pack(side="left")

        self.st_label = ctk.CTkLabel(
            txt_col, text="Aguardando...",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=C["text"], anchor="w"
        )
        self.st_label.pack(anchor="w")

        self.st_sub = ctk.CTkLabel(
            txt_col, text="Monitorando...",
            font=ctk.CTkFont(size=11), text_color=C["text2"], anchor="w"
        )
        self.st_sub.pack(anchor="w", pady=(2, 0))

        # Right: minutes circle
        self.min_circle = ctk.CTkFrame(
            banner_row, width=86, height=86,
            fg_color=C["card_inner"], corner_radius=43,
            border_width=2, border_color=C["green"]
        )
        self.min_circle.pack(side="right")
        self.min_circle.pack_propagate(False)

        self.min_num = ctk.CTkLabel(
            self.min_circle, text="--",
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color=C["green"]
        )
        self.min_num.pack(expand=True)

        self.min_unit = ctk.CTkLabel(
            self.min_circle, text="min",
            font=ctk.CTkFont(size=9, weight="bold"), text_color=C["text3"]
        )
        self.min_unit.place(relx=0.5, rely=0.82, anchor="center")

        # ── Progress bar ──
        self.pbar = ctk.CTkProgressBar(
            self.track_view, height=4, corner_radius=2,
            fg_color=C["card_border"], progress_color=C["green"]
        )
        self.pbar.pack(fill="x", pady=(0, 12))
        self.pbar.set(0)

        # ── Vehicle card ──
        self.veh_card = ctk.CTkFrame(
            self.track_view, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.veh_card.pack(fill="x", pady=(0, 10))

        # Vehicle header
        veh_hdr = ctk.CTkFrame(self.veh_card, fg_color="transparent")
        veh_hdr.pack(fill="x", padx=18, pady=(14, 10))

        ctk.CTkLabel(
            veh_hdr, text="🚘  DADOS DO VEÍCULO",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["text3"]
        ).pack(side="left")

        # Live badge
        self.live_dot = ctk.CTkLabel(
            veh_hdr, text="● AO VIVO",
            font=ctk.CTkFont(size=9, weight="bold"), text_color=C["green"]
        )
        self.live_dot.pack(side="right")

        # Data rows - NEW STRUCTURE

        data = ctk.CTkFrame(self.veh_card, fg_color="transparent")
        data.pack(fill="x", padx=18, pady=(0, 16))
        data.columnconfigure(0, weight=1)
        data.columnconfigure(1, weight=1)

        # ── Group 1: Principais ──
        self.v_motor   = self._cell(data, "MOTORISTA",  "Identificando...", 0, 0, span=2, size=22, color=C["white"])
        self.v_placa   = self._cell(data, "PLACA",      "---",              1, 0, mono=True, size=18, color=C["amber"])
        self.v_chegada = self._cell(data, "PREVISÃO",   "--:--",            1, 1, color=C["green"], mono=True, size=18)
        
        # Spacer
        sep1 = ctk.CTkFrame(data, height=2, fg_color=C["card_border"])
        sep1.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        # ── Group 2: Veículo ──
        self.v_modelo  = self._cell(data, "MODELO",     "---",              3, 0, size=13)
        self.v_cor     = self._cell(data, "COR",        "---",              3, 1, size=13)
        self.v_tipo    = self._cell(data, "VEÍCULO",    "---",              4, 0, size=13)
        self.v_modal   = self._cell(data, "ENTREGA",    "---",              4, 1, size=13)

        # Spacer 
        sep2 = ctk.CTkFrame(data, height=2, fg_color=C["card_border"])
        sep2.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)

        # ── Group 3: Rota ──
        self.v_origem  = self._cell(data, "LOCAL DE COLETA (DE)",  "---",   6, 0, span=2, size=13, color=C["text2"])
        self.v_destino = self._cell(data, "DESTINO (PARA)",        "---",   7, 0, span=2, size=13, color=C["text2"])

        # ── Map Preview ──
        self.map_card = ctk.CTkFrame(
            self.track_view, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"], height=200
        )
        self.map_card.pack_propagate(False)

        self.map_label = ctk.CTkLabel(self.map_card, text="Carregando mapa...", text_color=C["text3"])
        self.map_label.pack(expand=True, fill="both")

        self.map_card.pack(fill="x", pady=(0, 10))

        # ── History card ──
        self.hist_card = ctk.CTkFrame(
            self.track_view, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )

        hist_hdr = ctk.CTkFrame(self.hist_card, fg_color="transparent")
        hist_hdr.pack(fill="x", padx=18, pady=(14, 6))

        ctk.CTkLabel(
            hist_hdr, text="📋  HISTÓRICO DA VIAGEM",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["text3"]
        ).pack(side="left")

        self.hist_text = ctk.CTkTextbox(
            self.hist_card, height=130,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=C["card_inner"], text_color=C["text2"],
            border_width=0, corner_radius=8
        )
        self.hist_text.pack(fill="x", padx=18, pady=(0, 14))
        self.hist_text.configure(state="disabled")
        
        self.hist_card.pack(fill="x", pady=(0, 10))

        # ── Stop ──
        self.stop_btn = ctk.CTkButton(
            self.track_view, text="■  PARAR RASTREAMENTO", height=42, corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent", hover_color=C["rose_dim"],
            border_width=1, border_color=C["card_border"],
            text_color=C["text3"], command=self._stop
        )
        self.stop_btn.pack(fill="x", pady=(4, 10))

        # ════ FOOTER ════
        footer = ctk.CTkFrame(self, fg_color=C["bg2"], height=36, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text=f"Criado por Delta Silk Print  ·  v{APP_VERSION}",
            font=ctk.CTkFont(size=10), text_color=C["text3"]
        ).pack(expand=True)

    # ─── CELL HELPER ──────────────────────────────────────────────────────────
    def _cell(self, parent, label, initial, row, col, span=1, color=None, mono=False, size=14):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, columnspan=span, sticky="w", pady=6, padx=(0, 12))

        ctk.CTkLabel(
            f, text=label,
            font=ctk.CTkFont(size=9, weight="bold"), text_color=C["text3"]
        ).pack(anchor="w")

        v = ctk.CTkLabel(
            f, text=initial,
            font=ctk.CTkFont(
                family="Consolas" if mono else "Segoe UI",
                size=size, weight="bold"
            ),
            text_color=color or C["text"]
        )
        v.pack(anchor="w", pady=(2, 0))
        return v

    # ─── SHOW/HIDE ────────────────────────────────────────────────────────────
    def _show_track(self):
        self.input_card.pack_forget()
        self.track_view.pack(fill="x", pady=(24, 0))

    def _show_input(self):
        self.track_view.pack_forget()
        self.hist_card.pack_forget()
        self.input_card.pack(fill="x", pady=(24, 0))

    # ─── UPDATE UI (thread-safe) ──────────────────────────────────────────────
    def _update_ui(self):
        v = self.viagem
        cfg = STATUS_MAP.get(v.status, STATUS_MAP["aguardando"])

        self.st_icon.configure(text=cfg["icon"])
        self.st_label.configure(text=cfg["label"], text_color=cfg["color"])

        # Status subtitle
        subs = {
            "em_rota":    f"Faltam aproximadamente {v.minutos} minutos" if v.minutos else "Em rota...",
            "chegando":   "O motorista está no local de entrega",
            "entregue":   "A entrega foi concluída com sucesso! ✔",
            "cancelado":  "A viagem foi cancelada pelo motorista",
        }
        self.st_sub.configure(text=subs.get(v.status, "Monitorando o link da Uber..."))

        # Minutes circle
        if v.minutos is not None:
            self.min_num.configure(text=str(v.minutos))
            # Atualiza max_minutos com o primeiro valor grande detectado
            if v.minutos > self.max_minutos:
                self.max_minutos = v.minutos
            mc = C["rose"] if v.minutos <= 2 else C["amber"] if v.minutos <= 5 else C["sky"] if v.minutos <= 10 else C["green"]
            self.min_num.configure(text_color=mc)
            self.min_circle.configure(border_color=mc)
            self.pbar.configure(progress_color=mc)
            progresso = max(0.03, min(1.0, (self.max_minutos - v.minutos) / max(self.max_minutos, 1)))
            self.pbar.set(progresso)
        else:
            self.min_num.configure(text="--", text_color=C["text3"])
            self.min_circle.configure(border_color=C["card_border"])
            self.pbar.set(0)

        # Vehicle
        self.v_placa.configure(text=v.placa or "---")
        self.v_chegada.configure(text=v.chegada or "--:--")
        self.v_motor.configure(text=v.motorista or "Identificando...")
        self.v_modelo.configure(text=v.modelo or "---")
        self.v_cor.configure(text=v.cor or "---")
        self.v_tipo.configure(text=v.tipo_veiculo or "Carro")
        self.v_modal.configure(text=v.modalidade or "---")

        origem = (v.origem[:45] + '...') if v.origem and len(v.origem) > 45 else (v.origem or "---")
        destino = (v.destino[:45] + '...') if v.destino and len(v.destino) > 45 else (v.destino or "---")
        self.v_origem.configure(text=origem)
        self.v_destino.configure(text=destino)

        # Map Preview
        if v.map_image:
            try:
                img = Image.open(io.BytesIO(v.map_image))
                img = img.convert("RGBA")
                
                # O Chrome Headless tem tamanho 400x750. 
                # Vamos remover apenas a barrinha inútil do topo, preservando todo o fundo
                # onde ficam os dados originais e a foto do motorista no site.
                width, height = img.size
                
                # left, upper, right, lower
                # Corta apenas 60px de cima
                img = img.crop((0, 60, width, height))
                
                # Resize para caber bonitinho no painel
                new_w = 380
                new_h = int((new_w / width) * img.height)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                
                # Ajusta a altura ideal dinamicamente com base no resize + pad
                self.map_card.configure(height=new_h + 2)
                
                # Apply rounded corners manually via PIL for a smooth look
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=13, fill=255)
                img.putalpha(mask)

                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.map_label.configure(image=ctk_img, text="")
            except Exception as e:
                self.map_label.configure(text="Mapa indisponível", image="")
        
        # Live dot pulse
        if v.status in ("em_rota", "chegando"):
            self.live_dot.configure(text="● AO VIVO", text_color=C["green"])
        elif v.status == "entregue":
            self.live_dot.configure(text="✔ CONCLUÍDO", text_color=C["green"])
        elif v.status == "cancelado":
            self.live_dot.configure(text="✖ CANCELADO", text_color=C["rose"])

        # History
        if v.historico:
            if not self.hist_card.winfo_ismapped():
                self.hist_card.pack(fill="x", pady=(0, 10), in_=self.track_view, before=self.stop_btn)
            self.hist_text.configure(state="normal")
            self.hist_text.delete("1.0", "end")
            for i, (ts, mins) in enumerate(v.historico):
                dot = "🔴" if mins <= 3 else "🟡" if mins <= 5 else "🟢"
                line = f"  {dot}  {ts}   {mins} min restantes\n"
                self.hist_text.insert("end", line)
            self.hist_text.see("end")
            self.hist_text.configure(state="disabled")

    # ─── COMMANDS ─────────────────────────────────────────────────────────────
    def _start(self):
        txt = self.link_entry.get().strip()
        if not txt:
            self._err("Cole um link da Uber ou clique em DEBUG")
            return
        link = extrair_link(txt)
        if not link and txt.upper() != "DEBUG":
            self._err("Link inválido. Esperado: https://trip.uber.com/...")
            return
        self._err_hide()
        self.viagem = DadosViagem()
        self.ultimo_minuto = -1
        self.painel_mostrado = False
        self.stop_event.clear()
        self.is_tracking = True
        self._show_track()

        if txt.upper() == "DEBUG":
            threading.Thread(target=self._run_debug, daemon=True).start()
        else:
            threading.Thread(target=self._run_real, args=(link,), daemon=True).start()

    def _start_debug(self):
        self.link_entry.delete(0, "end")
        self.link_entry.insert(0, "DEBUG")
        self._start()

    def _stop(self):
        self.stop_event.set()
        self.is_tracking = False
        self.viagem = DadosViagem()
        self.max_minutos = 20
        self._show_input()

    def _err(self, msg):
        self.err_label.configure(text=f"⚠  {msg}")
        self.err_label.pack(fill="x", padx=18, pady=(0, 6))

    def _err_hide(self):
        self.err_label.pack_forget()

    # ─── TRACKING THREADS ────────────────────────────────────────────────────
    def _run_debug(self):
        log("DEBUG iniciado")
        notificar("🛠 Debug Ativado", "Simulando viagem Uber completa...")
        for etapa in range(9):
            if self.stop_event.is_set():
                break
            self._processar(gerar_pagina_simulada(etapa))
            self.after(0, self._update_ui)
            time.sleep(7.0)
        log("DEBUG finalizado")

    def _run_real(self, link: str):
        if not TEM_SELENIUM:
            self.after(0, lambda: self._err("Selenium não instalado: pip install selenium"))
            self.after(0, self._show_input)
            return

        log(f"Rastreamento: {link}")
        options = Options()
        for bp in [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]:
            if os.path.exists(bp):
                options.binary_location = bp
                break
        options.add_argument("--headless=new")
        options.add_argument("--window-size=400,750")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            log(f"Erro navegador: {e}")
            self.after(0, lambda: self._err(f"Navegador não encontrado: {e}"))
            self.after(0, self._show_input)
            return

        try:
            driver.get(link)
            time.sleep(5)
            notificar("UberTrack", "Monitoramento ativo ✔")

            while not self.stop_event.is_set():
                try:
                    # Tenta remover o banner de cookies e overlays pelo javascript antes do screenshot
                    script_remover_modais = """
                    var banners = document.querySelectorAll('div[data-testid="cookie-banner"], div[role="dialog"]');
                    banners.forEach(b => b.remove());
                    """
                    driver.execute_script(script_remover_modais)
                    
                    texto = driver.find_element(By.TAG_NAME, "body").text
                    png = driver.get_screenshot_as_png()
                except Exception:
                    time.sleep(3)
                    continue
                self._processar(texto, png)
                self.after(0, self._update_ui)
                if self.viagem.status in ("entregue", "cancelado"):
                    break
                wait = 5 if (self.viagem.minutos and self.viagem.minutos <= 3) else 15
                for _ in range(wait):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        log("Rastreamento finalizado")

    # ─── PROCESSAR ────────────────────────────────────────────────────────────
    def _processar(self, texto: str, map_png: bytes = None):
        novo = extrair_dados(texto)
        v = self.viagem
        if map_png: v.map_image = map_png
        v.minutos = novo.minutos if novo.minutos is not None else v.minutos
        v.status = novo.status
        v.chegada = novo.chegada or v.chegada
        if novo.placa: v.placa = novo.placa
        if novo.motorista: v.motorista = novo.motorista
        if novo.modelo: v.modelo = novo.modelo
        if novo.cor: v.cor = novo.cor
        if novo.origem: v.origem = novo.origem
        if novo.destino: v.destino = novo.destino
        if novo.modalidade: v.modalidade = novo.modalidade
        if novo.tipo_veiculo: v.tipo_veiculo = novo.tipo_veiculo

        if v.placa and not self.painel_mostrado:
            self.painel_mostrado = True
            notificar("🚘 Veículo Identificado", f"{v.placa} • {v.modelo or ''} {v.cor or ''}")

        if v.status == "entregue":
            if getattr(self, "ultimo_status", None) != "entregue":
                tocar_alerta(entregue=True)
                notificar("📦 Item Entregue!", v.resumo())
                self.ultimo_status = "entregue"
        elif v.status == "chegando":
            if getattr(self, "ultimo_status", None) != "chegando":
                tocar_alerta(urgente=True)
                notificar("🚨 UBER CHEGOU!", v.resumo())
                self.ultimo_status = "chegando"
        elif v.status == "cancelado":
            if getattr(self, "ultimo_status", None) != "cancelado":
                notificar("⚠ Viagem Cancelada", "Verifique o app da Uber.")
                self.ultimo_status = "cancelado"
        elif v.status == "em_rota" and v.minutos is not None:
            self.ultimo_status = "em_rota"
            if v.minutos != self.ultimo_minuto:
                v.historico.append((datetime.now().strftime("%H:%M:%S"), v.minutos))
                if v.minutos <= 3:
                    tocar_alerta(urgente=False, minutos=v.minutos)
                    notificar(f"⚡ CORRE! {v.minutos} min!", v.resumo())
                elif v.minutos in (10, 5):
                    notificar(f"⏱ {v.minutos} minutos", v.resumo())
                self.ultimo_minuto = v.minutos

    # ─── UPDATE ───────────────────────────────────────────────────────────────
    def _check_update_bg(self):
        try:
            info = check_for_update()
            if info.get("update_available"):
                self.after(0, lambda: self._show_update(info))
        except Exception:
            pass

    def _show_update(self, info):
        self.update_label.configure(text=f"🆕 v{info.get('latest_version', '')} disponível!")
        self._dl_url = info.get("download_url", "")
        self.update_frame.pack(fill="x", pady=(16, 0), in_=self.main,
                               before=self.input_card if self.input_card.winfo_ismapped()
                               else self.track_view)

    def _apply_update_action(self):
        url = getattr(self, '_dl_url', '')
        if not url: return
        self.update_btn.configure(text="...", state="disabled")
        threading.Thread(target=self._do_update, args=(url,), daemon=True).start()

    def _do_update(self, url):
        if apply_update(url):
            self.after(0, lambda: self.update_label.configure(text="✅ Atualizado! Reinicie."))
        else:
            self.after(0, lambda: self.update_label.configure(text="❌ Falha"))
            self.after(0, lambda: self.update_btn.configure(text="Tentar", state="normal"))

    # ─── CLOSE ────────────────────────────────────────────────────────────────
    def _on_close(self):
        self.stop_event.set()
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    app = RastreadorApp()
    app.mainloop()
