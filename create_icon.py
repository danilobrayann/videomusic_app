import os
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def generate_default_icon(output_path="app_icon.ico"):
    """Gera um ícone moderno de música/vídeo caso não haja um ícone fornecido."""
    if not PIL_AVAILABLE:
        return None
    try:
        size = (256, 256)
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Fundo circular degradê / escuro com borda laranja vibrante
        draw.rounded_rectangle([10, 10, 246, 246], radius=50, fill="#16151d", outline="#ff7700", width=8)

        # Símbolo de Play / Música
        # Triângulo de Play
        draw.polygon([(85, 65), (85, 191), (195, 128)], fill="#ff7700")

        # Círculo central brilhante
        draw.ellipse([115, 115, 141, 141], fill="#ffffff")

        # Salvar em múltiplos tamanhos de ícone ICO
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        image.save(output_path, format="ICO", sizes=icon_sizes)
        return output_path
    except Exception as e:
        print(f"Erro ao gerar ícone: {e}")
        return None

if __name__ == "__main__":
    icon_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    generate_default_icon(icon_file)
    print("Ícone gerado em:", icon_file)
