import os
import sys
import subprocess

def get_desktop_paths():
    """Retorna os possíveis caminhos da Área de Trabalho do Windows (incluindo OneDrive)."""
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    candidates = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
        os.path.join(user_profile, "Área de Trabalho"),
        os.path.join(user_profile, "OneDrive", "Área de Trabalho")
    ]
    existing = [p for p in candidates if os.path.exists(p)]
    return existing if existing else [os.path.join(user_profile, "Desktop")]

def get_start_menu_path():
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        start_menu = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
        if os.path.exists(start_menu):
            return start_menu
    return None

def create_windows_shortcut(target_path, arguments, working_dir, shortcut_path, icon_path=None, description=""):
    """Cria um atalho .lnk no Windows utilizando PowerShell nativo (não precisa de bibliotecas externas)."""
    try:
        ps_commands = [
            f'$WshShell = New-Object -comObject WScript.Shell;',
            f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}");',
            f'$Shortcut.TargetPath = "{target_path}";',
            f'$Shortcut.Arguments = "{arguments}";',
            f'$Shortcut.WorkingDirectory = "{working_dir}";',
            f'$Shortcut.Description = "{description}";'
        ]
        if icon_path and os.path.exists(icon_path):
            ps_commands.append(f'$Shortcut.IconLocation = "{icon_path}";')
        ps_commands.append('$Shortcut.Save();')

        full_command = " ".join(ps_commands)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_command], check=True)
        return True
    except Exception as e:
        print(f"Erro ao criar atalho com PowerShell: {e}")
        return False

def install_shortcuts():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    app_py = os.path.join(app_dir, "app.py")
    exe_path = os.path.join(app_dir, "dist", "VideoMusicStudio.exe")
    icon_path = os.path.join(app_dir, "app_icon.ico")

    # Garante que o ícone exista
    if not os.path.exists(icon_path):
        try:
            from create_icon import generate_gamer_icon
            generate_gamer_icon(icon_path)
        except Exception:
            pass

    # Determina o executável de destino
    if os.path.exists(exe_path):
        target = exe_path
        args = ""
        print(f"[*] Usando executável compilado: {exe_path}")
    else:
        # Usa pythonw.exe para abrir direto sem tela preta do cmd
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        if os.path.exists(pythonw_exe):
            target = pythonw_exe
        else:
            target = python_exe
        args = f'"{app_py}"'
        print(f"[*] Usando Python para execução: {target}")

    success_count = 0

    # 1. Criar atalho na Área de Trabalho (Desktop)
    desktop_dirs = get_desktop_paths()
    for desktop in desktop_dirs:
        shortcut_desktop = os.path.join(desktop, "VideoMusic Studio.lnk")
        if create_windows_shortcut(
            target_path=target,
            arguments=args,
            working_dir=app_dir,
            shortcut_path=shortcut_desktop,
            icon_path=icon_path,
            description="VideoMusic Studio - Player, Downloader & Custom Themes"
        ):
            print(f"[+] Atalho criado na Área de Trabalho: {shortcut_desktop}")
            success_count += 1

    # 2. Criar atalho no Menu Iniciar
    start_menu = get_start_menu_path()
    if start_menu:
        shortcut_menu = os.path.join(start_menu, "VideoMusic Studio.lnk")
        if create_windows_shortcut(
            target_path=target,
            arguments=args,
            working_dir=app_dir,
            shortcut_path=shortcut_menu,
            icon_path=icon_path,
            description="VideoMusic Studio"
        ):
            print(f"[+] Atalho criado no Menu Iniciar: {shortcut_menu}")
            success_count += 1

    if success_count > 0:
        print("\n=== SUCESSO! O atalho foi instalado no seu computador com sucesso! ===")
        print("Agora você pode abrir o VideoMusic Studio com 2 cliques pelo ícone na sua Área de Trabalho.")
    else:
        print("\n[!] Não foi possível criar os atalhos automaticamente.")

if __name__ == "__main__":
    install_shortcuts()
