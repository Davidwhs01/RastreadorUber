class TrackingCard(ctk.CTkFrame):
    def __init__(self, master, link, nome_sessao, is_debug=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.link = link
        self.is_debug = is_debug
        
        self.viagem = DadosViagem()
        if nome_sessao:
            self.viagem.nome_sessao = nome_sessao
            
        self.stop_event = threading.Event()
        self.ultimo_minuto = -1
        self.painel_mostrado = False
        self.max_minutos = 20
        self.alerta_1_tocado = False
        self.alerta_3_tocado = False
        self.ultimo_status = "aguardando"
        
        self._build_ui()
        
        if self.is_debug:
            threading.Thread(target=self._run_debug, daemon=True).start()
        else:
            threading.Thread(target=self._run_real, args=(self.link,), daemon=True).start()

    def _build_ui(self):
        # ── Status Banner ──
        self.status_banner = ctk.CTkFrame(
            self, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.status_banner.pack(fill="x", pady=(0, 10))

        banner_row = ctk.CTkFrame(self.status_banner, fg_color="transparent")
        banner_row.pack(fill="x", padx=18, pady=16)

        left = ctk.CTkFrame(banner_row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        self.st_icon = ctk.CTkLabel(left, text="⏳", font=("Segoe UI Emoji", 32))
        self.st_icon.pack(side="left", padx=(0, 14))

        txt_col = ctk.CTkFrame(left, fg_color="transparent")
        txt_col.pack(side="left")

        lbl_text = f"[{self.viagem.nome_sessao}] Aguardando..." if getattr(self.viagem, 'nome_sessao', None) else "Aguardando..."
        self.st_label = ctk.CTkLabel(
            txt_col, text=lbl_text,
            font=ctk.CTkFont(size=18, weight="bold"), text_color=C["text"], anchor="w"
        )
        self.st_label.pack(anchor="w")

        self.st_sub = ctk.CTkLabel(
            txt_col, text="Monitorando...",
            font=ctk.CTkFont(size=11), text_color=C["text2"], anchor="w"
        )
        self.st_sub.pack(anchor="w", pady=(2, 0))

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
            self, height=4, corner_radius=2,
            fg_color=C["card_border"], progress_color=C["green"]
        )
        self.pbar.pack(fill="x", pady=(0, 12))
        self.pbar.set(0)

        # ── Vehicle card ──
        self.veh_card = ctk.CTkFrame(
            self, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.veh_card.pack(fill="x", pady=(0, 10))

        veh_hdr = ctk.CTkFrame(self.veh_card, fg_color="transparent")
        veh_hdr.pack(fill="x", padx=18, pady=(14, 10))

        ctk.CTkLabel(
            veh_hdr, text="🚘  DADOS DO VEÍCULO",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["text3"]
        ).pack(side="left")

        self.live_dot = ctk.CTkLabel(
            veh_hdr, text="● AO VIVO",
            font=ctk.CTkFont(size=9, weight="bold"), text_color=C["green"]
        )
        self.live_dot.pack(side="right")

        data = ctk.CTkFrame(self.veh_card, fg_color="transparent")
        data.pack(fill="x", padx=18, pady=(0, 16))
        data.columnconfigure(0, weight=1)
        data.columnconfigure(1, weight=1)

        self.v_motor   = self._cell(data, "MOTORISTA",  "Identificando...", 0, 0, span=2, size=22, color=C["white"])
        self.v_placa   = self._cell(data, "PLACA",      "---",              1, 0, mono=True, size=18, color=C["amber"])
        self.v_chegada = self._cell(data, "PREVISÃO",   "--:--",            1, 1, color=C["green"], mono=True, size=18)
        
        sep1 = ctk.CTkFrame(data, height=2, fg_color=C["card_border"])
        sep1.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        self.v_modelo  = self._cell(data, "MODELO",     "---",              3, 0, size=13)
        self.v_cor     = self._cell(data, "COR",        "---",              3, 1, size=13)
        self.v_tipo    = self._cell(data, "VEÍCULO",    "---",              4, 0, size=13)
        self.v_modal   = self._cell(data, "ENTREGA",    "---",              4, 1, size=13)

        sep2 = ctk.CTkFrame(data, height=2, fg_color=C["card_border"])
        sep2.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)

        self.v_origem  = self._cell(data, "LOCAL DE COLETA (DE)",  "---",   6, 0, span=2, size=13, color=C["text2"])
        self.v_destino = self._cell(data, "DESTINO (PARA)",        "---",   7, 0, span=2, size=13, color=C["text2"])

        # ── Map Preview ──
        self.map_card = ctk.CTkFrame(
            self, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"], height=200
        )
        self.map_card.pack_propagate(False)

        self.map_label = ctk.CTkLabel(self.map_card, text="Carregando mapa...", text_color=C["text3"])
        self.map_label.pack(expand=True, fill="both")

        self.map_card.pack(fill="x", pady=(0, 10))

        # ── History card ──
        self.hist_card = ctk.CTkFrame(
            self, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )

        hist_hdr = ctk.CTkFrame(self.hist_card, fg_color="transparent")
        hist_hdr.pack(fill="x", padx=18, pady=(14, 6))

        ctk.CTkLabel(
            hist_hdr, text="📋  HISTÓRICO DA VIAGEM",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=C["text3"]
        ).pack(side="left")

        self.hist_text = ctk.CTkTextbox(
            self.hist_card, height=100,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=C["card_inner"], text_color=C["text2"],
            border_width=0, corner_radius=8
        )
        self.hist_text.pack(fill="x", padx=18, pady=(0, 14))
        self.hist_text.configure(state="disabled")

        # History packed explicitly later only when populated, to save space.

        # ── Stop ──
        self.stop_btn = ctk.CTkButton(
            self, text="■  FECHAR / PARAR", height=42, corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent", hover_color=C["rose_dim"],
            border_width=1, border_color=C["card_border"],
            text_color=C["text3"], command=self._stop
        )
        self.stop_btn.pack(fill="x", pady=(4, 24))

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

    def _update_ui(self):
        # Prevent updates if destroyed
        if not self.winfo_exists(): return
        
        v = self.viagem
        cfg = STATUS_MAP.get(v.status, STATUS_MAP["aguardando"])

        self.st_icon.configure(text=cfg["icon"])
        
        lbl_text = cfg["label"]
        if getattr(v, 'nome_sessao', None):
            lbl_text = f"[{v.nome_sessao}] {lbl_text}"
        self.st_label.configure(text=lbl_text, text_color=cfg["color"])

        subs = {
            "em_rota":    f"Faltam aproximadamente {v.minutos} minutos" if v.minutos else "Em rota...",
            "chegando":   "O motorista está no local de entrega",
            "entregue":   "A entrega foi concluída com sucesso! ✔",
            "cancelado":  "A viagem foi cancelada pelo motorista",
        }
        self.st_sub.configure(text=subs.get(v.status, "Monitorando o link da Uber..."))

        if v.minutos is not None:
            self.min_num.configure(text=str(v.minutos))
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

        if v.map_image:
            try:
                img = Image.open(io.BytesIO(v.map_image))
                img = img.convert("RGBA")
                width, height = img.size
                img = img.crop((0, 60, width, height))
                new_w = 380
                new_h = int((new_w / width) * img.height)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                self.map_card.configure(height=new_h + 2)
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=13, fill=255)
                img.putalpha(mask)

                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.map_label.configure(image=ctk_img, text="")
            except Exception:
                self.map_label.configure(text="Mapa indisponível", image="")

        if v.status in ("em_rota", "chegando"):
            self.live_dot.configure(text="● AO VIVO", text_color=C["green"])
        elif v.status == "entregue":
            self.live_dot.configure(text="✔ CONCLUÍDO", text_color=C["green"])
        elif v.status == "cancelado":
            self.live_dot.configure(text="✖ CANCELADO", text_color=C["rose"])

        if v.historico:
            if not self.hist_card.winfo_ismapped():
                self.hist_card.pack(fill="x", pady=(0, 10), in_=self, before=self.stop_btn)
            self.hist_text.configure(state="normal")
            self.hist_text.delete("1.0", "end")
            for i, (ts, mins) in enumerate(v.historico):
                dot = "🔴" if mins <= 3 else "🟡" if mins <= 5 else "🟢"
                line = f"  {dot}  {ts}   {mins} min restantes\n"
                self.hist_text.insert("end", line)
            self.hist_text.see("end")
            self.hist_text.configure(state="disabled")

    def _processar(self, texto: str, map_png: bytes = None):
        if self.stop_event.is_set(): return
        
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
                tocar_alerta(entregue=True, viagem=v)
                notificar("📦 Item Entregue!", v.resumo())
                self.ultimo_status = "entregue"
        elif v.status == "chegando":
            if getattr(self, "ultimo_status", None) != "chegando":
                if not getattr(self, "alerta_1_tocado", False):
                    self.alerta_1_tocado = True
                    tocar_alerta(urgente=True, viagem=v)
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
                if getattr(self, "ultimo_minuto", -1) != -1: 
                    # avoid firing alert instantly on load if it's already <3
                    pass
                if v.minutos <= 1 and not getattr(self, "alerta_1_tocado", False):
                    self.alerta_1_tocado = True
                    tocar_alerta(urgente=True, viagem=v)
                    notificar(f"⚡ DESCENDO! {v.minutos} min!", v.resumo())
                elif v.minutos <= 3 and not getattr(self, "alerta_3_tocado", False):
                    self.alerta_3_tocado = True
                    tocar_alerta(urgente=False, minutos=3, viagem=v)
                    notificar(f"⚡ PREPARE-SE! {v.minutos} min!", v.resumo())
                self.ultimo_minuto = v.minutos

    def _run_debug(self):
        log("DEBUG iniciado para sessaõ " + (self.viagem.nome_sessao or "unica"))
        notificar("🛠 Debug Ativado", "Simulando viagem Uber...")
        for etapa in range(9):
            if self.stop_event.is_set():
                break
            self._processar(gerar_pagina_simulada(etapa))
            self.after(0, self._update_ui)
            time.sleep(7.0)
        log("DEBUG finalizado")

    def _run_real(self, link: str):
        if not globals().get('TEM_SELENIUM', False):
            self.after(0, lambda: notificar("Erro", "Selenium não instalado: pip install selenium"))
            self.after(0, self._stop)
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

        driver = None
        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            log(f"Erro navegador: {e}")
            self.after(0, lambda: notificar("Erro", f"Navegador não encontrado: {e}"))
            self.after(0, self._stop)
            return

        try:
            driver.get(link)
            time.sleep(5)
            notificar("UberTrack", f"Monitoramento ativo para {self.viagem.nome_sessao or 'o link'} ✔")

            while not self.stop_event.is_set():
                try:
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
                if driver: driver.quit()
            except Exception:
                pass
        log("Rastreamento finalizado")

    def _stop(self):
        self.stop_event.set()
        self.destroy()


class RastreadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("UberTrack Multi — Delta Silk Print")
        self.geometry("540x840")
        self.minsize(440, 650)
        self.configure(fg_color=C["bg"])

        icon_candidates = [BASE_DIR / "icon.ico"]
        if getattr(sys, 'frozen', False):
            icon_candidates.insert(0, BASE_DIR / "_internal" / "icon.ico")
        self._icon_path = next((p for p in icon_candidates if p.exists()), BASE_DIR / "icon.ico")
        self.after(200, self._apply_icon)

        self._build_ui()
        threading.Thread(target=self._check_update_bg, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_icon(self):
        if not self._icon_path.exists():
            return
        try:
            if sys.platform.startswith("win"):
                self.iconbitmap(str(self._icon_path))
            else:
                from PIL import Image, ImageTk
                ico_img = Image.open(str(self._icon_path)).convert("RGBA")
                self._icon_photo = ImageTk.PhotoImage(ico_img)
                self.iconphoto(True, self._icon_photo)
        except Exception as e:
            print(f"Erro ao setar icone: {e}")

    def _build_ui(self):
        self.main = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C["card_border"],
            scrollbar_button_hover_color=C["text3"],
        )
        self.main.pack(fill="both", expand=True, padx=10, pady=(0, 0))

        hdr = ctk.CTkFrame(self.main, fg_color="transparent")
        hdr.pack(fill="x", pady=(20, 0))

        ctk.CTkLabel(
            hdr, text="🚗  UberTrack",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C["text"]
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            hdr, text="Monitoramento de Entregas em Tempo Real",
            font=ctk.CTkFont(size=11), text_color=C["text3"]
        ).pack()

        accent_line = ctk.CTkFrame(hdr, fg_color=C["green"], height=2, corner_radius=1)
        accent_line.pack(pady=(10, 0), ipadx=50)

        self.update_frame = ctk.CTkFrame(
            self.main, fg_color=C["green_dim"],
            corner_radius=10, border_width=1, border_color=C["green"]
        )
        self.update_label = ctk.CTkLabel(
            self.update_frame, text="", font=ctk.CTkFont(size=11),
            text_color=C["text"]
        )
        self.update_label.pack(side="left", padx=12, pady=8)
        self.update_btn = ctk.CTkButton(
            self.update_frame, text="Atualizar", width=80, height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=C["green"], hover_color=C["green_glow"],
            text_color="#000", command=self._apply_update_action
        )
        self.update_btn.pack(side="right", padx=12, pady=8)

        self.input_card = ctk.CTkFrame(
            self.main, fg_color=C["card"], corner_radius=14,
            border_width=1, border_color=C["card_border"]
        )
        self.input_card.pack(fill="x", pady=(24, 0))

        card_hdr = ctk.CTkFrame(self.input_card, fg_color="transparent")
        card_hdr.pack(fill="x", padx=18, pady=(18, 0))

        ctk.CTkLabel(
            card_hdr, text="📍",
            font=("Segoe UI Emoji", 18)
        ).pack(side="left")

        ctk.CTkLabel(
            card_hdr, text="  Adicionar Viagem",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=C["text"]
        ).pack(side="left")

        ctk.CTkLabel(
            self.input_card,
            text="Cole o link de rastreamento da Uber abaixo",
            font=ctk.CTkFont(size=11), text_color=C["text3"], anchor="w"
        ).pack(fill="x", padx=18, pady=(8, 6))

        self.link_entry = ctk.CTkEntry(
            self.input_card, height=46,
            placeholder_text="https://trip.uber.com/...",
            font=ctk.CTkFont(family="Consolas", size=13), corner_radius=10,
            fg_color=C["card_inner"], border_color=C["card_border"],
            text_color=C["text"], placeholder_text_color=C["text3"]
        )
        self.link_entry.pack(fill="x", padx=18, pady=(0, 10))
        self.link_entry.bind("<Return>", lambda e: self.nome_entry.focus_set())

        self.nome_entry = ctk.CTkEntry(
            self.input_card, height=40,
            placeholder_text="Identificação ex: DTF (Opcional)",
            font=ctk.CTkFont(size=13), corner_radius=10,
            fg_color=C["card_inner"], border_color=C["card_border"],
            text_color=C["text"], placeholder_text_color=C["text3"]
        )
        self.nome_entry.pack(fill="x", padx=18, pady=(0, 10))
        self.nome_entry.bind("<Return>", lambda e: self._start())

        self.err_label = ctk.CTkLabel(
            self.input_card, text="", font=ctk.CTkFont(size=10),
            text_color=C["rose"], anchor="w"
        )

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

        footer = ctk.CTkFrame(self, fg_color=C["bg2"], height=36, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text=f"Criado por Delta Silk Print  ·  v{APP_VERSION} MULTI",
            font=ctk.CTkFont(size=10), text_color=C["text3"]
        ).pack(expand=True)

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
        nome = self.nome_entry.get().strip()
        
        # Cria e injeta o novo TrackingCard logo abaixo do form
        card = TrackingCard(self.main, link=link, nome_sessao=nome, is_debug=(txt.upper() == "DEBUG"))
        card.pack(fill="x", pady=(24, 0), before=None) # Vai empilhando embaixo
        
        # Tenta rolar para baixo pra mostrar o card (pequeno delay pra render)
        self.after(200, lambda: self.main._parent_canvas.yview_moveto(1.0))

        # Limpa os campos
        self.link_entry.delete(0, "end")
        self.nome_entry.delete(0, "end")

    def _start_debug(self):
        self.link_entry.delete(0, "end")
        self.link_entry.insert(0, "DEBUG")
        self._start()

    def _err(self, msg):
        self.err_label.configure(text=f"⚠  {msg}")
        self.err_label.pack(fill="x", padx=18, pady=(0, 6))

    def _err_hide(self):
        self.err_label.pack_forget()

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
                               before=self.input_card if self.input_card.winfo_ismapped() else None)

    def _apply_update_action(self):
        url = getattr(self, '_dl_url', '')
        if not url: return
        self.update_btn.configure(text="Baixando...", state="disabled")
        threading.Thread(target=self._do_update, args=(url,), daemon=True).start()

    def _do_update(self, url):
        if apply_update(url):
            self.after(0, lambda: self.update_label.configure(text="✅ Atualizado com sucesso!", text_color=C["text"]))
            self.after(0, lambda: self.update_btn.configure(text="Reiniciar", state="normal", command=self._restart_app))
        else:
            import webbrowser
            webbrowser.open(url)
            self.after(0, lambda: self.update_label.configure(text="⬇ Baixando pelo navegador..."))
            self.after(0, lambda: self.update_btn.configure(text="Tentar", state="normal"))

    def _restart_app(self):
        self._on_close()
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv[1:])

    def _on_close(self):
        # Avisa todos os cards filhos para pararem as threads
        for child in self.main.winfo_children():
            if isinstance(child, TrackingCard):
                child.stop_event.set()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    app = RastreadorApp()
    app.mainloop()
