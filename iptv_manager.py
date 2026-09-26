import os
import sys
import json
import re
import shutil
import tempfile
import webbrowser
import subprocess
import threading

# Tentar importar python-vlc para reprodução nativa embutida
try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    vlc = None
    VLC_AVAILABLE = False

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

IPTV_CHANNELS_FILE = os.path.join(APP_DIR, "iptv_channels.json")

# Canais padrão pré-configurados (gratuitos e públicos)
DEFAULT_CHANNELS = [
    {
        "name": "NASA TV (Ciência & Espaço)",
        "url": "https://ntv1.akamaized.net/hls/live/2014075/NASA-NTV1-HLS/master.m3u8",
        "category": "Ciência / Documentários"
    },
    {
        "name": "Red Bull TV (Esportes & Ação)",
        "url": "https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master.m3u8",
        "category": "Esportes & Ação"
    },
    {
        "name": "Euronews Português (Notícias)",
        "url": "https://euronews-euronews-portuguese-1-pt.samsung.wurl.tv/playlist.m3u8",
        "category": "Notícias"
    },
    {
        "name": "TV Brasil (Ao Vivo)",
        "url": "https://tvbrasil-hls.ebc.com.br/hls/tvbrasil.m3u8",
        "category": "Variedades & Cultura"
    },
    {
        "name": "Record News HD (Notícias 24h)",
        "url": "https://stream.recordnews.com.br/hls/recordnews.m3u8",
        "category": "Notícias"
    },
    {
        "name": "SBT Ao Vivo",
        "url": "https://sbt-live.akamaized.net/hls/live/2026723/sbt/master.m3u8",
        "category": "Entretenimento"
    },
    {
        "name": "Al Jazeera English (Global News)",
        "url": "https://live-hls-web-aje.getaj.net/AJE/01.m3u8",
        "category": "Notícias"
    },
    {
        "name": "Anime & Cartoons (Pluto TV)",
        "url": "https://service-stitcher.clusters.pluto.tv/v1/stitch/hls/channel/5dfbcf04071ec20009c95353/master.m3u8",
        "category": "Anime & Desenhos"
    },
    {
        "name": "Lofi Hip Hop Radio (Live YouTube)",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "category": "Música & Relax"
    }
]

