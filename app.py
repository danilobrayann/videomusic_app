import os
import sys
import json
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser

# Auto-verificação de dependências
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    ctk = None
    PYGAME_AVAILABLE = False

from theme_manager import ThemeManager, CONFIG_PATH
from wallpaper_manager import WallpaperManager

class VideoMusicApp:
    def __init__(self):
        self.theme_mgr = ThemeManager()
        self.wallpaper_mgr = WallpaperManager()
        
        # Carregar configurações
        self.config = self.load_config()
        self.current_theme_name = self.config.get("theme", "Laranje (Vencord Style)")
        self.theme = self.theme_mgr.get_theme(self.current_theme_name)
        
        # Configurar Pygame Mixer para reprodução de áudio
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Aviso no mixer: {e}")

        # Configurar Janela Principal
        if ctk:
            ctk.set_appearance_mode("Dark")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("VideoMusic Studio - Player, Downloader & Custom Themes")
        self.root.geometry("1020x680")
        self.root.minsize(850, 580)
        
        # Ícone da janela
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Estado da reprodução
        self.playlist = []
        self.current_track_idx = -1
        self.is_playing = False
        self.is_paused = False

        # Configurar Wallpaper
        saved_wp = self.config.get("wallpaper_path")
        saved_dim = self.config.get("wallpaper_dim", 0.45)
        if saved_wp and os.path.exists(saved_wp):
            self.wallpaper_mgr.set_wallpaper(saved_wp, saved_dim)

        self.setup_ui()
        self.apply_theme(self.current_theme_name, initial=True)

        # Vincular redimensionamento para wallpaper responsivo
        self.root.bind("<Configure>", self.on_window_resize)
        self.last_resize_time = 0

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "theme": "Laranje (Vencord Style)",
            "wallpaper_path": None,
            "wallpaper_dim": 0.45,
            "download_dir": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
        }

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")

    def setup_ui(self):
        # 1. Camada de Fundo (Wallpaper)
        self.bg_label = tk.Label(self.root, bg=self.theme["bg_color"])
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # 2. Container Principal
        self.main_container = ctk.CTkFrame(self.root, corner_radius=14, fg_color=self.theme["card_color"]) if ctk else tk.Frame(self.root, bg=self.theme["card_color"])
        self.main_container.pack(fill="both", expand=True, padx=14, pady=14)

        # Grid: Sidebar (coluna 0) e Área de Conteúdo (coluna 1)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # 3. Sidebar (Menu Lateral)
        self.create_sidebar()

        # 4. Área de Conteúdo Dinâmico (Tabs)
        self.content_area = ctk.CTkFrame(self.main_container, corner_radius=10, fg_color="transparent") if ctk else tk.Frame(self.main_container, bg=self.theme["card_color"])
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Telas / Abas
        self.pages = {}
        self.pages["downloader"] = self.create_downloader_page()
        self.pages["player"] = self.create_player_page()
        self.pages["themes"] = self.create_themes_page()
        self.pages["wallpaper"] = self.create_wallpaper_page()
        self.pages["installer"] = self.create_installer_page()

        # Abrir na tela Downloader inicialmente
        self.show_page("downloader")

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self.main_container, width=220, corner_radius=10, fg_color=self.theme["sidebar_color"]) if ctk else tk.Frame(self.main_container, width=220, bg=self.theme["sidebar_color"])
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.sidebar.grid_propagate(False)

        # Título / Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="🎵 VideoMusic\nSTUDIO", 
            font=ctk.CTkFont(size=20, weight="bold") if ctk else ("Arial", 18, "bold"),
            text_color=self.theme["accent_color"]
        ) if ctk else tk.Label(self.sidebar, text="🎵 VideoMusic\nSTUDIO", font=("Arial", 16, "bold"), fg=self.theme["accent_color"], bg=self.theme["sidebar_color"])
        self.logo_label.pack(pady=(22, 20))

        # Botões de Navegação
        nav_buttons = [
            ("📥 Baixar Mídia", "downloader"),
            ("▶️ Player de Música", "player"),
            ("🎨 Personalizar Temas", "themes"),
            ("🖼️ Papel de Parede", "wallpaper"),
            ("🚀 Instalador / Atalhos", "installer"),
        ]

        self.nav_widgets = {}
        for text, key in nav_buttons:
            if ctk:
                btn = ctk.CTkButton(
                    self.sidebar,
                    text=text,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    height=42,
                    anchor="w",
                    fg_color="transparent",
                    text_color=self.theme["text_color"],
                    hover_color=self.theme["card_hover"],
                    command=lambda k=key: self.show_page(k)
                )
            else:
                btn = tk.Button(
                    self.sidebar,
                    text=text,
                    font=("Arial", 11, "bold"),
                    anchor="w",
                    relief="flat",
                    bg=self.theme["sidebar_color"],
                    fg=self.theme["text_color"],
                    command=lambda k=key: self.show_page(k)
                )
            btn.pack(fill="x", padx=12, pady=6)
            self.nav_widgets[key] = btn

        # Rodapé da Sidebar
        self.theme_badge = ctk.CTkLabel(
            self.sidebar,
            text=f"Tema: {self.current_theme_name}",
            font=ctk.CTkFont(size=11),
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(self.sidebar, text=f"Tema: {self.current_theme_name}", font=("Arial", 9), fg=self.theme["subtext_color"], bg=self.theme["sidebar_color"])
        self.theme_badge.pack(side="bottom", pady=15)

    def show_page(self, page_name):
        for name, frame in self.pages.items():
            frame.grid_forget()
            if ctk and name in self.nav_widgets:
                self.nav_widgets[name].configure(fg_color="transparent")

        if page_name in self.pages:
            self.pages[page_name].grid(row=0, column=0, sticky="nsew")
            if ctk and page_name in self.nav_widgets:
                self.nav_widgets[page_name].configure(fg_color=self.theme["accent_color"])

    # ==========================
    # ABA 1: DOWNLOADER (yt-dlp)
    # ==========================
    def create_downloader_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])
        
        # Cabeçalho
        title = ctk.CTkLabel(page, text="Baixar Vídeos e Músicas", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(page, text="Baixar Vídeos e Músicas", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(anchor="w", pady=(5, 15))

        # URL Input
        url_frame = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        url_frame.pack(fill="x", pady=6)

        lbl_url = ctk.CTkLabel(url_frame, text="Cole o Link (YouTube, SoundCloud, Vídeo Web):", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(url_frame, text="Link do Vídeo:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_url.pack(anchor="w", padx=12, pady=(10, 4))

        self.entry_url = ctk.CTkEntry(url_frame, placeholder_text="https://www.youtube.com/watch?v=...", height=38, font=ctk.CTkFont(size=13)) if ctk else tk.Entry(url_frame, font=("Arial", 12))
        self.entry_url.pack(fill="x", padx=12, pady=(0, 12))

        # Opções de Formato e Resolução
        opts_frame = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        opts_frame.pack(fill="x", pady=8)

        lbl_fmt = ctk.CTkLabel(opts_frame, text="Formato de Download:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(opts_frame, text="Formato:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_fmt.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.format_var = tk.StringVar(value="MP3 (Áudio - 320kbps)")
        formats = ["MP3 (Áudio - 320kbps)", "MP4 (Melhor Qualidade de Vídeo)", "MP4 (720p Leve)", "WAV (Áudio Sem Compressão)"]
        if ctk:
            self.combo_format = ctk.CTkComboBox(opts_frame, values=formats, variable=self.format_var, width=280)
            self.combo_format.grid(row=0, column=1, padx=12, pady=10, sticky="w")
        else:
            self.combo_format = tk.OptionMenu(opts_frame, self.format_var, *formats)
            self.combo_format.grid(row=0, column=1, padx=12, pady=10, sticky="w")

        # Pasta de Destino
        lbl_dest = ctk.CTkLabel(opts_frame, text="Salvar em:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(opts_frame, text="Salvar em:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_dest.grid(row=1, column=0, padx=12, pady=10, sticky="w")

        self.lbl_path = ctk.CTkLabel(opts_frame, text=self.config.get("download_dir"), text_color=self.theme["subtext_color"]) if ctk else tk.Label(opts_frame, text=self.config.get("download_dir"), fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        self.lbl_path.grid(row=1, column=1, padx=12, pady=10, sticky="w")

        btn_choose_dir = ctk.CTkButton(opts_frame, text="Escolher Pasta", width=120, command=self.choose_download_dir, fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"]) if ctk else tk.Button(opts_frame, text="Escolher Pasta", command=self.choose_download_dir)
        btn_choose_dir.grid(row=1, column=2, padx=12, pady=10)

        # Botão Iniciar Download
        self.btn_download = ctk.CTkButton(
            page, 
            text="⚡ BAIXAR AGORA", 
            height=46, 
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            command=self.start_download
        ) if ctk else tk.Button(page, text="⚡ BAIXAR AGORA", font=("Arial", 14, "bold"), bg=self.theme["accent_color"], command=self.start_download)
        self.btn_download.pack(fill="x", pady=15)

        # Barra de Progresso e Status
        self.lbl_status = ctk.CTkLabel(page, text="Pronto para baixar.", text_color=self.theme["subtext_color"]) if ctk else tk.Label(page, text="Pronto para baixar.", fg=self.theme["subtext_color"], bg=self.theme["card_color"])
        self.lbl_status.pack(pady=4)

        if ctk:
            self.progress_bar = ctk.CTkProgressBar(page)
            self.progress_bar.set(0.0)
            self.progress_bar.pack(fill="x", pady=6)
        
        return page

    def choose_download_dir(self):
        folder = filedialog.askdirectory(initialdir=self.config.get("download_dir"))
        if folder:
            self.config["download_dir"] = folder
            self.save_config()
            self.lbl_path.configure(text=folder)

    def start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Por favor, insira um link para baixar.")
            return

        fmt = self.format_var.get()
        out_dir = self.config.get("download_dir", os.path.expanduser("~"))

        self.btn_download.configure(state="disabled")
        self.lbl_status.configure(text="Iniciando download...")
        if ctk:
            self.progress_bar.set(0.1)

        # Executar download em thread separada para não travar a interface
        threading.Thread(target=self._download_worker, args=(url, fmt, out_dir), daemon=True).start()

    def _download_worker(self, url, fmt, out_dir):
        try:
            import yt_dlp
        except ImportError:
            self.root.after(0, lambda: messagebox.showerror("Erro", "A biblioteca 'yt-dlp' não está instalada. Execute 'pip install yt-dlp' ou use o instalador."))
            self.root.after(0, lambda: self.btn_download.configure(state="normal"))
            return

        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                    downloaded = d.get('downloaded_bytes', 0)
                    pct = downloaded / total
                    speed = d.get('speed', 0) or 0
                    speed_mb = speed / (1024 * 1024)
                    status_text = f"Baixando: {pct*100:.1f}% ({speed_mb:.2f} MB/s)"
                    self.root.after(0, lambda: self.lbl_status.configure(text=status_text))
                    if ctk:
                        self.root.after(0, lambda: self.progress_bar.set(pct))
                except Exception:
                    pass
            elif d['status'] == 'finished':
                self.root.after(0, lambda: self.lbl_status.configure(text="Convertendo formato final..."))

        ydl_opts = {
            'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
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
                title = info.get('title', 'Mídia')
                self.root.after(0, lambda: self._on_download_success(title))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_download_error(err_msg))

    def _on_download_success(self, title):
        self.lbl_status.configure(text=f"✅ Concluído: {title[:40]}...")
        if ctk:
            self.progress_bar.set(1.0)
        self.btn_download.configure(state="normal")
        messagebox.showinfo("Sucesso", f"Download concluído com sucesso:\n{title}")

    def _on_download_error(self, err_msg):
        self.lbl_status.configure(text="❌ Erro durante o download.")
        self.btn_download.configure(state="normal")
        messagebox.showerror("Erro de Download", f"Não foi possível baixar:\n{err_msg}")

    # ==========================
    # ABA 2: PLAYER DE MÚSICA
    # ==========================
    def create_player_page(self):
        page = ctk.CTkFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        title = ctk.CTkLabel(page, text="Player de Áudio & Vídeo", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(page, text="Player de Áudio & Vídeo", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(anchor="w", pady=(5, 12))

        # Painel da Música Atual
        now_playing_box = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=12) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        now_playing_box.pack(fill="x", pady=8, padx=5)

        self.lbl_track_title = ctk.CTkLabel(now_playing_box, text="Nenhuma música selecionada", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.theme["accent_color"]) if ctk else tk.Label(now_playing_box, text="Nenhuma música selecionada", font=("Arial", 14, "bold"), fg=self.theme["accent_color"], bg=self.theme["card_hover"])
        self.lbl_track_title.pack(pady=(15, 6))

        # Controles de Reprodução
        controls_frame = ctk.CTkFrame(now_playing_box, fg_color="transparent") if ctk else tk.Frame(now_playing_box, bg=self.theme["card_hover"])
        controls_frame.pack(pady=(6, 15))

        btn_prev = ctk.CTkButton(controls_frame, text="⏮️", width=50, height=40, font=ctk.CTkFont(size=16), fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.play_prev_track) if ctk else tk.Button(controls_frame, text="⏮️", command=self.play_prev_track)
        btn_prev.pack(side="left", padx=8)

        self.btn_play_pause = ctk.CTkButton(controls_frame, text="▶️ Tocar", width=110, height=40, font=ctk.CTkFont(size=15, weight="bold"), fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.toggle_play_pause) if ctk else tk.Button(controls_frame, text="▶️ Tocar", command=self.toggle_play_pause)
        self.btn_play_pause.pack(side="left", padx=8)

        btn_stop = ctk.CTkButton(controls_frame, text="⏹️", width=50, height=40, font=ctk.CTkFont(size=16), fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.stop_playback) if ctk else tk.Button(controls_frame, text="⏹️", command=self.stop_playback)
        btn_stop.pack(side="left", padx=8)

        btn_next = ctk.CTkButton(controls_frame, text="⏭️", width=50, height=40, font=ctk.CTkFont(size=16), fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.play_next_track) if ctk else tk.Button(controls_frame, text="⏭️", command=self.play_next_track)
        btn_next.pack(side="left", padx=8)

        # Volume Slider
        vol_frame = ctk.CTkFrame(now_playing_box, fg_color="transparent") if ctk else tk.Frame(now_playing_box, bg=self.theme["card_hover"])
        vol_frame.pack(fill="x", padx=30, pady=(0, 12))

        lbl_vol = ctk.CTkLabel(vol_frame, text="Volume: 🔊", font=ctk.CTkFont(size=12), text_color=self.theme["subtext_color"]) if ctk else tk.Label(vol_frame, text="Volume:", fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        lbl_vol.pack(side="left", padx=6)

        if ctk:
            self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=1, command=self.set_volume)
            self.vol_slider.set(0.7)
            self.vol_slider.pack(side="left", fill="x", expand=True, padx=8)

        # Lista de Músicas (Playlist)
        playlist_header = ctk.CTkFrame(page, fg_color="transparent") if ctk else tk.Frame(page, bg=self.theme["card_color"])
        playlist_header.pack(fill="x", pady=(10, 4))

        lbl_pl = ctk.CTkLabel(playlist_header, text="Fila de Reprodução:", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(playlist_header, text="Fila de Reprodução:", fg=self.theme["text_color"], bg=self.theme["card_color"])
        lbl_pl.pack(side="left")

        btn_add_files = ctk.CTkButton(playlist_header, text="➕ Adicionar Músicas / Vídeos", width=190, fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.add_media_files) if ctk else tk.Button(playlist_header, text="➕ Adicionar Arquivos", command=self.add_media_files)
        btn_add_files.pack(side="right")

        # Listbox de arquivos
        self.media_listbox = tk.Listbox(
            page,
            bg=self.theme["card_hover"],
            fg=self.theme["text_color"],
            selectbackground=self.theme["accent_color"],
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=0,
            font=("Arial", 11)
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
            messagebox.showwarning("Aviso", "Pygame não está instalado. Não é possível reproduzir som.")
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

        # Se for arquivo de vídeo, pode ser aberto no player nativo do Windows
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
    # ABA 3: TEMAS E PERSONALIZAÇÃO
    # ==========================
    def create_themes_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        title = ctk.CTkLabel(page, text="Gerenciador de Temas & Cores", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(page, text="Gerenciador de Temas", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(anchor="w", pady=(5, 12))

        # Seção 1: Escolher Tema Existente
        box_presets = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_presets.pack(fill="x", pady=8)

        lbl_preset = ctk.CTkLabel(box_presets, text="Temas Pré-definidos & Salvos:", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_presets, text="Temas Prontos:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
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
                width=260,
                command=self.on_theme_select
            )
            self.theme_dropdown.pack(side="left", padx=(0, 10))
        else:
            self.theme_dropdown = tk.OptionMenu(preset_row, self.theme_dropdown_var, *theme_names, command=self.on_theme_select)
            self.theme_dropdown.pack(side="left", padx=(0, 10))

        # Importar do PC / Exportar
        btn_import_theme = ctk.CTkButton(preset_row, text="📂 Importar Tema do PC (.json / .css)", fg_color=self.theme["accent_color"], hover_color=self.theme["accent_hover"], command=self.import_theme_file) if ctk else tk.Button(preset_row, text="📂 Importar do PC", command=self.import_theme_file)
        btn_import_theme.pack(side="left", padx=6)

        btn_export_theme = ctk.CTkButton(preset_row, text="💾 Exportar Tema", width=120, fg_color=self.theme["card_color"], hover_color=self.theme["card_hover"], command=self.export_current_theme) if ctk else tk.Button(preset_row, text="💾 Exportar", command=self.export_current_theme)
        btn_export_theme.pack(side="left", padx=6)

        # Seção 2: Criar / Personalizar Tema Livremente com Seletor de Cores
        box_custom = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_custom.pack(fill="x", pady=10)

        lbl_custom_title = ctk.CTkLabel(box_custom, text="Personalizar Cores do Tema Livremente:", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(box_custom, text="Crie suas próprias cores:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_custom_title.pack(anchor="w", padx=14, pady=(12, 8))

        # Paleta em edição temporária
        self.editing_theme = dict(self.theme)

        colors_grid = ctk.CTkFrame(box_custom, fg_color="transparent") if ctk else tk.Frame(box_custom, bg=self.theme["card_hover"])
        colors_grid.pack(fill="x", padx=14, pady=6)

        color_options = [
            ("Cor de Destaque / Botões (Accent)", "accent_color"),
            ("Cor de Fundo da Janela (Background)", "bg_color"),
            ("Cor do Menu Lateral (Sidebar)", "sidebar_color"),
            ("Cor dos Cartões / Painéis (Card)", "card_color"),
            ("Cor do Texto Principal", "text_color"),
        ]

        self.color_preview_buttons = {}
        for row, (label_text, key) in enumerate(color_options):
            lbl = ctk.CTkLabel(colors_grid, text=label_text, font=ctk.CTkFont(size=12), text_color=self.theme["text_color"]) if ctk else tk.Label(colors_grid, text=label_text, fg=self.theme["text_color"], bg=self.theme["card_hover"])
            lbl.grid(row=row, column=0, sticky="w", pady=6)

            # Botão colorido para escolher cor
            btn_color = ctk.CTkButton(
                colors_grid, 
                text=self.editing_theme.get(key, "#ffffff"),
                width=130,
                fg_color=self.editing_theme.get(key, "#ffffff"),
                text_color="#000000" if key == "accent_color" or key == "text_color" else "#ffffff",
                command=lambda k=key: self.pick_color_for_key(k)
            ) if ctk else tk.Button(colors_grid, text=self.editing_theme.get(key, "#ffffff"), bg=self.editing_theme.get(key, "#ffffff"), command=lambda k=key: self.pick_color_for_key(k))
            btn_color.grid(row=row, column=1, padx=20, pady=6)
            self.color_preview_buttons[key] = btn_color

        # Nome do novo tema e botão Salvar
        save_row = ctk.CTkFrame(box_custom, fg_color="transparent") if ctk else tk.Frame(box_custom, bg=self.theme["card_hover"])
        save_row.pack(fill="x", padx=14, pady=(12, 16))

        lbl_name = ctk.CTkLabel(save_row, text="Nome do seu Tema:", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(save_row, text="Nome do Tema:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_name.pack(side="left", padx=(0, 10))

        self.entry_theme_name = ctk.CTkEntry(save_row, placeholder_text="Ex: Meu Tema Laranja Neon", width=250) if ctk else tk.Entry(save_row)
        self.entry_theme_name.pack(side="left", padx=(0, 12))

        btn_save_theme = ctk.CTkButton(
            save_row, 
            text="✨ Salvar e Aplicar Tema", 
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_custom_theme
        ) if ctk else tk.Button(save_row, text="Salvar e Aplicar", command=self.save_custom_theme)
        btn_save_theme.pack(side="left")

        return page

    def pick_color_for_key(self, key):
        initial = self.editing_theme.get(key, "#ffffff")
        chosen_color = colorchooser.askcolor(color=initial, title=f"Escolha a {key}")
        if chosen_color and chosen_color[1]:
            hex_val = chosen_color[1]
            self.editing_theme[key] = hex_val
            if key == "accent_color":
                self.editing_theme["accent_hover"] = self.theme_mgr._adjust_brightness(hex_val, 1.2)
                self.editing_theme["border_color"] = hex_val
            elif key == "card_color":
                self.editing_theme["card_hover"] = self.theme_mgr._adjust_brightness(hex_val, 1.25)
            
            # Atualiza botão de amostra
            if key in self.color_preview_buttons:
                btn = self.color_preview_buttons[key]
                if ctk:
                    btn.configure(fg_color=hex_val, text=hex_val)
                else:
                    btn.configure(bg=hex_val, text=hex_val)

    def save_custom_theme(self):
        name = self.entry_theme_name.get().strip()
        if not name:
            name = f"Personalizado {int(time.time()) % 1000}"
        
        self.editing_theme["name"] = name
        saved_name = self.theme_mgr.save_custom_theme(dict(self.editing_theme))
        
        # Atualiza dropdown
        theme_names = self.theme_mgr.get_all_theme_names()
        if ctk:
            self.theme_dropdown.configure(values=theme_names)
            self.theme_dropdown_var.set(saved_name)
        
        self.apply_theme(saved_name)
        messagebox.showinfo("Tema Salvo", f"O tema '{saved_name}' foi criado e aplicado com sucesso!")

    def on_theme_select(self, theme_name):
        self.apply_theme(theme_name)

    def import_theme_file(self):
        file_path = filedialog.askopenfilename(
            title="Importar Tema do PC",
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
                messagebox.showinfo("Sucesso", f"Tema importado com sucesso: '{theme_name}'!")
            except Exception as e:
                messagebox.showerror("Erro na Importação", f"Não foi possível importar tema:\n{e}")

    def export_current_theme(self):
        target_path = filedialog.asksaveasfilename(
            title="Exportar Tema Atual",
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
    # ABA 4: PAPEL DE PAREDE (WALLPAPER)
    # ==========================
    def create_wallpaper_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        title = ctk.CTkLabel(page, text="Papel de Parede (Wallpaper)", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(page, text="Papel de Parede", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(anchor="w", pady=(5, 12))

        box_wp = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        box_wp.pack(fill="x", pady=8)

        lbl_desc = ctk.CTkLabel(
            box_wp, 
            text="Adicione qualquer imagem do seu computador como fundo do aplicativo.\nVocê pode ajustar o nível de escurecimento para deixar os botões bem visíveis.",
            justify="left",
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(box_wp, text="Escolha uma imagem de fundo:", fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        lbl_desc.pack(anchor="w", padx=14, pady=(12, 10))

        # Botões de Ação do Wallpaper
        btn_row = ctk.CTkFrame(box_wp, fg_color="transparent") if ctk else tk.Frame(box_wp, bg=self.theme["card_hover"])
        btn_row.pack(fill="x", padx=14, pady=6)

        btn_select_wp = ctk.CTkButton(
            btn_row, 
            text="🖼️ Escolher Imagem do PC...", 
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.select_wallpaper_file
        ) if ctk else tk.Button(btn_row, text="🖼️ Escolher Imagem...", command=self.select_wallpaper_file)
        btn_select_wp.pack(side="left", padx=(0, 10))

        btn_clear_wp = ctk.CTkButton(
            btn_row, 
            text="❌ Remover Wallpaper", 
            fg_color=self.theme["card_color"],
            hover_color=self.theme["card_hover"],
            command=self.clear_wallpaper
        ) if ctk else tk.Button(btn_row, text="Remover Wallpaper", command=self.clear_wallpaper)
        btn_clear_wp.pack(side="left")

        # Caminho da imagem atual
        self.lbl_wp_path = ctk.CTkLabel(
            box_wp, 
            text=f"Arquivo atual: {self.config.get('wallpaper_path') or 'Nenhum'}", 
            text_color=self.theme["subtext_color"],
            anchor="w"
        ) if ctk else tk.Label(box_wp, text="Nenhum", fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        self.lbl_wp_path.pack(anchor="w", padx=14, pady=(10, 6))

        # Slider de Escurecimento (Dimming)
        dim_box = ctk.CTkFrame(box_wp, fg_color="transparent") if ctk else tk.Frame(box_wp, bg=self.theme["card_hover"])
        dim_box.pack(fill="x", padx=14, pady=(10, 16))

        lbl_dim = ctk.CTkLabel(dim_box, text="Nível de Escurecimento do Fundo (Para nitidez dos textos):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(dim_box, text="Escurecimento:", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_dim.pack(anchor="w", pady=(0, 6))

        if ctk:
            self.slider_dim = ctk.CTkSlider(dim_box, from_=0.0, to=0.85, command=self.on_dim_slider_change)
            self.slider_dim.set(self.config.get("wallpaper_dim", 0.45))
            self.slider_dim.pack(fill="x", pady=4)

        return page

    def select_wallpaper_file(self):
        file_path = filedialog.askopenfilename(
            title="Escolha seu Papel de Parede",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            ok, msg = self.wallpaper_mgr.set_wallpaper(file_path, self.config.get("wallpaper_dim", 0.45))
            if ok:
                self.config["wallpaper_path"] = file_path
                self.save_config()
                self.lbl_wp_path.configure(text=f"Arquivo atual: {file_path}")
                self.render_background()
                messagebox.showinfo("Wallpaper Atualizado", "Papel de parede aplicado com sucesso!")
            else:
                messagebox.showerror("Erro", msg)

    def clear_wallpaper(self):
        self.wallpaper_mgr.set_wallpaper(None)
        self.config["wallpaper_path"] = None
        self.save_config()
        self.lbl_wp_path.configure(text="Arquivo atual: Nenhum")
        self.bg_label.configure(image="")
        self.bg_label.image = None
        self.bg_label.configure(bg=self.theme["bg_color"])
        messagebox.showinfo("Wallpaper", "Papel de parede removido. Fundo restaurado para a cor do tema.")

    def on_dim_slider_change(self, val):
        val_float = float(val)
        self.wallpaper_mgr.set_dim_level(val_float)
        self.config["wallpaper_dim"] = val_float
        self.save_config()
        self.render_background()

    def on_window_resize(self, event):
        # Debounce de redimensionamento
        now = time.time()
        if now - self.last_resize_time > 0.15:
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
    # ABA 5: INSTALADOR DE ATALHO & EXECUTÁVEL
    # ==========================
    def create_installer_page(self):
        page = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent") if ctk else tk.Frame(self.content_area, bg=self.theme["card_color"])

        title = ctk.CTkLabel(page, text="Instalação no Computador & Atalhos", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(page, text="Instalação & Atalhos", font=("Arial", 18, "bold"), fg=self.theme["text_color"], bg=self.theme["card_color"])
        title.pack(anchor="w", pady=(5, 12))

        # Cartão 1: Atalho no Desktop
        card_shortcut = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        card_shortcut.pack(fill="x", pady=8)

        lbl_s_title = ctk.CTkLabel(card_shortcut, text="🖥️ Criar Atalho na Área de Trabalho (Desktop)", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(card_shortcut, text="Atalho na Área de Trabalho", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_s_title.pack(anchor="w", padx=14, pady=(12, 4))

        lbl_s_desc = ctk.CTkLabel(
            card_shortcut, 
            text="Cria um atalho oficial com ícone personalizado na sua Área de Trabalho e no Menu Iniciar do Windows.",
            text_color=self.theme["subtext_color"]
        ) if ctk else tk.Label(card_shortcut, text="Cria atalho no desktop.", fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        lbl_s_desc.pack(anchor="w", padx=14, pady=(0, 10))

        btn_install_shortcut = ctk.CTkButton(
            card_shortcut, 
            text="✨ Instalar Atalho Agora", 
            fg_color=self.theme["accent_color"],
            hover_color=self.theme["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_install_shortcut
        ) if ctk else tk.Button(card_shortcut, text="Instalar Atalho Agora", command=self.run_install_shortcut)
        btn_install_shortcut.pack(anchor="w", padx=14, pady=(0, 14))

        # Cartão 2: Gerar .EXE
        card_exe = ctk.CTkFrame(page, fg_color=self.theme["card_hover"], corner_radius=10) if ctk else tk.Frame(page, bg=self.theme["card_hover"])
        card_exe.pack(fill="x", pady=8)

        lbl_e_title = ctk.CTkLabel(card_exe, text="📦 Gerar Executável Portátil (.EXE)", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.theme["text_color"]) if ctk else tk.Label(card_exe, text="Gerar Executável .EXE", fg=self.theme["text_color"], bg=self.theme["card_hover"])
        lbl_e_title.pack(anchor="w", padx=14, pady=(12, 4))

        lbl_e_desc = ctk.CTkLabel(
            card_exe, 
            text="Deseja transformar o aplicativo em um arquivo VideoMusicStudio.exe independente?\nVocê pode executar o script 'gerar_executavel.bat' localizado na pasta do programa.",
            text_color=self.theme["subtext_color"],
            justify="left"
        ) if ctk else tk.Label(card_exe, text="Gera executável .exe", fg=self.theme["subtext_color"], bg=self.theme["card_hover"])
        lbl_e_desc.pack(anchor="w", padx=14, pady=(0, 10))

        btn_open_folder = ctk.CTkButton(
            card_exe, 
            text="📁 Abrir Pasta do Programa no Windows Explorer", 
            fg_color=self.theme["card_color"],
            hover_color=self.theme["card_hover"],
            command=self.open_program_folder
        ) if ctk else tk.Button(card_exe, text="Abrir Pasta", command=self.open_program_folder)
        btn_open_folder.pack(anchor="w", padx=14, pady=(0, 14))

        return page

    def run_install_shortcut(self):
        try:
            from setup_shortcut import install_shortcuts
            install_shortcuts()
            messagebox.showinfo("Sucesso!", "Atalho instalado com sucesso na sua Área de Trabalho e no Menu Iniciar!")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar o atalho automaticamente: {e}")

    def open_program_folder(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ==========================
    # APLICAÇÃO DE TEMAS DINÂMICOS
    # ==========================
    def apply_theme(self, theme_name, initial=False):
        self.theme = self.theme_mgr.get_theme(theme_name)
        self.current_theme_name = theme_name
        self.config["theme"] = theme_name
        if not initial:
            self.save_config()

        # Atualizar elementos visuais
        if not self.wallpaper_mgr.current_wallpaper_path:
            self.bg_label.configure(bg=self.theme["bg_color"])

        if hasattr(self, "theme_badge"):
            self.theme_badge.configure(text=f"Tema: {theme_name}")

        if hasattr(self, "logo_label") and ctk:
            self.logo_label.configure(text_color=self.theme["accent_color"])

        if hasattr(self, "sidebar") and ctk:
            self.sidebar.configure(fg_color=self.theme["sidebar_color"])

        # Re-renderizar background se houver
        self.render_background()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VideoMusicApp()
    app.run()
