import os
import math
try:
    from PIL import Image, ImageDraw, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def generate_gamer_icon(output_path="app_icon.ico"):
    """
    Gera um ícone de altíssima definição no estilo GAMER CYBERPUNK:
    Escudo hexagonal escuro, bordas neon em degradê ciano/magenta,
    fones gamer com detalhes em neon, símbolo de Play e ondas sonoras futuristas.
    """
    if not PIL_AVAILABLE:
        return None
    try:
        size = (512, 512)
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 1. Glow de fundo (Neon Aura)
        center = (256, 256)
        radius = 230
        
        # Desenhar hexágono gamer
        def get_hexagon_points(cx, cy, r):
            points = []
            for i in range(6):
                angle_deg = 60 * i - 30
                angle_rad = math.radians(angle_deg)
                points.append((cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad)))
            return points

        # Fundo do escudo escuro obsidiana
        hex_points = get_hexagon_points(256, 256, 230)
        draw.polygon(hex_points, fill="#0a0914")

        # Borda dupla neon externa (Cyan #00f0ff)
        hex_border1 = get_hexagon_points(256, 256, 226)
        draw.polygon(hex_border1, outline="#00f0ff", width=8)

        # Borda interna (Neon Magenta #ff007f)
        hex_border2 = get_hexagon_points(256, 256, 206)
        draw.polygon(hex_border2, outline="#ff007f", width=4)

        # Camada interna escura com corte esportivo
        hex_inner = get_hexagon_points(256, 256, 195)
        draw.polygon(hex_inner, fill="#120f24")

        # 2. Fones de Ouvido Gamer (Headset Arc)
        # Arco do fone (superior)
        draw.arc([130, 100, 382, 340], start=180, end=360, fill="#00f0ff", width=22)
        draw.arc([150, 120, 362, 320], start=190, end=350, fill="#ff007f", width=8)

        # Conchas laterais dos fones (Earcups gamer com ângulo)
        # Esquerda
        draw.rounded_rectangle([105, 210, 155, 310], radius=18, fill="#191533", outline="#00f0ff", width=6)
        draw.rounded_rectangle([118, 225, 142, 295], radius=10, fill="#00f0ff")

        # Direita
        draw.rounded_rectangle([357, 210, 407, 310], radius=18, fill="#191533", outline="#ff007f", width=6)
        draw.rounded_rectangle([370, 225, 394, 295], radius=10, fill="#ff007f")

        # Microfone Gamer (Boom mic saindo da concha esquerda)
        draw.line([(130, 300), (160, 350), (220, 360)], fill="#00f0ff", width=8)
        draw.ellipse([215, 352, 235, 368], fill="#ff007f", outline="#ffffff", width=2)

        # 3. Triângulo de Play Futurista Central (com efeito corte gamer)
        # Símbolo de Play central neon laranja/magenta vibrante
        play_poly = [
            (210, 190),
            (210, 310),
            (320, 250)
        ]
        draw.polygon(play_poly, fill="#ff007f", outline="#00f0ff", width=5)

        # Triângulo interno brilhante
        inner_play = [
            (225, 215),
            (225, 285),
            (295, 250)
        ]
        draw.polygon(inner_play, fill="#ffffff")

        # 4. Ondas de Áudio / Equalizador Gamer na parte inferior
        eq_bars = [
            (190, 400, 202, 420),
            (212, 385, 224, 420),
            (234, 370, 246, 420),
            (256, 360, 268, 420),
            (278, 370, 290, 420),
            (300, 385, 312, 420),
            (322, 400, 334, 420),
        ]
        for idx, bar in enumerate(eq_bars):
            color = "#00f0ff" if idx % 2 == 0 else "#ff007f"
            draw.rounded_rectangle(bar, radius=4, fill=color)

        # 5. Salvar em múltiplos tamanhos de ícone ICO (alta fidelidade)
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        resized_images = []
        for s in icon_sizes:
            resized_images.append(image.resize(s, Image.Resampling.LANCZOS))

        # Salvar ICO
        resized_images[-1].save(
            output_path, 
            format="ICO", 
            sizes=icon_sizes, 
            append_images=resized_images[:-1]
        )
        return output_path
    except Exception as e:
        print(f"Erro ao gerar ícone gamer: {e}")
        return None

if __name__ == "__main__":
    icon_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    generate_gamer_icon(icon_file)
    print("Ícone Gamer gerado com sucesso em:", icon_file)