class IPTVManager:
    def __init__(self):
        self.channels = []
        self.load_channels()

    def load_channels(self):
        """Carrega a lista de canais do arquivo JSON ou inicializa com os padrões."""
        if os.path.exists(IPTV_CHANNELS_FILE):
            try:
                with open(IPTV_CHANNELS_FILE, "r", encoding="utf-8") as f:
                    self.channels = json.load(f)
                    return
            except Exception as e:
                print(f"Aviso ao ler iptv_channels.json: {e}")
        
        # Padrão
        self.channels = list(DEFAULT_CHANNELS)
        self.save_channels()

    def save_channels(self):
        """Salva os canais no arquivo JSON."""
        try:
            with open(IPTV_CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.channels, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar canais IPTV: {e}")

    def add_channel(self, name, url, category="Geral"):
        name = name.strip() or "Canal Sem Nome"
        url = url.strip()
        if not url:
            return False, "URL não pode estar vazia."
        
        # Verifica duplicata
        for ch in self.channels:
            if ch.get("url") == url:
                ch["name"] = name
                ch["category"] = category
                self.save_channels()
                return True, "Canal atualizado!"

        self.channels.append({
            "name": name,
            "url": url,
            "category": category
        })
        self.save_channels()
        return True, "Canal adicionado com sucesso!"

    def remove_channel(self, index):
        if 0 <= index < len(self.channels):
            removed = self.channels.pop(index)
            self.save_channels()
            return True, f"Canal '{removed.get('name')}' removido."
        return False, "Índice inválido."

    def import_m3u_file(self, filepath):
        """Faz a importação de uma lista IPTV em formato M3U ou M3U8."""
        if not os.path.exists(filepath):
            return 0, "Arquivo não encontrado."

        imported_count = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            current_name = None
            current_category = "Importados"

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("#EXTINF"):
                    # Extrair categoria se houver group-title
                    group_match = re.search(r'group-title="([^"]+)"', line, re.IGNORECASE)
                    if group_match:
                        current_category = group_match.group(1)
                    else:
                        current_category = "Importados"

                    # Extrair nome do canal (após a última vírgula)
                    parts = line.split(",", 1)
                    if len(parts) > 1:
                        current_name = parts[1].strip()
                    else:
                        current_name = "Canal Importado"

                elif not line.startswith("#"):
                    # Linha de URL
                    url = line
                    name = current_name or f"Canal {len(self.channels) + 1}"
                    # Evita duplicatas exatas de URL
                    if not any(c.get("url") == url for c in self.channels):
                        self.channels.append({
                            "name": name,
                            "url": url,
                            "category": current_category
                        })
                        imported_count += 1
                    current_name = None

            self.save_channels()
            return imported_count, f"{imported_count} canais importados com sucesso!"
        except Exception as e:
            return 0, f"Erro ao ler lista M3U: {e}"

    def export_m3u_file(self, filepath):
        """Exporta os canais salvos para um arquivo M3U padrão."""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in self.channels:
                    name = ch.get("name", "Canal")
                    cat = ch.get("category", "Geral")
                    url = ch.get("url", "")
                    f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n')
                    f.write(f'{url}\n')
            return True, f"Lista salva em: {filepath}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_youtube_or_twitch(url):
        return any(domain in url.lower() for domain in ["youtube.com", "youtu.be", "twitch.tv"])

    @staticmethod
    def resolve_live_stream_url(url):
        """
        Se a URL for do YouTube ou Twitch, utiliza o yt-dlp para extrair a URL HLS (.m3u8) direta.
        Caso contrário, retorna a URL original.
        """
        if not IPTVManager.is_youtube_or_twitch(url):
            return url

        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best[protocol^=m3u8]/best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # Tenta obter stream hls direta
                stream_url = info.get("url")
                if not stream_url and "formats" in info:
                    for f in reversed(info["formats"]):
                        if f.get("url"):
                            stream_url = f["url"]
                            break
                if stream_url:
                    return stream_url
        except Exception as e:
            print(f"Aviso ao resolver URL com yt-dlp: {e}")

        return url

    @staticmethod
    def get_vlc_path():
        """Procura o executável do VLC no sistema Windows."""
        candidates = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "VideoLAN", "VLC", "vlc.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "VideoLAN", "VLC", "vlc.exe"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        
        # Procurar no PATH
        vlc_in_path = shutil.which("vlc")
        if vlc_in_path:
            return vlc_in_path

        return None

    @staticmethod
    def launch_external_vlc(stream_url):
        """Abre o stream diretamente no aplicativo VLC do Windows."""
        vlc_exe = IPTVManager.get_vlc_path()
        if not vlc_exe:
            return False, "VLC Media Player não foi encontrado no seu computador."

        try:
            subprocess.Popen([vlc_exe, stream_url, "--network-caching=1500"])
            return True, "Transmissão aberta no VLC Player!"
        except Exception as e:
            return False, f"Erro ao iniciar VLC: {e}"

    @staticmethod
    def launch_hls_web_player(stream_url, channel_title="Transmissão Ao Vivo"):
        """
        Gera um player web moderno Hls.js/Video.js em HTML e abre no navegador padrão.
        Funciona com qualquer .m3u8, aceleração de hardware e codecs modernos.
        """
        temp_dir = os.path.join(tempfile.gettempdir(), "videomusic_live")
        os.makedirs(temp_dir, exist_ok=True)
        html_file = os.path.join(temp_dir, "player_live.html")

        # Escapar strings para JS/HTML
        clean_url = stream_url.replace('"', '&quot;')
        clean_title = channel_title.replace('"', '&quot;')

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VideoMusic Studio - {clean_title}</title>
  <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
  <script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d0c14;
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .topbar {{
      background: #161522;
      border-bottom: 2px solid #ff7700;
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 15px rgba(0,0,0,0.5);
      z-index: 10;
    }}
    .channel-info {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .live-badge {{
      background: #e11d48;
      color: #fff;
      font-size: 11px;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 20px;
      letter-spacing: 1px;
      animation: pulse 1.6s infinite;
    }}
    @keyframes pulse {{
      0% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.6; transform: scale(0.97); }}
      100% {{ opacity: 1; transform: scale(1); }}
    }}
    .channel-title {{
      font-size: 17px;
      font-weight: 700;
      color: #f8f9fa;
    }}
    .brand {{
      font-size: 13px;
      font-weight: 600;
      color: #ff7700;
    }}
    .player-wrapper {{
      flex: 1;
      width: 100%;
      height: 100%;
      background: #000;
      position: relative;
    }}
    .video-js {{
      width: 100% !important;
      height: 100% !important;
    }}
    .video-js .vjs-big-play-button {{
      background-color: rgba(255, 119, 0, 0.8) !important;
      border-color: #ff7700 !important;
      border-radius: 50% !important;
      width: 70px !important;
      height: 70px !important;
      line-height: 70px !important;
      margin-top: -35px !important;
      margin-left: -35px !important;
    }}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="channel-info">
      <span class="live-badge">● AO VIVO</span>
      <span class="channel-title">{clean_title}</span>
    </div>
    <div class="brand">🎵 VideoMusic Studio - Live Player</div>
  </div>

  <div class="player-wrapper">
    <video
      id="videoPlayer"
      class="video-js vjs-default-skin vjs-big-play-centered"
      controls
      autoplay
      preload="auto"
      data-setup='{{"fluid": false, "autoplay": true, "liveui": true}}'>
      <source src="{clean_url}" type="application/x-mpegURL">
      <source src="{clean_url}" type="video/mp4">
      <p class="vjs-no-js">
        Para assistir a este vídeo, habilite o JavaScript no navegador.
      </p>
    </video>
  </div>

  <script>
    var player = videojs('videoPlayer');
    player.play().catch(function(error) {{
      console.log("Autoplay bloqueado pelo navegador, aguardando clique do usuário:", error);
    }});
  </script>
