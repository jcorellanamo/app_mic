"""
Lanzador WINCENTCAR (versión única, compatible con PyInstaller one‑file)
"""
import sys
import threading
import time
import webbrowser
import os
os.environ["STREAMLIT_DEVELOP_MODE"] = "false"


# ───────────────────────────────────────────────────────────── Browser helper
def open_browser(port: int = 8501) -> None:
    time.sleep(2)                        # pequeño delay
    webbrowser.open_new(f"http://localhost:{port}")

# ───────────────────────────────────────────────────────────── Main launcher
def main() -> None:
    port = "8501"
    # 1️⃣   Abre el navegador en un hilo
    threading.Thread(target=open_browser, args=(int(port),), daemon=True).start()

    # 2️⃣   Arranca Streamlit en el hilo principal
    import streamlit.web.cli as stcli
    sys.argv = [
        "streamlit", "run", "app.py",
        "--server.headless=true",
        "--server.port=" + port,
        "--server.enableXsrfProtection=false"
    ]
    stcli.main()                         # bloquea hasta que se cierre la app

if __name__ == "__main__":
    main()
