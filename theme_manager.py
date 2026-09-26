import os
import sys
import json
import re

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    APP_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BUNDLE_DIR

THEMES_DIR = os.path.join(APP_DIR, "themes")
BUNDLED_THEMES_DIR = os.path.join(BUNDLE_DIR, "themes")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULT_THEMES = {
    "Laranje (Vencord Style)": {
        "name": "Laranje (Vencord Style)",
        "bg_color": "#16151d",
        "sidebar_color": "#1e1c27",
        "card_color": "#272434",
        "card_hover": "#322f42",
        "accent_color": "#ff7700",
        "accent_hover": "#ff9533",
        "text_color": "#f8f9fa",
        "subtext_color": "#a8a5b8",
        "border_color": "#ff7700"
    },
    "Cyberpunk 2077": {
        "name": "Cyberpunk 2077",
        "bg_color": "#0d0f18",
        "sidebar_color": "#141724",
        "card_color": "#1c2033",
        "card_hover": "#252b45",
        "accent_color": "#fcee0a",
        "accent_hover": "#ffe600",
        "text_color": "#00f0ff",
        "subtext_color": "#94a3b8",
        "border_color": "#ff003c"
    },
    "Midnight OLED": {
        "name": "Midnight OLED",
        "bg_color": "#000000",
        "sidebar_color": "#0a0a0a",
        "card_color": "#141414",
        "card_hover": "#222222",
        "accent_color": "#3b82f6",
        "accent_hover": "#60a5fa",
        "text_color": "#ffffff",
        "subtext_color": "#888888",
        "border_color": "#333333"
    },
    "Dracula Violet": {
        "name": "Dracula Violet",
        "bg_color": "#282a36",
        "sidebar_color": "#21222c",
        "card_color": "#44475a",
        "card_hover": "#50546c",
        "accent_color": "#bd93f9",
        "accent_hover": "#ff79c6",
        "text_color": "#f8f8f2",
        "subtext_color": "#6272a4",
        "border_color": "#bd93f9"
    },
    "Emerald Forest": {
        "name": "Emerald Forest",
        "bg_color": "#0b1a13",
        "sidebar_color": "#12291f",
        "card_color": "#1b3d2f",
        "card_hover": "#24523f",
        "accent_color": "#10b981",
        "accent_hover": "#34d399",
        "text_color": "#f0fdf4",
        "subtext_color": "#86efac",
        "border_color": "#059669"
    },
    "Neon Crimson": {
        "name": "Neon Crimson",
        "bg_color": "#150a0f",
        "sidebar_color": "#220e18",
        "card_color": "#331624",
        "card_hover": "#471e32",
        "accent_color": "#f43f5e",
        "accent_hover": "#fb7185",
        "text_color": "#fff1f2",
        "subtext_color": "#fda4af",
        "border_color": "#e11d48"
    }
}

class ThemeManager:
    def __init__(self):
        os.makedirs(THEMES_DIR, exist_ok=True)
        self.themes = dict(DEFAULT_THEMES)
        self.load_all_themes()

    def get_all_theme_names(self):
        return list(self.themes.keys())

    def get_theme(self, name):
        return self.themes.get(name, self.themes.get("Laranje (Vencord Style)", list(DEFAULT_THEMES.values())[0]))

    def load_all_themes(self):
        # Save default themes to disk if not exists
        for name, data in DEFAULT_THEMES.items():
            filename = self._sanitize_filename(name) + ".json"
            filepath = os.path.join(THEMES_DIR, filename)
            if not os.path.exists(filepath):
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                except Exception:
                    pass

        # Load from bundled dir if frozen
        if os.path.exists(BUNDLED_THEMES_DIR) and BUNDLED_THEMES_DIR != THEMES_DIR:
            for file in os.listdir(BUNDLED_THEMES_DIR):
                if file.endswith(".json"):
                    try:
                        filepath = os.path.join(BUNDLED_THEMES_DIR, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "name" in data and "bg_color" in data:
                                self.themes[data["name"]] = data
                    except Exception:
                        pass

        # Load all JSON themes from persistent folder
        if os.path.exists(THEMES_DIR):
            for file in os.listdir(THEMES_DIR):
                if file.endswith(".json"):
                    try:
                        filepath = os.path.join(THEMES_DIR, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "name" in data and "bg_color" in data and "accent_color" in data:
                                self.themes[data["name"]] = data
                    except Exception as e:
                        print(f"Erro ao carregar tema {file}: {e}")

    def save_custom_theme(self, theme_data):
        name = theme_data.get("name", "Tema Personalizado").strip()
        if not name:
            name = "Tema Personalizado"
        theme_data["name"] = name
        self.themes[name] = theme_data
        
        filename = self._sanitize_filename(name) + ".json"
        filepath = os.path.join(THEMES_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=4)
        return name

    def import_theme_from_file(self, file_path):
        """Suporta arquivos .json e arquivos .css (extraindo variáveis de cores ou hex)"""
        if not os.path.exists(file_path):
            raise FileNotFoundError("Arquivo não encontrado.")

        ext = os.path.splitext(file_path)[1].lower()
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Formato JSON inválido.")
                name = data.get("name", base_name)
                # Garante que possui os campos essenciais
                theme = {
                    "name": name,
                    "bg_color": data.get("bg_color", "#16151d"),
                    "sidebar_color": data.get("sidebar_color", "#1e1c27"),
                    "card_color": data.get("card_color", "#272434"),
                    "card_hover": data.get("card_hover", "#322f42"),
                    "accent_color": data.get("accent_color", "#ff7700"),
                    "accent_hover": data.get("accent_hover", "#ff9533"),
                    "text_color": data.get("text_color", "#ffffff"),
                    "subtext_color": data.get("subtext_color", "#aaaaaa"),
                    "border_color": data.get("border_color", "#ff7700")
                }
                return self.save_custom_theme(theme)

        elif ext == ".css":
            # Extrai cores hexadecimais do CSS
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', content)
            if not hex_colors:
                raise ValueError("Nenhuma cor hexadecimal (#HEX) encontrada no arquivo CSS.")

            # Cores heurísticas do arquivo CSS
            accent = hex_colors[0] if len(hex_colors) > 0 else "#ff7700"
            bg = hex_colors[1] if len(hex_colors) > 1 else "#16151d"
            card = hex_colors[2] if len(hex_colors) > 2 else "#272434"

            theme = {
                "name": f"{base_name} (CSS)",
                "bg_color": bg,
                "sidebar_color": self._adjust_brightness(bg, 0.9),
                "card_color": card,
                "card_hover": self._adjust_brightness(card, 1.2),
                "accent_color": accent,
                "accent_hover": self._adjust_brightness(accent, 1.2),
                "text_color": "#ffffff",
                "subtext_color": "#a8a5b8",
                "border_color": accent
            }
            return self.save_custom_theme(theme)
        else:
            raise ValueError("Extensão não suportada. Use .json ou .css")

    def export_theme_to_file(self, theme_name, target_path):
        theme_data = self.get_theme(theme_name)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=4)

    def _sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9_\-]', '_', name).lower()

    def _adjust_brightness(self, hex_color, factor):
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = min(255, max(0, int(r * factor)))
            g = min(255, max(0, int(g * factor)))
            b = min(255, max(0, int(b * factor)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color