</body>
</html>"""

        try:
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            webbrowser.open(f"file:///{os.path.abspath(html_file).replace(os.sep, '/')}")
            return True, "Player Web HLS iniciado com sucesso!"
        except Exception as e:
            return False, f"Erro ao criar player web: {e}"


class EmbeddedVLCPlayer:
    """Gerencia a reprodução de vídeo diretamente embutida numa janela Tkinter."""
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.instance = None
        self.player = None
        self.is_playing = False
        self.is_paused = False

        if VLC_AVAILABLE:
            try:
                # Inicializar instância do libVLC
                args = [
                    "--no-xlib",
                    "--quiet",
                    "--network-caching=2000",
                    "--video-on-top"
                ]
                self.instance = vlc.Instance(args)
                self.player = self.instance.media_player_new()
                if sys.platform.startswith("win"):
                    self.player.set_hwnd(self.hwnd)
            except Exception as e:
                print(f"Erro ao inicializar EmbeddedVLCPlayer: {e}")
                self.player = None

    def play(self, stream_url):
        if not self.player or not self.instance:
            return False, "VLC não está disponível para reprodução interna."

        try:
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
            self.is_paused = False
            return True, "Reprodução iniciada."
        except Exception as e:
            return False, f"Erro ao reproduzir no VLC: {e}"

    def pause(self):
        if self.player:
            self.player.pause()
            self.is_paused = not self.is_paused

    def stop(self):
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.is_paused = False

    def set_volume(self, volume):
        """Volume de 0 a 100."""
        if self.player:
            self.player.audio_set_volume(max(0, min(100, int(volume))))

    def set_aspect_ratio(self, ratio_str):
        """Ex: '16:9', '4:3', 'default'"""
        if self.player:
            if ratio_str == "default":
                self.player.video_set_aspect_ratio(None)
            else:
                self.player.video_set_aspect_ratio(ratio_str.encode('utf-8'))
