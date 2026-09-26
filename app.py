import os
import sys
import json
import threading
import time
import re
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog

# Auto-verificação de dependências
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk, ImageFilter
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    ctk = None
    PYGAME_AVAILABLE = False

from theme_manager import ThemeManager, CONFIG_PATH
from wallpaper_manager import WallpaperManager
from iptv_manager import IPTVManager, EmbeddedVLCPlayer, VLC_AVAILABLE
from create_icon import generate_gamer_icon

class VideoMusicApp:
    def __init__(self):
        self.theme_mgr = ThemeManager()
        self.wallpaper_mgr = WallpaperManager()
        self.iptv_mgr = IPTVManager()
        
        # Carregar configurações
        self.config = self.load_config()
        self.current_theme_name = self.config.get("theme", "Cyberpunk 2077 (Gamer Neon)")
        self.theme = self.theme_mgr.get_theme(self.current_theme_name)
        
        # Configurar Pygame Mixer para reprodução de áudio
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Aviso no mixer: {e}")

        # Configurar Janela Principal Gamer
        if ctk:
            ctk.set_appearance_mode("Dark")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("⚡ VIDEOMUSIC // GAMER HUD - Player, Downloader & Live TV")
        self.root.geometry("1140x740")
        self.root.minsize(940, 640)
        
        # Gerar e Aplicar Ícone Gamer Estiloso
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        try:
            generate_gamer_icon(icon_path)
        except Exception:
            pass
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Aplicar opacidade da janela do Windows (Desktop Alpha)
        alpha = self.config.get("window_alpha", 1.0)
        try:
            self.root.attributes("-alpha", max(0.5, min(1.0, float(alpha))))
        except Exception:
            pass

        # Estado da reprodução de música local
        self.playlist = []
        self.current_track_idx = -1
        self.is_playing = False
        self.is_paused = False

        # Estado do Player IPTV / Live
        self.vlc_player = None
        self.current_iptv_stream = None
        self.current_iptv_name = "Nenhum canal ativo"
        self.iptv_volume = 80
        self.iptv_is_live = False

        # Estado do Downloader
        self.last_downloaded_folder = None

        # Configurar Wallpaper com Escurecimento e Desfoque (Blur)
        saved_wp = self.config.get("wallpaper_path")
        saved_dim = self.config.get("wallpaper_dim", 0.35)
        saved_blur = self.config.get("wallpaper_blur", 0)
        if saved_wp and os.path.exists(saved_wp):
            self.wallpaper_mgr.set_wallpaper(saved_wp, saved_dim, saved_blur)

        self.setup_ui()
        self.apply_theme(self.current_theme_name, initial=True)

        # Vincular redimensionamento para wallpaper responsivo
        self.root.bind("<Configure>", self.on_window_resize)
        self.last_resize_time = 0

    def load_config(self):
        default_cfg = {
            "theme": "Cyberpunk 2077 (Gamer Neon)",
            "wallpaper_path": None,
            "wallpaper_dim": 0.35,
            "wallpaper_blur": 0,
            "transparency_mode": "transparent",  # "transparent", "glass", "solid"
            "window_alpha": 1.0,
            "download_dir": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
            "create_playlist_folder": True,
            "last_iptv_url": "https://ntv1.akamaized.net/hls/live/2014075/NASA-NTV1-HLS/master.m3u8",
            "iptv_engine": "auto"
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_cfg.update(data)
                    return default_cfg
            except Exception:
                pass
        return default_cfg

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")

    # ==========================
    # SISTEMA DE CORES & TRANSPARÊNCIA GAMER
    # ==========================
    def get_card_color(self):
        mode = self.config.get("transparency_mode", "transparent")
        if mode == "transparent":
            return "transparent"
        elif mode == "glass":
            return self.theme_mgr._adjust_brightness(self.theme["card_color"], 0.70)
        else:
            return self.theme["card_color"]

    def get_card_hover_color(self):
        mode = self.config.get("transparency_mode", "transparent")
        if mode == "transparent":
            return self.theme_mgr._adjust_brightness(self.theme["card_color"], 0.45)
        elif mode == "glass":
            return self.theme_mgr._adjust_brightness(self.theme["card_hover"], 0.80)
        else:
            return self.theme["card_hover"]

    def get_sidebar_color(self):
        mode = self.config.get("transparency_mode", "transparent")
        if mode == "transparent":
            return self.theme_mgr._adjust_brightness(self.theme["sidebar_color"], 0.55)
        elif mode == "glass":
            return self.theme_mgr._adjust_brightness(self.theme["sidebar_color"], 0.75)
        else:
            return self.theme["sidebar_color"]

    def _sanitize_folder_name(self, name):
        """Remove caracteres inválidos do Windows para nomes de pastas."""
        clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
        return clean or "Playlist_Download"

    # ==========================
    # INTERFACE PRINCIPAL GAMER HUD
    # ==========================
    def setup_ui(self):
        # 1. Camada de Fundo (Wallpaper ou Cor do Tema)
        self.bg_label = tk.Label(self.root, bg=self.theme["bg_color"])
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # 2. Container Geral
        self.app_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent") if ctk else tk.Frame(self.root, bg=self.theme["bg_color"])
        self.app_frame.pack(fill="both", expand=True)

        # 3. Topbar Gamer HUD (Estilo Gamer Futurista)
        self.create_gamer_topbar()

        # 4. Container Principal Dividido (Sidebar + Área de Conteúdo)
        self.main_container = ctk.CTkFrame(self.app_frame, corner_radius=0, fg_color="transparent") if ctk else tk.Frame(self.app_frame, bg=self.theme["bg_color"])
        self.main_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # 5. Sidebar Gamer
        self.create_sidebar()

        # 6. Área de Conteúdo
        self.content_area = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color="transparent") if ctk else tk.Frame(self.main_container, bg=self.theme["card_color"])
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Telas / Abas
        self.pages = {}
        self.pages["downloader"] = self.create_downloader_page()
        self.pages["iptv"] = self.create_iptv_page()
        self.pages["player"] = self.create_player_page()
        self.pages["themes"] = self.create_themes_page()
        self.pages["wallpaper"] = self.create_wallpaper_page()
        self.pages["installer"] = self.create_installer_page()

        # Abrir na tela Downloader inicialmente
        self.show_page("downloader")

    def create_gamer_topbar(self):
        """Barra de status superior estilo Gamer HUD com indicadores RGB."""
        self.topbar = ctk.CTkFrame(self.app_frame, height=44, corner_radius=0, fg_color=self.get_sidebar_color()) if ctk else tk.Frame(self.app_frame, height=44, bg=self.theme["sidebar_color"])
        self.topbar.pack(fill="x", side="top", pady=(0, 6))
        self.topbar.pack_propagate(False)

        # Logotipo Gamer
        top_left = ctk.CTkFrame(self.topbar, fg_color="transparent") if ctk else tk.Frame(self.topbar, bg=self.theme["sidebar_color"])
        top_left.pack(side="left", padx=14)

        self.lbl_gamer_title = ctk.CTkLabel(
            top_left,
            text="⚡ VIDEOMUSIC // GAMER HUD",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(top_left, text="⚡ VIDEOMUSIC // GAMER HUD", font=("Arial", 12, "bold"), fg=self.theme["accent_color"], bg=self.theme["sidebar_color"])
        self.lbl_gamer_title.pack(side="left")

        lbl_version = ctk.CTkLabel(
            top_left,
            text="[v2.5 CYBER EDITION]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(top_left, text="[v2.5]", font=("Arial", 8), fg=self.theme["subtext_color"], bg=self.theme["sidebar_color"])
        lbl_version.pack(side="left", padx=(8, 0))

        # Indicadores Gamer à Direita (Status HUD)
        top_right = ctk.CTkFrame(self.topbar, fg_color="transparent") if ctk else tk.Frame(self.topbar, bg=self.theme["sidebar_color"])
        top_right.pack(side="right", padx=14)

        self.hud_badge_fps = ctk.CTkLabel(
            top_right,
            text="● LOW LATENCY 144Hz",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#10b981"
        ) if ctk else tk.Label(top_right, text="● 144Hz", fg="#10b981", bg=self.theme["sidebar_color"])
        self.hud_badge_fps.pack(side="left", padx=8)

        self.hud_badge_audio = ctk.CTkLabel(
            top_right,
            text="🎧 320KBPS HI-FI",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(top_right, text="🎧 320KBPS", fg=self.theme["accent_color"], bg=self.theme["sidebar_color"])
        self.hud_badge_audio.pack(side="left", padx=8)

        self.hud_badge_rgb = ctk.CTkLabel(
            top_right,
            text="🌐 RGB SYNC: ON",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(top_right, text="RGB SYNC", fg=self.theme["subtext_color"], bg=self.theme["sidebar_color"])
        self.hud_badge_rgb.pack(side="left", padx=8)

        # Linha RGB Neon Separadora
        self.rgb_line = ctk.CTkFrame(self.app_frame, height=2, fg_color=self.theme["accent_color"], corner_radius=0) if ctk else tk.Frame(self.app_frame, height=2, bg=self.theme["accent_color"])
        self.rgb_line.pack(fill="x", side="top", pady=(0, 8))

    def create_sidebar(self):
        sidebar_bg = self.get_sidebar_color()
        self.sidebar = ctk.CTkFrame(
            self.main_container, 
            width=230, 
            corner_radius=12, 
            fg_color=sidebar_bg,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(self.main_container, width=230, bg=self.theme["sidebar_color"])
        
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_propagate(False)

        # Cabeçalho da Sidebar
        side_head = ctk.CTkFrame(self.sidebar, fg_color="transparent") if ctk else tk.Frame(self.sidebar, bg=self.theme["sidebar_color"])
        side_head.pack(fill="x", pady=(14, 10), padx=12)

        self.logo_label = ctk.CTkLabel(
            side_head, 
            text="🎮 CONTROLES", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme["accent_color"],
            anchor="w"
        ) if ctk else tk.Label(side_head, text="🎮 CONTROLES", font=("Arial", 12, "bold"), fg=self.theme["accent_color"], bg=self.theme["sidebar_color"])
        self.logo_label.pack(anchor="w")

        # Botões de Navegação Gamer HUD
        nav_buttons = [
            ("⚡ 01 // BAIXAR PLAYLIST", "downloader"),
            ("📺 02 // TV & LIVE IPTV", "iptv"),
            ("🎧 03 // PLAYER DE ÁUDIO", "player"),
            ("🎨 04 // TEMAS RGB CHROMA", "themes"),
            ("🖼️ 05 // PAPEL DE PAREDE", "wallpaper"),
            ("🚀 06 // ATALHOS / .EXE", "installer"),
        ]

        self.nav_widgets = {}
        for text, key in nav_buttons:
            if ctk:
                btn = ctk.CTkButton(
                    self.sidebar,
                    text=text,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    height=40,
                    anchor="w",
                    corner_radius=8,
                    fg_color="transparent",
                    text_color=self.theme["text_color"],
                    hover_color=self.get_card_hover_color(),
                    command=lambda k=key: self.show_page(k)
                )
            else:
                btn = tk.Button(
                    self.sidebar,
                    text=text,
                    font=("Arial", 10, "bold"),
                    anchor="w",
                    relief="flat",
                    bg=self.theme["sidebar_color"],
                    fg=self.theme["text_color"],
                    command=lambda k=key: self.show_page(k)
                )
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_widgets[key] = btn

        # Rodapé da Sidebar (Gamer Status Card)
        footer = ctk.CTkFrame(
            self.sidebar, 
            fg_color=self.get_card_color(), 
            corner_radius=8,
            border_width=1,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(self.sidebar, bg=self.theme["sidebar_color"])
        footer.pack(side="bottom", fill="x", pady=12, padx=10)

        self.theme_badge = ctk.CTkLabel(
            footer,
            text=f"CHROMA: {self.current_theme_name[:15]}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme["subtext_color"],
            anchor="w"
        ) if ctk else tk.Label(footer, text="CHROMA", font=("Arial", 8), fg=self.theme["subtext_color"], bg=self.theme["sidebar_color"])
        self.theme_badge.pack(anchor="w", padx=8, pady=(8, 2))

        self.mode_badge = ctk.CTkLabel(
            footer,
            text="FUNDO: TRANSPARENTE [OK]",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.theme["accent_color"],
            anchor="w"
        ) if ctk else tk.Label(footer, text="TRANSPARENTE", font=("Arial", 8), fg=self.theme["accent_color"], bg=self.theme["sidebar_color"])
        self.mode_badge.pack(anchor="w", padx=8, pady=(0, 8))

    def show_page(self, page_name):
        for name, frame in self.pages.items():
            frame.grid_forget()
            if ctk and name in self.nav_widgets:
                self.nav_widgets[name].configure(
                    fg_color="transparent", 
                    text_color=self.theme["text_color"]
                )

        if page_name in self.pages:
            self.pages[page_name].grid(row=0, column=0, sticky="nsew")
            if ctk and page_name in self.nav_widgets:
                self.nav_widgets[page_name].configure(
                    fg_color=self.theme["accent_color"],
                    text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff"
                )

    # ==========================
    # ABA 1: DOWNLOADER GAMER (COM CRIAÇÃO DE PASTA DE PLAYLIST AUTOMÁTICA)
    # ==========================
    def create_downloader_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])
        
        # Cabeçalho Gamer
        head_box = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        head_box.pack(fill="x", pady=(2, 10))

        title = ctk.CTkLabel(
            head_box, 
            text="⚡ BAIXAR MÚSICAS & PLAYLISTS", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(head_box, text="BAIXAR PLAYLISTS & MÚSICAS", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(side="left")

        tag_dl = ctk.CTkLabel(
            head_box,
            text="[ ULTRA YT-DLP ENGINE ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(head_box, text="[ ULTRA YT-DLP ]", fg=self.theme["accent_color"], bg=self.theme["card_color"])
        tag_dl.pack(side="right", padx=6)

        # Card 1: URL Input
        url_frame = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        url_frame.pack(fill="x", pady=6)

        lbl_url = ctk.CTkLabel(
            url_frame, 
            text="Cole o Link (Vídeo, Música ou Playlist Completa do YouTube, SoundCloud, etc.):", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(url_frame, text="Link do Vídeo ou Playlist:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_url.pack(anchor="w", padx=14, pady=(10, 4))

        self.entry_url = ctk.CTkEntry(
            url_frame, 
            placeholder_text="https://www.youtube.com/playlist?list=... ou link de música", 
            height=38, 
            font=ctk.CTkFont(size=13)
        ) if ctk else tk.Entry(url_frame, font=("Arial", 12))
        self.entry_url.pack(fill="x", padx=14, pady=(0, 12))

        # Card 2: Configuração de Pastas & Criação Automática de Pasta para Playlist
        folder_card = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        folder_card.pack(fill="x", pady=6)

        lbl_folder_title = ctk.CTkLabel(
            folder_card, 
            text="📁 Organização de Pastas de Playlists:", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(folder_card, text="Organização de Pastas:", fg=self.theme["accent_color"], bg=self.theme["card_hover"])
        lbl_folder_title.pack(anchor="w", padx=14, pady=(10, 4))

        # Checkbox para criar subpasta automática
        self.create_folder_var = tk.BooleanVar(value=self.config.get("create_playlist_folder", True))
        self.chk_playlist_folder = ctk.CTkCheckBox(
            folder_card,
            text="Criar subpasta automaticamente com o nome da Playlist (ex: 'As Melhores Músicas')",
            font=ctk.CTkFont(size=12, weight="bold"),
            variable=self.create_folder_var,
            onvalue=True,
            offvalue=False,
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            command=self.on_playlist_checkbox_toggle
        ) if ctk else tk.Checkbutton(folder_card, text="Criar pasta para playlist", variable=self.create_folder_var)
        self.chk_playlist_folder.pack(anchor="w", padx=14, pady=(2, 6))

        # Campo para nome de pasta personalizado (opcional)
        cust_row = ctk.CTkFrame(folder_card, fg_color="transparent") if ctk else tk.Frame(folder_card, bg=self.theme["card_hover"])
        cust_row.pack(fill="x", padx=14, pady=(0, 12))

        lbl_cust_name = ctk.CTkLabel(
            cust_row, 
            text="Nome personalizado da pasta (opcional):", 
            font=ctk.CTkFont(size=11), 
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(cust_row, text="Nome da pasta (opcional):", fg=self.theme["subtext_color"])
        lbl_cust_name.pack(side="left", padx=(0, 10))

        self.entry_custom_folder = ctk.CTkEntry(
            cust_row, 
            placeholder_text="Deixe em branco para usar o nome da Playlist automaticamente ou digite ex: 'As Melhores Músicas'", 
            height=32, 
            font=ctk.CTkFont(size=12)
        ) if ctk else tk.Entry(cust_row)
        self.entry_custom_folder.pack(side="left", fill="x", expand=True)

        # Card 3: Formato e Diretório Raiz
        opts_frame = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        opts_frame.pack(fill="x", pady=6)

        lbl_fmt = ctk.CTkLabel(opts_frame, text="Formato de Download:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(opts_frame, text="Formato:", fg=self.theme["text_color"])
        lbl_fmt.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self.format_var = tk.StringVar(value="MP3 (Áudio - 320kbps)")
        formats = [
            "MP3 (Áudio - 320kbps)", 
            "MP4 (Vídeo 1080p / Melhor Qualidade)", 
            "MP4 (720p Leve)", 
            "WAV (Áudio Sem Compressão Hi-Res)"
        ]
        if ctk:
            self.combo_format = ctk.CTkComboBox(opts_frame, values=formats, variable=self.format_var, width=280)
            self.combo_format.grid(row=0, column=1, padx=12, pady=10, sticky="w")
        else:
            self.combo_format = tk.OptionMenu(opts_frame, self.format_var, *formats)
            self.combo_format.grid(row=0, column=1, padx=12, pady=10, sticky="w")

        lbl_dest = ctk.CTkLabel(opts_frame, text="Salvar em:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(opts_frame, text="Salvar em:", fg=self.theme["text_color"])
        lbl_dest.grid(row=1, column=0, padx=14, pady=10, sticky="w")

        self.lbl_path = ctk.CTkLabel(opts_frame, text=self.config.get("download_dir"), text_color=self.theme["subtext_color"]) if ctk else tk.Label(opts_frame, text=self.config.get("download_dir"), fg=self.theme["subtext_color"])
        self.lbl_path.grid(row=1, column=1, padx=12, pady=10, sticky="w")

        btn_choose_dir = ctk.CTkButton(
            opts_frame, 
            text="Escolher Pasta", 
            width=120, 
            command=self.choose_download_dir, 
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"]
        ) if ctk else tk.Button(opts_frame, text="Escolher Pasta", command=self.choose_download_dir)
        btn_choose_dir.grid(row=1, column=2, padx=12, pady=10)

        # Botão Iniciar Download Gamer
        self.btn_download = ctk.CTkButton(
            page, 
            text="⚡ BAIXAR AGORA (MÚSICA OU PLAYLIST COMPLETA)", 
            height=46, 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.start_download
        ) if ctk else tk.Button(page, text="⚡ BAIXAR AGORA", font=("Arial", 13, "bold"), bg=self.theme["accent_color"], command=self.start_download)
        self.btn_download.pack(fill="x", pady=12)

        # Barra de Progresso e Status
        status_box = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=8,
            border_width=1,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        status_box.pack(fill="x", pady=4)

        self.lbl_status = ctk.CTkLabel(
            status_box, 
            text="Pronto para baixar. Insira o link e clique no botão acima.", 
            text_color=self.theme["subtext_color"],
            font=ctk.CTkFont(size=12)
        ) if ctk else tk.Label(status_box, text="Pronto para baixar.", fg=self.theme["subtext_color"])
        self.lbl_status.pack(pady=(8, 4), padx=12)

        if ctk:
            self.progress_bar = ctk.CTkProgressBar(status_box, progress_color=self.theme["accent_color"])
            self.progress_bar.set(0.0)
            self.progress_bar.pack(fill="x", padx=14, pady=(2, 8))

        # Botão de Abrir Pasta Baixada (habilitado após download)
        self.btn_open_download_folder = ctk.CTkButton(
            status_box,
            text="📂 Abrir Pasta da Playlist no Windows Explorer",
            height=32,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.open_last_downloaded_folder
        ) if ctk else tk.Button(status_box, text="Abrir Pasta Baixada", command=self.open_last_downloaded_folder)
        # Inicialmente não empacotado

        return page

    def on_playlist_checkbox_toggle(self):
        val = self.create_folder_var.get()
        self.config["create_playlist_folder"] = val
        self.save_config()

    def choose_download_dir(self):
        folder = filedialog.askdirectory(initialdir=self.config.get("download_dir"))
        if folder:
            self.config["download_dir"] = folder
            self.save_config()
            self.lbl_path.configure(text=folder)

    def start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Por favor, insira o link do vídeo, música ou playlist.")
            return

        fmt = self.format_var.get()
        out_dir = self.config.get("download_dir", os.path.expanduser("~"))
        create_folder = self.create_folder_var.get()
        custom_folder_name = self.entry_custom_folder.get().strip()

        self.btn_download.configure(state="disabled")
        self.lbl_status.configure(text="🔍 Analisando link e detectando playlist...")
        if ctk:
            self.progress_bar.set(0.05)

        threading.Thread(
            target=self._download_worker, 
            args=(url, fmt, out_dir, create_folder, custom_folder_name), 
            daemon=True
        ).start()

    def _download_worker(self, url, fmt, out_dir, create_folder, custom_folder_name):
        try:
            import yt_dlp
        except ImportError:
            self.root.after(0, lambda: messagebox.showerror("Erro", "A biblioteca 'yt-dlp' não está instalada."))
            self.root.after(0, lambda: self.btn_download.configure(state="normal"))
            return

        # 1. Analisar se é playlist e determinar pasta de destino
        playlist_title = None
        is_playlist = False
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': 'in_playlist'}) as ydl:
                info_check = ydl.extract_info(url, download=False)
                if info_check:
                    if 'entries' in info_check or info_check.get('_type') == 'playlist':
                        is_playlist = True
                        playlist_title = info_check.get('title')
        except Exception as e:
            print(f"Aviso na verificação de playlist: {e}")

        # Se for playlist ou o usuário digitou nome personalizado, cria a subpasta
        target_dir = out_dir
        if custom_folder_name:
            clean_name = self._sanitize_folder_name(custom_folder_name)
            target_dir = os.path.join(out_dir, clean_name)
            os.makedirs(target_dir, exist_ok=True)
        elif create_folder and playlist_title:
            clean_name = self._sanitize_folder_name(playlist_title)
            target_dir = os.path.join(out_dir, clean_name)
            os.makedirs(target_dir, exist_ok=True)
        elif create_folder and ("list=" in url.lower() or "playlist" in url.lower()):
            clean_name = "Playlist_Download"
            target_dir = os.path.join(out_dir, clean_name)
            os.makedirs(target_dir, exist_ok=True)

        self.last_downloaded_folder = target_dir

        self.root.after(0, lambda: self.lbl_status.configure(
            text=f"📁 Pasta: {os.path.basename(target_dir)} | Iniciando download..."
        ))

        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = downloaded / total
                    speed = d.get('speed', 0) or 0
                    speed_mb = speed / (1024 * 1024)

                    # Info de índice de playlist se disponível
                    info_dict = d.get('info_dict', {})
                    p_idx = info_dict.get('playlist_index')
                    p_count = info_dict.get('n_entries')

                    if p_idx and p_count:
                        status_text = f"Faixa [{p_idx}/{p_count}] Baixando: {pct*100:.1f}% ({speed_mb:.2f} MB/s)"
                    else:
                        status_text = f"Baixando: {pct*100:.1f}% ({speed_mb:.2f} MB/s)"

                    self.root.after(0, lambda: self.lbl_status.configure(text=status_text))
                    if ctk:
                        self.root.after(0, lambda: self.progress_bar.set(pct))
                except Exception:
                    pass
            elif d['status'] == 'finished':
                self.root.after(0, lambda: self.lbl_status.configure(text="Convertendo formato final e salvando tags..."))

        # Template de saída
        if is_playlist or custom_folder_name:
            outtmpl = os.path.join(target_dir, '%(playlist_index&{:02d} - |)s%(title)s.%(ext)s')
        else:
            outtmpl = os.path.join(target_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,  # Continua baixando se uma música falhar na playlist
        }

        if "MP3" in fmt:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            })
        elif "WAV" in fmt:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }]
            })
        elif "720p" in fmt:
            ydl_opts.update({
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]'
            })
        else:
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best'
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                item_title = info.get('title', 'Mídia') if info else 'Playlist'
                self.root.after(0, lambda: self._on_download_success(item_title, target_dir))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_download_error(err_msg))

    def _on_download_success(self, title, target_dir):
        folder_name = os.path.basename(target_dir)
        self.lbl_status.configure(text=f"✅ Concluído! Salvo na pasta: {folder_name}")
        if ctk:
            self.progress_bar.set(1.0)
        self.btn_download.configure(state="normal")

        # Exibir botão para abrir pasta
        self.btn_open_download_folder.pack(pady=(4, 8))

        messagebox.showinfo(
            "Download Concluído!", 
            f"Download finalizado com sucesso!\n\n📁 Pasta criada/usada:\n{target_dir}\n\nItem: {title}"
        )

    def _on_download_error(self, err_msg):
        self.lbl_status.configure(text="❌ Erro durante o download.")
        self.btn_download.configure(state="normal")
        messagebox.showerror("Erro de Download", f"Não foi possível concluir o download:\n{err_msg}")

    def open_last_downloaded_folder(self):
        if self.last_downloaded_folder and os.path.exists(self.last_downloaded_folder):
            try:
                os.startfile(self.last_downloaded_folder)
            except Exception as e:
                messagebox.showerror("Erro", str(e))
        else:
            default_dir = self.config.get("download_dir", os.path.expanduser("~"))
            try:
                os.startfile(default_dir)
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    # ==========================
    # ABA 2: TV AO VIVO & IPTV
    # ==========================
    def create_iptv_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        # Cabeçalho Gamer
        header = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        header.pack(fill="x", pady=(2, 8))

        lbl_title = ctk.CTkLabel(
            header, 
            text="📺 TV AO VIVO & TRANSMISSÕES IPTV", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(header, text="TV Ao Vivo & IPTV", font=("Arial", 18, "bold"), fg=self.theme["text_color"])
        lbl_title.pack(side="left")

        lbl_live_badge = ctk.CTkLabel(
            header,
            text="[ ● LIVE HUD HLS/IPTV ENGINE ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(header, text="● AO VIVO", fg=self.theme["accent_color"])
        lbl_live_badge.pack(side="right", padx=6)

        # Entrada de URL
        url_card = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        url_card.pack(fill="x", pady=(0, 10))

        url_inner = ctk.CTkFrame(url_card, fg_color="transparent") if ctk else tk.Frame(url_card, bg=self.theme["card_hover"])
        url_inner.pack(fill="x", padx=12, pady=10)

        lbl_url = ctk.CTkLabel(
            url_inner, 
            text="Link do Canal / Live (.m3u8, IPTV, YouTube Live, Web TV):", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(url_inner, text="Link do Canal / Live:", fg=self.theme["text_color"])
        lbl_url.pack(anchor="w", pady=(0, 4))

        input_row = ctk.CTkFrame(url_inner, fg_color="transparent") if ctk else tk.Frame(url_inner, bg=self.theme["card_hover"])
        input_row.pack(fill="x")

        saved_url = self.config.get("last_iptv_url", "https://ntv1.akamaized.net/hls/live/2014075/NASA-NTV1-HLS/master.m3u8")
        self.entry_iptv_url = ctk.CTkEntry(
            input_row, 
            placeholder_text="Cole o link aqui (Ex: https://.../stream.m3u8 ou YouTube Live)", 
            height=38, 
            font=ctk.CTkFont(size=13)
        ) if ctk else tk.Entry(input_row, font=("Arial", 12))
        self.entry_iptv_url.insert(0, saved_url)
        self.entry_iptv_url.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_play_live = ctk.CTkButton(
            input_row, 
            text="▶️ REPRODUZIR", 
            width=130, 
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.play_current_iptv_input
        ) if ctk else tk.Button(input_row, text="▶️ Tocar", command=self.play_current_iptv_input)
        btn_play_live.pack(side="left", padx=4)

        btn_save_ch = ctk.CTkButton(
            input_row, 
            text="⭐ Salvar Canal", 
            width=110, 
            height=38,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.save_channel_dialog
        ) if ctk else tk.Button(input_row, text="⭐ Salvar", command=self.save_channel_dialog)
        btn_save_ch.pack(side="left", padx=4)

        btn_import_m3u = ctk.CTkButton(
            input_row, 
            text="📂 Lista .M3U", 
            width=100, 
            height=38,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.import_m3u_dialog
        ) if ctk else tk.Button(input_row, text="📂 Importar M3U", command=self.import_m3u_dialog)
        btn_import_m3u.pack(side="left", padx=(4, 0))

        # Divisão Principal: Player (Esquerda) e Guia (Direita)
        body = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        body.pack(fill="both", expand=True)

        body.grid_columnconfigure(0, weight=6)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        # Player Panel
        player_panel = ctk.CTkFrame(
            body, 
            fg_color=self.get_card_color(), 
            corner_radius=12,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(body, bg=self.theme["card_hover"])
        player_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        # Status Bar
        status_bar = ctk.CTkFrame(player_panel, fg_color="transparent") if ctk else tk.Frame(player_panel, bg=self.theme["card_hover"])
        status_bar.pack(fill="x", padx=12, pady=(10, 6))

        self.lbl_iptv_status_badge = ctk.CTkLabel(
            status_bar,
            text="● STREAM HUD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ff0044"
        ) if ctk else tk.Label(status_bar, text="● AO VIVO", fg="#ff0044")
        self.lbl_iptv_status_badge.pack(side="left", padx=(0, 8))

        self.lbl_iptv_title = ctk.CTkLabel(
            status_bar, 
            text="Nenhum canal ativo", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=self.theme["accent_color"],
            anchor="w"
        ) if ctk else tk.Label(status_bar, text="Nenhum canal ativo", fg=self.theme["accent_color"])
        self.lbl_iptv_title.pack(side="left", fill="x", expand=True)

        # Vídeo Frame
        self.video_frame = ctk.CTkFrame(player_panel, corner_radius=8, fg_color="#000000") if ctk else tk.Frame(player_panel, bg="#000000")
        self.video_frame.pack(fill="both", expand=True, padx=12, pady=6)

        self.video_canvas_container = tk.Frame(self.video_frame, bg="#000000")
        self.video_canvas_container.place(x=0, y=0, relwidth=1, relheight=1)

        self.video_overlay = ctk.CTkFrame(self.video_frame, fg_color="#090a10", corner_radius=8) if ctk else tk.Frame(self.video_frame, bg="#090a10")
        self.video_overlay.place(x=0, y=0, relwidth=1, relheight=1)

        overlay_content = ctk.CTkFrame(self.video_overlay, fg_color="transparent") if ctk else tk.Frame(self.video_overlay, bg="#090a10")
        overlay_content.place(relx=0.5, rely=0.5, anchor="center")

        lbl_big_icon = ctk.CTkLabel(overlay_content, text="📺", font=ctk.CTkFont(size=44)) if ctk else tk.Label(overlay_content, text="📺", font=("Arial", 36))
        lbl_big_icon.pack(pady=(0, 4))

        self.lbl_stream_state = ctk.CTkLabel(
            overlay_content,
            text="Transmissão Pronta",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(overlay_content, text="Transmissão Pronta", fg=self.theme["accent_color"])
        self.lbl_stream_state.pack(pady=2)

        lbl_hint = ctk.CTkLabel(
            overlay_content,
            text="Selecione um canal ou cole o link e clique em 'REPRODUZIR'.\nAssista diretamente aqui, no Player HLS acelerado ou no VLC.",
            font=ctk.CTkFont(size=11),
            text_color=self.theme["subtext_color"],
            justify="center"
        ) if ctk else tk.Label(overlay_content, text="Selecione um canal ao lado.", fg=self.theme["subtext_color"])
        lbl_hint.pack(pady=(4, 12))

        quick_btns = ctk.CTkFrame(overlay_content, fg_color="transparent") if ctk else tk.Frame(overlay_content, bg="#090a10")
        quick_btns.pack()

        btn_launch_web = ctk.CTkButton(
            quick_btns,
            text="🌐 Abrir Player HLS Integrado",
            height=34,
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.open_current_in_web_player
        ) if ctk else tk.Button(quick_btns, text="Player HLS", command=self.open_current_in_web_player)
        btn_launch_web.pack(side="left", padx=5)

        btn_launch_vlc = ctk.CTkButton(
            quick_btns,
            text="🚀 Abrir no VLC",
            height=34,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_current_in_external_vlc
        ) if ctk else tk.Button(quick_btns, text="VLC", command=self.open_current_in_external_vlc)
        btn_launch_vlc.pack(side="left", padx=5)

        # Controles
        controls_bar = ctk.CTkFrame(player_panel, fg_color="transparent") if ctk else tk.Frame(player_panel, bg=self.theme["card_hover"])
        controls_bar.pack(fill="x", padx=12, pady=(4, 12))

        self.btn_iptv_play = ctk.CTkButton(
            controls_bar,
            text="▶️ Tocar",
            width=80,
            height=36,
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.toggle_iptv_playback
        ) if ctk else tk.Button(controls_bar, text="▶️", command=self.toggle_iptv_playback)
        self.btn_iptv_play.pack(side="left", padx=(0, 6))

        self.btn_iptv_stop = ctk.CTkButton(
            controls_bar,
            text="⏹️ Parar",
            width=80,
            height=36,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.stop_iptv_playback
        ) if ctk else tk.Button(controls_bar, text="⏹️", command=self.stop_iptv_playback)
        self.btn_iptv_stop.pack(side="left", padx=4)

        lbl_v = ctk.CTkLabel(controls_bar, text="🔊", font=ctk.CTkFont(size=13)) if ctk else tk.Label(controls_bar, text="🔊")
        lbl_v.pack(side="left", padx=(8, 4))

        if ctk:
            self.iptv_vol_slider = ctk.CTkSlider(controls_bar, from_=0, to=100, width=105, command=self.set_iptv_volume)
            self.iptv_vol_slider.set(self.iptv_volume)
            self.iptv_vol_slider.pack(side="left", padx=4)

        lbl_motor = ctk.CTkLabel(controls_bar, text="Modo:", font=ctk.CTkFont(size=11), text_color=self.theme["subtext_color"]) if ctk else tk.Label(controls_bar, text="Modo:")
        lbl_motor.pack(side="left", padx=(12, 4))

        engine_opts = ["HLS Player Web (Recomendado)", "VLC Embutido", "VLC Externo"]
        self.engine_var = tk.StringVar(value="HLS Player Web (Recomendado)")
        if ctk:
            self.combo_engine = ctk.CTkComboBox(controls_bar, values=engine_opts, variable=self.engine_var, width=175, font=ctk.CTkFont(size=11))
            self.combo_engine.pack(side="left", padx=4)
        else:
            self.combo_engine = tk.OptionMenu(controls_bar, self.engine_var, *engine_opts)
            self.combo_engine.pack(side="left", padx=4)

        # Guide Panel
        guide_panel = ctk.CTkFrame(
            body, 
            fg_color=self.get_card_color(), 
            corner_radius=12,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(body, bg=self.theme["card_hover"])
        guide_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)

        guide_head = ctk.CTkFrame(guide_panel, fg_color="transparent") if ctk else tk.Frame(guide_panel, bg=self.theme["card_hover"])
        guide_head.pack(fill="x", padx=12, pady=(10, 6))

        lbl_guide = ctk.CTkLabel(
            guide_head, 
            text="📑 GUIA DE CANAIS & FAVORITOS", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(guide_head, text="Lista de Canais:", font=("Arial", 12, "bold"), fg=self.theme["text_color"])
        lbl_guide.pack(side="left")

        search_frame = ctk.CTkFrame(guide_panel, fg_color="transparent") if ctk else tk.Frame(guide_panel, bg=self.theme["card_hover"])
        search_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.entry_channel_search = ctk.CTkEntry(
            search_frame, 
            placeholder_text="🔍 Buscar canal...", 
            height=32, 
            font=ctk.CTkFont(size=12)
        ) if ctk else tk.Entry(search_frame)
        self.entry_channel_search.pack(fill="x")
        self.entry_channel_search.bind("<KeyRelease>", lambda e: self.filter_channels_list())

        self.channel_listbox = tk.Listbox(
            guide_panel,
            bg=self.theme_mgr._adjust_brightness(self.theme["card_color"], 0.75),
            fg=self.theme["text_color"],
            selectbackground=self.theme["accent_color"],
            selectforeground="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightcolor=self.theme["accent_color"],
            font=("Arial", 10)
        )
        self.channel_listbox.pack(fill="both", expand=True, padx=12, pady=4)
        self.channel_listbox.bind("<Double-Button-1>", lambda e: self.play_selected_channel())

        guide_footer = ctk.CTkFrame(guide_panel, fg_color="transparent") if ctk else tk.Frame(guide_panel, bg=self.theme["card_hover"])
        guide_footer.pack(fill="x", padx=12, pady=(6, 12))

        btn_ch_play = ctk.CTkButton(
            guide_footer,
            text="▶️ Assistir",
            height=32,
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.play_selected_channel
        ) if ctk else tk.Button(guide_footer, text="▶️ Assistir", command=self.play_selected_channel)
        btn_ch_play.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_ch_del = ctk.CTkButton(
            guide_footer,
            text="🗑️ Excluir",
            height=32,
            width=75,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color="#ef4444",
            command=self.delete_selected_channel
        ) if ctk else tk.Button(guide_footer, text="Excluir", command=self.delete_selected_channel)
        btn_ch_del.pack(side="left", padx=4)

        btn_ch_export = ctk.CTkButton(
            guide_footer,
            text="💾 Salvar M3U",
            height=32,
            width=85,
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.export_m3u_dialog
        ) if ctk else tk.Button(guide_footer, text="Salvar M3U", command=self.export_m3u_dialog)
        btn_ch_export.pack(side="left", padx=(4, 0))

        self.populate_channel_listbox()
        return page

    def populate_channel_listbox(self, filter_text=""):
        self.channel_listbox.delete(0, tk.END)
        filter_text = filter_text.lower().strip()
        self.filtered_indices = []

        for idx, ch in enumerate(self.iptv_mgr.channels):
            name = ch.get("name", "Sem Nome")
            cat = ch.get("category", "Geral")
            if not filter_text or filter_text in name.lower() or filter_text in cat.lower():
                display_str = f"📺 {name}  [{cat}]"
                self.channel_listbox.insert(tk.END, display_str)
                self.filtered_indices.append(idx)

    def filter_channels_list(self):
        text = self.entry_channel_search.get()
        self.populate_channel_listbox(text)

    def play_selected_channel(self):
        sel = self.channel_listbox.curselection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um canal da lista para assistir.")
            return

        filtered_idx = sel[0]
        actual_idx = self.filtered_indices[filtered_idx]
        ch = self.iptv_mgr.channels[actual_idx]

        name = ch.get("name", "Canal")
        url = ch.get("url", "")
        self.entry_iptv_url.delete(0, tk.END)
        self.entry_iptv_url.insert(0, url)
        self.start_iptv_playback(url, name)

    def play_current_iptv_input(self):
        url = self.entry_iptv_url.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Por favor, digite ou cole um link de canal/vídeo.")
            return
        self.start_iptv_playback(url, "Transmissão Ao Vivo")

    def start_iptv_playback(self, url, name="Transmissão Ao Vivo"):
        self.current_iptv_name = name
        self.current_iptv_stream = url
        self.config["last_iptv_url"] = url
        self.save_config()

        self.lbl_iptv_title.configure(text=f"{name}")
        self.lbl_stream_state.configure(text=f"Conectando a {name}...")

        if IPTVManager.is_youtube_or_twitch(url):
            self.lbl_stream_state.configure(text="Resolvendo stream ao vivo com yt-dlp...")
            threading.Thread(target=self._resolve_and_play_worker, args=(url, name), daemon=True).start()
        else:
            self._execute_playback(url, name)

    def _resolve_and_play_worker(self, url, name):
        resolved_url = IPTVManager.resolve_live_stream_url(url)
        self.root.after(0, lambda: self._execute_playback(resolved_url, name))

    def _execute_playback(self, stream_url, name):
        selected_engine = self.engine_var.get()
        self.lbl_stream_state.configure(text=f"▶️ Reproduzindo: {name}")
        self.btn_iptv_play.configure(text="⏸️ Pausar")
        self.iptv_is_live = True

        if "VLC Embutido" in selected_engine:
            if VLC_AVAILABLE:
                if not self.vlc_player:
                    try:
                        self.vlc_player = EmbeddedVLCPlayer(self.video_canvas_container.winfo_id())
                    except Exception as e:
                        print(f"Erro VLC: {e}")
                
                if self.vlc_player and self.vlc_player.player:
                    self.video_overlay.place_forget()
                    ok, msg = self.vlc_player.play(stream_url)
                    if not ok:
                        self.video_overlay.place(x=0, y=0, relwidth=1, relheight=1)
                        messagebox.showwarning("Aviso VLC", f"Não foi possível reproduzir embutido:\n{msg}\nAbrindo no Player Web...")
                        IPTVManager.launch_hls_web_player(stream_url, name)
                    return
            
            messagebox.showinfo(
                "VLC Embutido", 
                "O player VLC nativo não está disponível neste computador.\nAbrindo no Player Web HLS Integrado de alta performance!"
            )
            IPTVManager.launch_hls_web_player(stream_url, name)

        elif "VLC Externo" in selected_engine:
            ok, msg = IPTVManager.launch_external_vlc(stream_url)
            if not ok:
                messagebox.showwarning("VLC Externo", f"{msg}\nAbrindo no Player Web HLS em vez disso.")
                IPTVManager.launch_hls_web_player(stream_url, name)

        else:
            IPTVManager.launch_hls_web_player(stream_url, name)

    def open_current_in_web_player(self):
        url = self.entry_iptv_url.get().strip() or self.current_iptv_stream
        if not url:
            messagebox.showinfo("Aviso", "Insira ou selecione um canal primeiro.")
            return
        IPTVManager.launch_hls_web_player(url, self.current_iptv_name)

    def open_current_in_external_vlc(self):
        url = self.entry_iptv_url.get().strip() or self.current_iptv_stream
        if not url:
            messagebox.showinfo("Aviso", "Insira ou selecione um canal primeiro.")
            return
        ok, msg = IPTVManager.launch_external_vlc(url)
        if not ok:
            messagebox.showerror("Erro VLC", msg)

    def toggle_iptv_playback(self):
        if self.vlc_player and self.vlc_player.player:
            self.vlc_player.pause()
            if self.vlc_player.is_paused:
                self.btn_iptv_play.configure(text="▶️ Tocar")
            else:
                self.btn_iptv_play.configure(text="⏸️ Pausar")
        else:
            self.play_current_iptv_input()

    def stop_iptv_playback(self):
        if self.vlc_player:
            self.vlc_player.stop()
        self.video_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.btn_iptv_play.configure(text="▶️ Tocar")
        self.lbl_stream_state.configure(text="Transmissão Interrompida")

    def set_iptv_volume(self, val):
        self.iptv_volume = int(float(val))
        if self.vlc_player:
            self.vlc_player.set_volume(self.iptv_volume)

    def save_channel_dialog(self):
        url = self.entry_iptv_url.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Insira uma URL antes de salvar.")
            return
        name = simpledialog.askstring("Salvar Canal", "Digite o nome para este canal:", initialvalue=self.current_iptv_name)
        if name:
            cat = simpledialog.askstring("Categoria", "Digite a categoria do canal:", initialvalue="Favoritos") or "Favoritos"
            ok, msg = self.iptv_mgr.add_channel(name, url, cat)
            self.populate_channel_listbox()
            messagebox.showinfo("Canal", msg)

    def delete_selected_channel(self):
        sel = self.channel_listbox.curselection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um canal para remover.")
            return
        filtered_idx = sel[0]
        actual_idx = self.filtered_indices[filtered_idx]
        ch = self.iptv_mgr.channels[actual_idx]
        if messagebox.askyesno("Confirmar", f"Deseja remover o canal '{ch.get('name')}'?"):
            self.iptv_mgr.remove_channel(actual_idx)
            self.populate_channel_listbox()

    def import_m3u_dialog(self):
        f = filedialog.askopenfilename(
            title="Importar Lista de Canais M3U / M3U8",
            filetypes=[("Listas IPTV M3U", "*.m3u;*.m3u8"), ("Todos os Arquivos", "*.*")]
        )
        if f:
            count, msg = self.iptv_mgr.import_m3u_file(f)
            self.populate_channel_listbox()
            messagebox.showinfo("Importação M3U", msg)

    def export_m3u_dialog(self):
        f = filedialog.asksaveasfilename(
            title="Salvar Lista M3U",
            defaultextension=".m3u",
            initialfile="MinhaListaIPTV.m3u",
            filetypes=[("Lista IPTV M3U", "*.m3u")]
        )
        if f:
            ok, msg = self.iptv_mgr.export_m3u_file(f)
            if ok:
                messagebox.showinfo("Exportado", msg)
            else:
                messagebox.showerror("Erro", msg)

    # ==========================
    # ABA 3: PLAYER DE MÚSICA & ÁUDIO GAMER
    # ==========================
    def create_player_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        head_box = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        head_box.pack(fill="x", pady=(2, 10))

        title = ctk.CTkLabel(
            head_box, 
            text="🎧 PLAYER DE ÁUDIO & MÍDIA LOCAL", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(head_box, text="PLAYER DE ÁUDIO", font=("Arial", 18, "bold"), fg=self.theme["text_color"])
        title.pack(side="left")

        tag_pl = ctk.CTkLabel(
            head_box,
            text="[ PYGAME HI-FI SOUND ENGINE ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(head_box, text="[ HI-FI AUDIO ]", fg=self.theme["accent_color"])
        tag_pl.pack(side="right", padx=6)

        now_playing_box = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=12,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        now_playing_box.pack(fill="x", pady=6, padx=4)

        self.lbl_track_title = ctk.CTkLabel(
            now_playing_box, 
            text="Nenhuma música selecionada", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(now_playing_box, text="Nenhuma música selecionada", font=("Arial", 14, "bold"), fg=self.theme["accent_color"])
        self.lbl_track_title.pack(pady=(14, 6))

        controls_frame = ctk.CTkFrame(now_playing_box, fg_color="transparent") if ctk else tk.Frame(now_playing_box, bg=self.theme["card_hover"])
        controls_frame.pack(pady=(6, 14))

        btn_prev = ctk.CTkButton(
            controls_frame, 
            text="⏮️", 
            width=50, 
            height=38, 
            font=ctk.CTkFont(size=16), 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.play_prev_track
        ) if ctk else tk.Button(controls_frame, text="⏮️", command=self.play_prev_track)
        btn_prev.pack(side="left", padx=6)

        self.btn_play_pause = ctk.CTkButton(
            controls_frame, 
            text="▶️ Tocar", 
            width=110, 
            height=38, 
            font=ctk.CTkFont(size=14, weight="bold"), 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.toggle_play_pause
        ) if ctk else tk.Button(controls_frame, text="▶️ Tocar", command=self.toggle_play_pause)
        self.btn_play_pause.pack(side="left", padx=6)

        btn_stop = ctk.CTkButton(
            controls_frame, 
            text="⏹️", 
            width=50, 
            height=38, 
            font=ctk.CTkFont(size=16), 
            fg_color=self.get_card_hover_color(), 
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"], 
            command=self.stop_playback
        ) if ctk else tk.Button(controls_frame, text="⏹️", command=self.stop_playback)
        btn_stop.pack(side="left", padx=6)

        btn_next = ctk.CTkButton(
            controls_frame, 
            text="⏭️", 
            width=50, 
            height=38, 
            font=ctk.CTkFont(size=16), 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.play_next_track
        ) if ctk else tk.Button(controls_frame, text="⏭️", command=self.play_next_track)
        btn_next.pack(side="left", padx=6)

        # Volume Slider
        vol_frame = ctk.CTkFrame(now_playing_box, fg_color="transparent") if ctk else tk.Frame(now_playing_box, bg=self.theme["card_hover"])
        vol_frame.pack(fill="x", padx=30, pady=(0, 12))

        lbl_vol = ctk.CTkLabel(vol_frame, text="Volume: 🔊", font=ctk.CTkFont(size=12), text_color=self.theme["subtext_color"]) if ctk else tk.Label(vol_frame, text="Volume:")
        lbl_vol.pack(side="left", padx=6)

        if ctk:
            self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=1, command=self.set_volume, progress_color=self.theme["accent_color"])
            self.vol_slider.set(0.7)
            self.vol_slider.pack(side="left", fill="x", expand=True, padx=8)

        # Playlist Header
        playlist_header = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        playlist_header.pack(fill="x", pady=(10, 4))

        lbl_pl = ctk.CTkLabel(playlist_header, text="Fila de Reprodução:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(playlist_header, text="Fila de Reprodução:", fg=self.theme["text_color"])
        lbl_pl.pack(side="left")

        btn_add_files = ctk.CTkButton(
            playlist_header, 
            text="➕ Adicionar Músicas / Vídeos", 
            width=190, 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.add_media_files
        ) if ctk else tk.Button(playlist_header, text="➕ Adicionar Arquivos", command=self.add_media_files)
        btn_add_files.pack(side="right")

        self.media_listbox = tk.Listbox(
            page,
            bg=self.theme_mgr._adjust_brightness(self.theme["card_color"], 0.75),
            fg=self.theme["text_color"],
            selectbackground=self.theme["accent_color"],
            selectforeground="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightcolor=self.theme["accent_color"],
            font=("Arial", 10)
        )
        self.media_listbox.pack(fill="both", expand=True, pady=6)
        self.media_listbox.bind("<Double-Button-1>", lambda e: self.play_selected_track())

        return page

    def add_media_files(self):
        files = filedialog.askopenfilenames(
            title="Selecionar Músicas ou Vídeos",
            filetypes=[("Arquivos de Áudio/Vídeo", "*.mp3;*.wav;*.ogg;*.flac;*.mp4;*.mkv;*.avi"), ("Todos os Arquivos", "*.*")]
        )
        if files:
            for f in files:
                self.playlist.append(f)
                self.media_listbox.insert(tk.END, f"🎵 {os.path.basename(f)}")

    def toggle_play_pause(self):
        if not PYGAME_AVAILABLE:
            messagebox.showwarning("Aviso", "Pygame não está instalado.")
            return

        if not self.playlist:
            messagebox.showinfo("Fila Vazia", "Adicione músicas à fila clicando em '➕ Adicionar Músicas'.")
            return

        if self.is_playing:
            if self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.btn_play_pause.configure(text="⏸️ Pausar")
            else:
                pygame.mixer.music.pause()
                self.is_paused = True
                self.btn_play_pause.configure(text="▶️ Retomar")
        else:
            if self.current_track_idx < 0 and self.playlist:
                self.current_track_idx = 0
            self.play_track(self.current_track_idx)

    def play_track(self, index):
        if not PYGAME_AVAILABLE or index < 0 or index >= len(self.playlist):
            return

        track_path = self.playlist[index]
        ext = os.path.splitext(track_path)[1].lower()

        if ext in [".mp4", ".mkv", ".avi", ".webm"]:
            try:
                os.startfile(track_path)
                self.lbl_track_title.configure(text=f"🎬 Reproduzindo vídeo: {os.path.basename(track_path)}")
                return
            except Exception as e:
                print(f"Erro ao abrir vídeo: {e}")

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.current_track_idx = index
            self.btn_play_pause.configure(text="⏸️ Pausar")
            self.lbl_track_title.configure(text=f"🎶 Tocando: {os.path.basename(track_path)}")
            self.media_listbox.selection_clear(0, tk.END)
            self.media_listbox.selection_set(index)
            self.media_listbox.see(index)
        except Exception as e:
            messagebox.showerror("Erro ao Tocar", f"Falha ao reproduzir áudio: {e}")

    def play_selected_track(self):
        sel = self.media_listbox.curselection()
        if sel:
            self.play_track(sel[0])

    def stop_playback(self):
        if PYGAME_AVAILABLE and self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.btn_play_pause.configure(text="▶️ Tocar")
            self.lbl_track_title.configure(text="Reprodução interrompida.")

    def play_next_track(self):
        if self.playlist and self.current_track_idx < len(self.playlist) - 1:
            self.play_track(self.current_track_idx + 1)

    def play_prev_track(self):
        if self.playlist and self.current_track_idx > 0:
            self.play_track(self.current_track_idx - 1)

    def set_volume(self, val):
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(float(val))

    # ==========================
    # ABA 4: TEMAS RGB CHROMA
    # ==========================
    def create_themes_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        head_box = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        head_box.pack(fill="x", pady=(2, 10))

        title = ctk.CTkLabel(
            head_box, 
            text="🎨 MOTOR DE TEMAS & RGB CHROMA", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(head_box, text="TEMAS RGB CHROMA", font=("Arial", 18, "bold"), fg=self.theme["text_color"])
        title.pack(side="left")

        tag_th = ctk.CTkLabel(
            head_box,
            text="[ DYNAMIC PALETTE ENGINE ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(head_box, text="[ RGB ENGINE ]", fg=self.theme["accent_color"])
        tag_th.pack(side="right", padx=6)

        box_presets = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_presets.pack(fill="x", pady=6)

        lbl_preset = ctk.CTkLabel(box_presets, text="Perfis de Iluminação & Temas Gamer:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_presets, text="Temas:")
        lbl_preset.pack(anchor="w", padx=14, pady=(12, 6))

        preset_row = ctk.CTkFrame(box_presets, fg_color="transparent") if ctk else tk.Frame(box_presets, bg=self.theme["card_hover"])
        preset_row.pack(fill="x", padx=14, pady=(0, 14))

        theme_names = self.theme_mgr.get_all_theme_names()
        self.theme_dropdown_var = tk.StringVar(value=self.current_theme_name)
        if ctk:
            self.theme_dropdown = ctk.CTkOptionMenu(
                preset_row, 
                values=theme_names, 
                variable=self.theme_dropdown_var,
                width=270,
                command=self.on_theme_select
            )
            self.theme_dropdown.pack(side="left", padx=(0, 10))
        else:
            self.theme_dropdown = tk.OptionMenu(preset_row, self.theme_dropdown_var, *theme_names, command=self.on_theme_select)
            self.theme_dropdown.pack(side="left", padx=(0, 10))

        btn_import_theme = ctk.CTkButton(
            preset_row, 
            text="📂 Importar (.json / .css)", 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.import_theme_file
        ) if ctk else tk.Button(preset_row, text="📂 Importar", command=self.import_theme_file)
        btn_import_theme.pack(side="left", padx=6)

        btn_export_theme = ctk.CTkButton(
            preset_row, 
            text="💾 Exportar Tema", 
            width=120, 
            fg_color=self.get_card_hover_color(), 
            text_color=self.theme["text_color"], 
            hover_color=self.theme["accent_color"], 
            command=self.export_current_theme
        ) if ctk else tk.Button(preset_row, text="💾 Exportar", command=self.export_current_theme)
        btn_export_theme.pack(side="left", padx=6)

        # Personalizar Cores
        box_custom = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_custom.pack(fill="x", pady=8)

        lbl_custom_title = ctk.CTkLabel(box_custom, text="Personalizar Paleta RGB Livremente:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_custom, text="Crie suas cores:")
        lbl_custom_title.pack(anchor="w", padx=14, pady=(12, 8))

        self.editing_theme = dict(self.theme)

        colors_grid = ctk.CTkFrame(box_custom, fg_color="transparent") if ctk else tk.Frame(box_custom, bg=self.theme["card_hover"])
        colors_grid.pack(fill="x", padx=14, pady=4)

        color_options = [
            ("Luz Neon Primária (Accent / Destaque)", "accent_color"),
            ("Fundo do HUD (Background)", "bg_color"),
            ("Painel Lateral Gamer (Sidebar)", "sidebar_color"),
            ("Cartões e Módulos (Card)", "card_color"),
            ("Cor dos Textos do HUD", "text_color"),
        ]

        self.color_preview_buttons = {}
        for row, (label_text, key) in enumerate(color_options):
            lbl = ctk.CTkLabel(colors_grid, text=label_text, font=ctk.CTkFont(size=12), text_color=self.theme["text_color"]) if ctk else tk.Label(colors_grid, text=label_text)
            lbl.grid(row=row, column=0, sticky="w", pady=5)

            btn_color = ctk.CTkButton(
                colors_grid, 
                text=self.editing_theme.get(key, "#ffffff"),
                width=130,
                fg_color=self.editing_theme.get(key, "#ffffff"),
                text_color="#000000" if key in ["accent_color", "text_color"] else "#ffffff",
                command=lambda k=key: self.pick_color_for_key(k)
            ) if ctk else tk.Button(colors_grid, text=self.editing_theme.get(key, "#ffffff"), command=lambda k=key: self.pick_color_for_key(k))
            btn_color.grid(row=row, column=1, padx=20, pady=5)
            self.color_preview_buttons[key] = btn_color

        save_row = ctk.CTkFrame(box_custom, fg_color="transparent") if ctk else tk.Frame(box_custom, bg=self.theme["card_hover"])
        save_row.pack(fill="x", padx=14, pady=(12, 16))

        lbl_name = ctk.CTkLabel(save_row, text="Nome do seu Perfil RGB:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(save_row, text="Nome:")
        lbl_name.pack(side="left", padx=(0, 10))

        self.entry_theme_name = ctk.CTkEntry(save_row, placeholder_text="Ex: Meu Perfil Neon Cyber", width=240) if ctk else tk.Entry(save_row)
        self.entry_theme_name.pack(side="left", padx=(0, 12))

        btn_save_theme = ctk.CTkButton(
            save_row, 
            text="✨ Salvar e Aplicar", 
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.save_custom_theme
        ) if ctk else tk.Button(save_row, text="Salvar e Aplicar", command=self.save_custom_theme)
        btn_save_theme.pack(side="left")

        return page

    def pick_color_for_key(self, key):
        initial = self.editing_theme.get(key, "#ffffff")
        chosen_color = colorchooser.askcolor(color=initial, title=f"Escolha a cor para {key}")
        if chosen_color and chosen_color[1]:
            hex_val = chosen_color[1]
            self.editing_theme[key] = hex_val
            if key == "accent_color":
                self.editing_theme["accent_hover"] = self.theme_mgr._adjust_brightness(hex_val, 1.2)
                self.editing_theme["border_color"] = hex_val
            elif key == "card_color":
                self.editing_theme["card_hover"] = self.theme_mgr._adjust_brightness(hex_val, 1.25)
            
            if key in self.color_preview_buttons:
                btn = self.color_preview_buttons[key]
                if ctk:
                    btn.configure(fg_color=hex_val, text=hex_val)
                else:
                    btn.configure(bg=hex_val, text=hex_val)

    def save_custom_theme(self):
        name = self.entry_theme_name.get().strip()
        if not name:
            name = f"Perfil Gamer {int(time.time()) % 1000}"
        
        self.editing_theme["name"] = name
        saved_name = self.theme_mgr.save_custom_theme(dict(self.editing_theme))
        
        theme_names = self.theme_mgr.get_all_theme_names()
        if ctk:
            self.theme_dropdown.configure(values=theme_names)
            self.theme_dropdown_var.set(saved_name)
        
        self.apply_theme(saved_name)
        messagebox.showinfo("Perfil Salvo", f"O perfil RGB '{saved_name}' foi salvo e aplicado!")

    def on_theme_select(self, theme_name):
        self.apply_theme(theme_name)

    def import_theme_file(self):
        file_path = filedialog.askopenfilename(
            title="Importar Perfil de Tema",
            filetypes=[("Arquivos de Tema", "*.json;*.css"), ("Tema JSON", "*.json"), ("Tema CSS", "*.css")]
        )
        if file_path:
            try:
                theme_name = self.theme_mgr.import_theme_from_file(file_path)
                theme_names = self.theme_mgr.get_all_theme_names()
                if ctk:
                    self.theme_dropdown.configure(values=theme_names)
                    self.theme_dropdown_var.set(theme_name)
                self.apply_theme(theme_name)
                messagebox.showinfo("Sucesso", f"Tema importado: '{theme_name}'!")
            except Exception as e:
                messagebox.showerror("Erro na Importação", f"Falha ao importar tema:\n{e}")

    def export_current_theme(self):
        target_path = filedialog.asksaveasfilename(
            title="Exportar Perfil RGB",
            defaultextension=".json",
            initialfile=f"{self.theme['name']}.json",
            filetypes=[("Tema JSON", "*.json")]
        )
        if target_path:
            try:
                self.theme_mgr.export_theme_to_file(self.theme["name"], target_path)
                messagebox.showinfo("Exportado", f"Tema exportado para:\n{target_path}")
            except Exception as e:
                messagebox.showerror("Erro ao Exportar", str(e))

    # ==========================
    # ABA 5: PAPEL DE PAREDE, VIDRO & TRANSPARÊNCIA
    # ==========================
    def create_wallpaper_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        head_box = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        head_box.pack(fill="x", pady=(2, 10))

        title = ctk.CTkLabel(
            head_box, 
            text="🖼️ PAPEL DE PAREDE & TRANSPARÊNCIA CYBER", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(head_box, text="PAPEL DE PAREDE & TRANSPARÊNCIA", font=("Arial", 18, "bold"), fg=self.theme["text_color"])
        title.pack(side="left")

        tag_wp = ctk.CTkLabel(
            head_box,
            text="[ GLASS & ALPHA CONTROLLER ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(head_box, text="[ GLASS CONTROLLER ]", fg=self.theme["accent_color"])
        tag_wp.pack(side="right", padx=6)

        # Imagem do PC
        box_wp = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_wp.pack(fill="x", pady=6)

        lbl_desc = ctk.CTkLabel(
            box_wp, 
            text="Defina qualquer papel de parede do seu computador como fundo do aplicativo.\nO fundo transparente permite ver a arte do seu PC combinada com as bordas neon gamer!",
            justify="left",
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(box_wp, text="Escolha uma imagem de fundo:", fg=self.theme["subtext_color"])
        lbl_desc.pack(anchor="w", padx=14, pady=(12, 8))

        btn_row = ctk.CTkFrame(box_wp, fg_color="transparent") if ctk else tk.Frame(box_wp, bg=self.theme["card_hover"])
        btn_row.pack(fill="x", padx=14, pady=6)

        btn_select_wp = ctk.CTkButton(
            btn_row, 
            text="🖼️ Escolher Imagem do PC...", 
            fg_color=self.theme["accent_color"], 
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.select_wallpaper_file
        ) if ctk else tk.Button(btn_row, text="🖼️ Escolher Imagem...", command=self.select_wallpaper_file)
        btn_select_wp.pack(side="left", padx=(0, 10))

        btn_clear_wp = ctk.CTkButton(
            btn_row, 
            text="❌ Restaurar Fundo do Tema", 
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.clear_wallpaper
        ) if ctk else tk.Button(btn_row, text="Remover Wallpaper", command=self.clear_wallpaper)
        btn_clear_wp.pack(side="left")

        self.lbl_wp_path = ctk.CTkLabel(
            box_wp, 
            text=f"Arquivo atual: {self.config.get('wallpaper_path') or 'Nenhum (usando cor do tema)'}", 
            text_color=self.theme["subtext_color"],
            anchor="w"
        ) if ctk else tk.Label(box_wp, text="Nenhum")
        self.lbl_wp_path.pack(anchor="w", padx=14, pady=(10, 12))

        # Modos de Transparência
        box_style = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_style.pack(fill="x", pady=6)

        lbl_style_title = ctk.CTkLabel(box_style, text="Estilo de Transparência dos Cartões HUD:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_style, text="Transparência:")
        lbl_style_title.pack(anchor="w", padx=14, pady=(12, 6))

        mode_opts = ["🌟 100% Transparente", "🪟 Vidro Translúcido", "⬛ Sólido Tradicional"]
        curr_mode = self.config.get("transparency_mode", "transparent")
        mode_map = {"transparent": "🌟 100% Transparente", "glass": "🪟 Vidro Translúcido", "solid": "⬛ Sólido Tradicional"}
        self.transparency_var = tk.StringVar(value=mode_map.get(curr_mode, "🌟 100% Transparente"))

        if ctk:
            self.seg_mode = ctk.CTkSegmentedButton(
                box_style, 
                values=mode_opts, 
                variable=self.transparency_var,
                command=self.on_transparency_mode_change
            )
            self.seg_mode.pack(fill="x", padx=14, pady=(4, 14))

        # Ajustes de Efeitos
        box_effects = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_effects.pack(fill="x", pady=6)

        lbl_eff_title = ctk.CTkLabel(box_effects, text="Efeitos Visuais e Desfoque Glass:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_effects, text="Efeitos:")
        lbl_eff_title.pack(anchor="w", padx=14, pady=(12, 8))

        lbl_blur = ctk.CTkLabel(box_effects, text="Desfoque do Fundo (Vidro Fosco / Glassmorphic Blur):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_effects, text="Desfoque:")
        lbl_blur.pack(anchor="w", padx=14, pady=(4, 2))

        if ctk:
            self.slider_blur = ctk.CTkSlider(box_effects, from_=0, to=20, number_of_steps=20, command=self.on_blur_slider_change, progress_color=self.theme["accent_color"])
            self.slider_blur.set(self.config.get("wallpaper_blur", 0))
            self.slider_blur.pack(fill="x", padx=14, pady=(0, 10))

        lbl_dim = ctk.CTkLabel(box_effects, text="Nível de Escurecimento (Para contraste dos textos):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_effects, text="Escurecimento:")
        lbl_dim.pack(anchor="w", padx=14, pady=(4, 2))

        if ctk:
            self.slider_dim = ctk.CTkSlider(box_effects, from_=0.0, to=0.85, command=self.on_dim_slider_change, progress_color=self.theme["accent_color"])
            self.slider_dim.set(self.config.get("wallpaper_dim", 0.35))
            self.slider_dim.pack(fill="x", padx=14, pady=(0, 10))

        lbl_alpha = ctk.CTkLabel(box_effects, text="Opacidade Geral da Janela (Ver o Desktop Através do App):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_effects, text="Opacidade:")
        lbl_alpha.pack(anchor="w", padx=14, pady=(4, 2))

        if ctk:
            self.slider_alpha = ctk.CTkSlider(box_effects, from_=0.60, to=1.0, command=self.on_alpha_slider_change, progress_color=self.theme["accent_color"])
            self.slider_alpha.set(self.config.get("window_alpha", 1.0))
            self.slider_alpha.pack(fill="x", padx=14, pady=(0, 14))

        return page

    def on_transparency_mode_change(self, val):
        rev_map = {"🌟 100% Transparente": "transparent", "🪟 Vidro Translúcido": "glass", "⬛ Sólido Tradicional": "solid"}
        mode = rev_map.get(val, "transparent")
        self.config["transparency_mode"] = mode
        self.save_config()
        self.mode_badge.configure(text=f"FUNDO: {val[:12]} [OK]")
        self.refresh_all_ui()

    def on_blur_slider_change(self, val):
        blur_int = int(float(val))
        self.wallpaper_mgr.set_blur_level(blur_int)
        self.config["wallpaper_blur"] = blur_int
        self.save_config()
        self.render_background()

    def on_dim_slider_change(self, val):
        val_float = float(val)
        self.wallpaper_mgr.set_dim_level(val_float)
        self.config["wallpaper_dim"] = val_float
        self.save_config()
        self.render_background()

    def on_alpha_slider_change(self, val):
        alpha_val = float(val)
        self.config["window_alpha"] = alpha_val
        self.save_config()
        try:
            self.root.attributes("-alpha", alpha_val)
        except Exception:
            pass

    def select_wallpaper_file(self):
        file_path = filedialog.askopenfilename(
            title="Escolha sua Imagem do Computador",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            ok, msg = self.wallpaper_mgr.set_wallpaper(
                file_path, 
                self.config.get("wallpaper_dim", 0.35),
                self.config.get("wallpaper_blur", 0)
            )
            if ok:
                self.config["wallpaper_path"] = file_path
                self.save_config()
                self.lbl_wp_path.configure(text=f"Arquivo atual: {os.path.basename(file_path)}")
                self.render_background()
                messagebox.showinfo("Sucesso", "Imagem aplicada com sucesso ao fundo do programa!")
            else:
                messagebox.showerror("Erro", msg)

    def clear_wallpaper(self):
        self.wallpaper_mgr.set_wallpaper(None)
        self.config["wallpaper_path"] = None
        self.save_config()
        self.lbl_wp_path.configure(text="Arquivo atual: Nenhum (usando cor do tema)")
        self.bg_label.configure(image="")
        self.bg_label.image = None
        self.bg_label.configure(bg=self.theme["bg_color"])
        messagebox.showinfo("Wallpaper", "Fundo restaurado para a cor original do tema.")

    def on_window_resize(self, event):
        now = time.time()
        if now - self.last_resize_time > 0.12:
            self.last_resize_time = now
            self.render_background()

    def render_background(self):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if w < 50 or h < 50:
            return

        photo = self.wallpaper_mgr.get_rendered_image(w, h)
        if photo:
            self.bg_label.configure(image=photo)
            self.bg_label.image = photo
        else:
            self.bg_label.configure(image="")
            self.bg_label.image = None
            self.bg_label.configure(bg=self.theme["bg_color"])

    # ==========================
    # ABA 6: INSTALADOR DE ATALHO & EXECUTÁVEL
    # ==========================
    def create_installer_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        head_box = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        head_box.pack(fill="x", pady=(2, 10))

        title = ctk.CTkLabel(
            head_box, 
            text="🚀 ATALHOS NO SISTEMA & EXECUTÁVEL .EXE", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color=self.theme["text_color"]
        ) if ctk else tk.Label(head_box, text="ATALHOS & EXECUTÁVEL", font=("Arial", 18, "bold"), fg=self.theme["text_color"])
        title.pack(side="left")

        tag_in = ctk.CTkLabel(
            head_box,
            text="[ WINDOWS INTEGRATION ]",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(head_box, text="[ WINDOWS ]", fg=self.theme["accent_color"])
        tag_in.pack(side="right", padx=6)

        card_shortcut = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        card_shortcut.pack(fill="x", pady=6)

        lbl_s_title = ctk.CTkLabel(card_shortcut, text="🖥️ Criar Atalho Gamer na Área de Trabalho", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(card_shortcut, text="Atalho no Desktop:")
        lbl_s_title.pack(anchor="w", padx=14, pady=(12, 4))

        lbl_s_desc = ctk.CTkLabel(
            card_shortcut, 
            text="Instala o atalho oficial com o novo ícone Gamer na Área de Trabalho e no Menu Iniciar do Windows.",
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(card_shortcut, text="Cria atalho no desktop.", fg=self.theme["subtext_color"])
        lbl_s_desc.pack(anchor="w", padx=14, pady=(0, 10))

        btn_install_shortcut = ctk.CTkButton(
            card_shortcut, 
            text="✨ Instalar Atalho Agora", 
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#000000" if self.current_theme_name.startswith("Cyberpunk") or self.current_theme_name.startswith("Razer") else "#ffffff",
            command=self.run_install_shortcut
        ) if ctk else tk.Button(card_shortcut, text="Instalar Atalho Agora", command=self.run_install_shortcut)
        btn_install_shortcut.pack(anchor="w", padx=14, pady=(0, 14))

        card_exe = ctk.CTkFrame(
            page, 
            fg_color=self.get_card_color(), 
            corner_radius=10,
            border_width=2,
            border_color=self.theme["border_color"]
        ) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        card_exe.pack(fill="x", pady=6)

        lbl_e_title = ctk.CTkLabel(card_exe, text="📦 Compilar Executável Portátil (.EXE)", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(card_exe, text="Gerar .EXE:")
        lbl_e_title.pack(anchor="w", padx=14, pady=(12, 4))

        lbl_e_desc = ctk.CTkLabel(
            card_exe, 
            text="Para gerar o arquivo VideoMusicStudio.exe independente com o novo ícone gamer,\nexecute o arquivo 'gerar_executavel.bat' localizado na pasta do programa.",
            text_color=self.theme["subtext_color"],
            justify="left"
        ) if ctk else tk.Label(card_exe, text="Execute gerar_executavel.bat", fg=self.theme["subtext_color"])
        lbl_e_desc.pack(anchor="w", padx=14, pady=(0, 10))

        btn_open_folder = ctk.CTkButton(
            card_exe, 
            text="📁 Abrir Pasta do Programa no Windows Explorer", 
            fg_color=self.get_card_hover_color(),
            text_color=self.theme["text_color"],
            hover_color=self.theme["accent_color"],
            command=self.open_program_folder
        ) if ctk else tk.Button(card_exe, text="Abrir Pasta", command=self.open_program_folder)
        btn_open_folder.pack(anchor="w", padx=14, pady=(0, 14))

        return page

    def run_install_shortcut(self):
        try:
            from setup_shortcut import install_shortcuts
            install_shortcuts()
            messagebox.showinfo("Sucesso!", "Atalho Gamer instalado com sucesso na sua Área de Trabalho e no Menu Iniciar!")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar o atalho: {e}")

    def open_program_folder(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ==========================
    # ATUALIZAÇÃO DINÂMICA DE TEMA & UI
    # ==========================
    def apply_theme(self, theme_name, initial=False):
        self.theme = self.theme_mgr.get_theme(theme_name)
        self.current_theme_name = theme_name
        self.config["theme"] = theme_name
        if not initial:
            self.save_config()

        # Atualizar elementos principais
        if not self.wallpaper_mgr.current_wallpaper_path:
            self.bg_label.configure(bg=self.theme["bg_color"])

        if hasattr(self, "topbar") and ctk:
            self.topbar.configure(fg_color=self.get_sidebar_color())

        if hasattr(self, "rgb_line") and ctk:
            self.rgb_line.configure(fg_color=self.theme["accent_color"])

        if hasattr(self, "lbl_gamer_title") and ctk:
            self.lbl_gamer_title.configure(text_color=self.theme["accent_color"])

        if hasattr(self, "hud_badge_audio") and ctk:
            self.hud_badge_audio.configure(text_color=self.theme["accent_color"])

        if hasattr(self, "theme_badge"):
            self.theme_badge.configure(text=f"CHROMA: {theme_name[:15]}")

        if hasattr(self, "logo_label") and ctk:
            self.logo_label.configure(text_color=self.theme["accent_color"])

        if hasattr(self, "sidebar") and ctk:
            self.sidebar.configure(
                fg_color=self.get_sidebar_color(),
                border_color=self.theme["border_color"]
            )

        if hasattr(self, "nav_widgets"):
            for key, btn in self.nav_widgets.items():
                if ctk:
                    btn.configure(
                        text_color=self.theme["text_color"],
                        hover_color=self.get_card_hover_color()
                    )

        self.render_background()

        if not initial:
            self.refresh_all_ui()

    def refresh_all_ui(self):
        """Reconstrói as páginas com os novos estilos e cores de forma transparente e fluida."""
        current_active = "downloader"
        for name, frame in self.pages.items():
            if frame.winfo_ismapped():
                current_active = name
                break

        for frame in self.pages.values():
            frame.destroy()

        self.pages.clear()
        self.pages["downloader"] = self.create_downloader_page()
        self.pages["iptv"] = self.create_iptv_page()
        self.pages["player"] = self.create_player_page()
        self.pages["themes"] = self.create_themes_page()
        self.pages["wallpaper"] = self.create_wallpaper_page()
        self.pages["installer"] = self.create_installer_page()

        self.show_page(current_active)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VideoMusicApp()
    app.run()
