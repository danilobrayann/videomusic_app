import os
try:
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class WallpaperManager:
    def __init__(self):
        self.current_wallpaper_path = None
        self.dim_level = 0.45   # 0.0 (sem escurecer) até 0.9 (muito escuro)
        self.blur_radius = 0    # 0 (sem desfoque) até 25 (vidro fosco acentuado)
        self._cached_original_img = None
        self._last_size = (0, 0)
        self._last_dim = None
        self._last_blur = None
        self._last_rendered_photo = None

    def set_wallpaper(self, image_path, dim_level=None, blur_radius=None):
        if not PIL_AVAILABLE:
            return False, "A biblioteca Pillow (PIL) não está instalada. Instale com 'pip install pillow'."
        
        if image_path and os.path.exists(image_path):
            try:
                self.current_wallpaper_path = image_path
                self._cached_original_img = Image.open(image_path).convert("RGBA")
                if dim_level is not None:
                    self.dim_level = max(0.0, min(0.9, float(dim_level)))
                if blur_radius is not None:
                    self.blur_radius = max(0, min(25, int(blur_radius)))
                self._last_size = (0, 0)
                self._last_rendered_photo = None
                return True, "Wallpaper carregado com sucesso."
            except Exception as e:
                return False, f"Erro ao abrir imagem: {e}"
        else:
            self.current_wallpaper_path = None
            self._cached_original_img = None
            self._last_rendered_photo = None
            return True, "Wallpaper removido."

    def set_dim_level(self, level):
        self.dim_level = max(0.0, min(0.9, float(level)))
        self._last_size = (0, 0)  # forçar re-render

    def set_blur_level(self, radius):
        self.blur_radius = max(0, min(25, int(radius)))
        self._last_size = (0, 0)  # forçar re-render

    def get_rendered_image(self, target_width, target_height):
        """Retorna uma ImageTk.PhotoImage dimensionada para preencher a janela com escurecimento e desfoque aplicados."""
        if not PIL_AVAILABLE or not self._cached_original_img or target_width <= 10 or target_height <= 10:
            return None

        # Cache para evitar reprocessamento a cada frame se dimensões e efeitos não mudaram
        if (self._last_rendered_photo and 
            self._last_size == (target_width, target_height) and 
            self._last_dim == self.dim_level and 
            self._last_blur == self.blur_radius):
            return self._last_rendered_photo

        try:
            img = self._cached_original_img.copy()

            # Aspect Cover (preenche a tela mantendo proporção)
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height

            if target_ratio > img_ratio:
                # Mais largo: corta altura
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                # Mais alto: corta largura
                new_height = target_height
                new_width = int(target_height * img_ratio)

            img = img.resize((max(1, new_width), max(1, new_height)), Image.Resampling.BILINEAR)

            # Centraliza o corte
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            img = img.crop((left, top, right, bottom))

            # Aplicar efeito de desfoque (Glassmorphic Blur) se ativo
            if self.blur_radius > 0:
                img = img.filter(ImageFilter.GaussianBlur(self.blur_radius))

            # Aplicar overlay escuro para contraste
            if self.dim_level > 0.01:
                overlay = Image.new("RGBA", img.size, (0, 0, 0, int(255 * self.dim_level)))
                img = Image.alpha_composite(img, overlay)

            self._last_rendered_photo = ImageTk.PhotoImage(img)
            self._last_size = (target_width, target_height)
            self._last_dim = self.dim_level
            self._last_blur = self.blur_radius
            return self._last_rendered_photo
        except Exception as e:
            print(f"Erro ao renderizar wallpaper: {e}")
            return None
