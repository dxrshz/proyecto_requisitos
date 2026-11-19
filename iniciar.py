"""
iniciar.py  -  ARRANQUE CON UN SOLO CLIC
----------------------------------------
    (opcional) git pull   -> trae la ultima version del codigo   [--pull]
    1. Abre login RiTech (Streamlit)
    2. El usuario se autentica y entra al simulador
    3. El panel actualiza NASDAQ una vez después del login (o manualmente)

Si la actualizacion falla (sin internet, BD apagada, sin configuracion...)
igual abre la app con los datos que ya existan, y avisa del problema.
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))


def asegurar_credenciales_streamlit():
    """Streamlit pregunta un email la primera vez y bloquea el arranque.
    Un credentials.toml vacio evita esa pregunta."""
    cred = Path.home() / ".streamlit" / "credentials.toml"
    if not cred.exists():
        cred.parent.mkdir(parents=True, exist_ok=True)
        cred.write_text('[general]\nemail = ""\n', encoding="utf-8")


def actualizar_codigo():
    if not (RAIZ / ".git").exists():
        print("[0] Sin repositorio git: se omite la actualizacion del codigo.")
        return
    print("[0] Actualizando codigo (git pull)...")
    r = subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True)
    print("    " + (r.stdout.strip() or r.stderr.strip()))


def main():
    print("=== Asistente de Decisiones RiTech ===\n")

    if "--pull" in sys.argv:
        actualizar_codigo()

    print("[1] Abriendo RiTech: login / sign in...")
    asegurar_credenciales_streamlit()
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])


if __name__ == "__main__":
    main()
