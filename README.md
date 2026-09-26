# 🎵 VideoMusic Studio

Um aplicativo completo, moderno e altamente personalizável para **download de vídeos e músicas (YouTube, Web)** e **reprodução de áudio/vídeo**, com suporte a **temas customizados livres**, **papel de parede (wallpaper)**, **importador de temas do PC** e **instalador de atalhos e executável (.exe) para Windows**.

---

## 🚀 Como Iniciar / Instalar com 1 Clique

Para instalar as dependências e criar o atalho oficial na sua Área de Trabalho com 1 clique:

1. Dê 2 cliques no arquivo:
   👉 **`instalar_atalho.bat`**
2. O instalador irá:
   - Instalar as bibliotecas necessárias (`customtkinter`, `pillow`, `pygame`, `yt-dlp`).
   - Gerar o ícone oficial da aplicação (`app_icon.ico`).
   - Criar o atalho no seu **Desktop (Área de Trabalho)** e no **Menu Iniciar** do Windows.
3. Pronto! Um atalho chamado **VideoMusic Studio** estará disponível na sua Área de Trabalho para abrir sempre que quiser.

---

## 📦 Como Gerar o Executável Independente (.EXE)

Se você quiser transformar o aplicativo em um arquivo executável que não precisa abrir terminal:

1. Dê 2 cliques no arquivo:
   👉 **`gerar_executavel.bat`**
2. O PyInstaller compilará o programa para a pasta `dist\VideoMusicStudio.exe`.
3. O atalho da Área de Trabalho será automaticamente atualizado para apontar para o novo `.exe`.

---

## 🎨 Recursos de Personalização de Temas

### 1. Temas Pré-definidos

- **Laranje (Vencord Style)**: Inspirado no tema escuro com tons de laranja vibrante.
- **Cyberpunk 2077**: Amarelo neon, ciano e preto fosco.
- **Midnight OLED**: Preto absoluto `#000000` com destaques em azul royal.
- **Dracula Violet**: Paleta clássica Dracula com tons roxos e rosa neon.
- **Emerald Forest**: Tons florestais profundos com verde esmeralda.
- **Neon Crimson**: Vermelho rubi e carmesim escuro.

### 2. Personalizar a Cor que Quiser (Seletor Livre)

Na aba **"🎨 Personalizar Temas"**:

- Clique nos botões de amostra de cor para abrir a paleta interativa do Windows.
- Escolha a cor exata para:
  - Fundo da janela (Background)
  - Barra lateral (Sidebar)
  - Cartões e caixas de conteúdo (Card)
  - Botões de destaque e seleção (Accent)
  - Cor do texto principal
- Digite um nome para o seu tema e clique em **"✨ Salvar e Aplicar Tema"**. O tema é salvo automaticamente na pasta `themes/`.

### 3. Importar Temas do Computador (.json ou .css)

- Clique em **"📂 Importar Tema do PC"**.
- Você pode selecionar arquivos `.json` de temas ou até arquivos `.css` (como estilos do Vencord/Discord) — o app analisa e importa a paleta de cores automaticamente!

### 4. Exportar Temas

- Clique em **"💾 Exportar Tema"** para salvar seu tema em qualquer pasta do computador e compartilhar com quem quiser.

---

## 🖼️ Papel de Parede (Wallpaper)

Na aba **"🖼️ Papel de Parede"**:

- **Escolher Imagem**: Selecione qualquer arquivo `.png`, `.jpg`, `.jpeg` ou `.webp` do seu PC.
- **Ajuste de Escurecimento (Dimmer)**: Use a barra de intensidade para escurecer o fundo, garantindo que botões, textos e listas fiquem 100% legíveis e nítidos por cima do wallpaper.
- O wallpaper e suas preferências são lembrados automaticamente mesmo após fechar o programa.
- Botão **Remover Wallpaper** para restaurar a cor sólida do tema atual com 1 clique.

---

## 📥 Downloader & 🎵 Player

- **Downloader de Alta Velocidade**:
  - Cole qualquer link do YouTube ou da web.
  - Escolha o formato: **MP3 (320kbps áudio)**, **MP4 (Qualidade máxima de vídeo)**, **MP4 (720p leve)** ou **WAV**.
  - Barra de progresso com porcentagem em tempo real e velocidade de download (MB/s).
  - Execução assíncrona (não congela a janela durante o download).
- **Player de Mídia**:
  - Adicione músicas e vídeos do seu computador à lista de reprodução.
  - Controles de Tocar, Pausar, Parar, Próxima e Anterior.
  - Controle de volume com slider.
  - Clique duplo na lista para tocar a faixa selecionada.
