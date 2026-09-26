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
    "Cyberpunk 2077 (Gamer Neon)": {
        "name": "Cyberpunk 2077 (Gamer Neon)",
        "bg_color": "#090a10",
        "sidebar_color": "#10121d",
        "card_color": "#171a29",
        "card_hover": "#22273d",
        "accent_color": "#00f0ff",
        "accent_hover": "#38f5ff",
        "text_color": "#ffffff",
        "subtext_color": "#8b9bb4",
        "border_color": "#00f0ff"
    },
    "Razer Chroma (Gamer Green)": {
        "name": "Razer Chroma (Gamer Green)",
        "bg_color": "#070c08",
        "sidebar_color": "#0c150e",
        "card_color": "#122015",
        "card_hover": "#1c3221",
        "accent_color": "#00ff55",
        "accent_hover": "#33ff77",
        "text_color": "#f0fff4",
        "subtext_color": "#76ba8a",
        "border_color": "#00ff55"
    },
    "ROG Blood (Gamer Crimson)": {
        "name": "ROG Blood (Gamer Crimson)",
        "bg_color": "#0e0608",
        "sidebar_color": "#170a0e",
        "card_color": "#241016",
        "card_hover": "#361822",
        "accent_color": "#ff0044",
        "accent_hover": "#ff3366",
        "text_color": "#fff0f3",
        "subtext_color": "#c27d8e",
        "border_color": "#ff0044"
    },
    "Alienware Frost (Ice Blue)": {
        "name": "Alienware Frost (Ice Blue)",
        "bg_color": "#080c14",
        "sidebar_color": "#0d1422",
        "card_color": "#131d31",
        "card_hover": "#1d2c49",
        "accent_color": "#00b4d8",
        "accent_hover": "#48cae4",
        "text_color": "#e0f2fe",
        "subtext_color": "#7dd3fc",
        "border_color": "#00b4d8"
    },
    "Apex Legend (Vivid Purple)": {
        "name": "Apex Legend (Vivid Purple)",
        "bg_color": "#0e0919",
        "sidebar_color": "#150d26",
        "card_color": "#20143a",
        "card_hover": "#2e1c53",
        "accent_color": "#a855f7",
        "accent_hover": "#c084fc",
        "text_color": "#faf5ff",
        "subtext_color": "#c084fc",
        "border_color": "#a855f7"
    },
    "Laranje (Vencord Gamer)": {
        "name": "Laranje (Vencord Gamer)",
        "bg_color": "#121118",
        "sidebar_color": "#181622",
        "card_color": "#211e2e",
        "card_hover": "#2c283d",
        "accent_color": "#ff6600",
        "accent_hover": "#ff8533",
        "text_color": "#f8f9fa",
        "subtext_color": "#a8a5b8",
        "border_color": "#ff6600"
    },
    "Midnight OLED Stealth": {
        "name": "Midnight OLED Stealth",
        "bg_color": "#000000",
        "sidebar_color": "#080808",
        "card_color": "#111111",
        "card_hover": "#1c1c1c",
        "accent_color": "#38bdf8",
        "accent_hover": "#7dd3fc",
        "text_color": "#ffffff",
        "subtext_color": "#737373",
        "border_color": "#262626"
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
        return self.themes.get(name, self.themes.get("Cyberpunk 2077 (Gamer Neon)", list(DEFAULT_THEMES.values())[0]))

    def load_all_themes(self):
        # Salvar temas padrão se não existirem
        for name, data in DEFAULT_THEMES.items():
            filename = self._sanitize_filename(name) + ".json"
            filepath = os.path.join(THEMES_DIR, filename)
            if not os.path.exists(filepath):
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                except Exception:
                    pass

        # Carregar temas embutidos se estiver congelado
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

        # Carregar temas da pasta persistente
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
            json.dump(theme_data, f, indent=4, ensure_ascii=False)
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
                theme = {
                    "name": name,
                    "bg_color": data.get("bg_color", "#090a10"),
                    "sidebar_color": data.get("sidebar_color", "#10121d"),
                    "card_color": data.get("card_color", "#171a29"),
                    "card_hover": data.get("card_hover", "#22273d"),
                    "accent_color": data.get("accent_color", "#00f0ff"),
                    "accent_hover": data.get("accent_hover", "#38f5ff"),
                    "text_color": data.get("text_color", "#ffffff"),
                    "subtext_color": data.get("subtext_color", "#8b9bb4"),
                    "border_color": data.get("border_color", "#00f0ff")
                }
                return self.save_custom_theme(theme)

        elif ext == ".css":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', content)
            if not hex_colors:
                raise ValueError("Nenhuma cor hexadecimal (#HEX) encontrada no arquivo CSS.")

            accent = hex_colors[0] if len(hex_colors) > 0 else "#00f0ff"
            bg = hex_colors[1] if len(hex_colors) > 1 else "#090a10"
            card = hex_colors[2] if len(hex_colors) > 2 else "#171a29"

            theme = {
                "name": f"{base_name} (Gamer CSS)",
                "bg_color": bg,
                "sidebar_color": self._adjust_brightness(bg, 0.9),
                "card_color": card,
                "card_hover": self._adjust_brightness(card, 1.2),
                "accent_color": accent,
                "accent_hover": self._adjust_brightness(accent, 1.2),
                "text_color": "#ffffff",
                "subtext_color": "#8b9bb4",
                "border_color": accent
            }
            return self.save_custom_theme(theme)
        else:
            raise ValueError("Extensão não suportada. Use .json ou .css")

    def export_theme_to_file(self, theme_name, target_path):
        theme_data = self.get_theme(theme_name)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=4, ensure_ascii=False)

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
