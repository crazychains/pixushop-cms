import requests
import sys
import os
import re
from datetime import datetime

USERNAME = os.environ.get("NOIP_USERNAME")
PASSWORD = os.environ.get("NOIP_PASSWORD")

if not USERNAME or not PASSWORD:
    print("ERROR: Faltan las variables de entorno NOIP_USERNAME o NOIP_PASSWORD")
    sys.exit(1)

BASE_URL = "https://www.noip.com"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def renew_hosts():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # 1. Página de login (forzar inglés)
    log("Accediendo a la página de login...")
    resp = session.get(f"{BASE_URL}/login", headers={"Accept-Language": "en-US,en;q=0.9"})
    log(f"URL login: {resp.url} (status {resp.status_code})")

    # Mostrar fragmento del HTML para depurar
    html = resp.text
    log(f"--- Fragmento HTML login (primeros 2000 chars) ---")
    print(html[:2000])
    log(f"--- Fin fragmento ---")

    # Extraer token CSRF con múltiples patrones
    csrf_token = None
    for pattern in [
        r'name=["\']csrf_token["\'][^>]*value=["\'](.*?)["\']',
        r'value=["\'](.*?)["\'][^>]*name=["\']csrf_token["\']',
        r'csrf_token.*?value=["\'](.*?)["\']',
        r'"csrf_token"\s*:\s*"([^"]+)"',
        r"'csrf_token'\s*:\s*'([^']+)'",
    ]:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            csrf_token = match.group(1)
            log(f"Token CSRF encontrado con patrón: {pattern[:40]}")
            break

    if not csrf_token:
        log("Aviso: No se encontró token CSRF")
        # Buscar cualquier input hidden que pueda ser relevante
        hiddens = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', html, re.IGNORECASE)
        log(f"Inputs hidden encontrados: {hiddens[:5]}")

    # 2. Login
    log("Iniciando sesión...")
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
    }
    if csrf_token:
        login_data["csrf_token"] = csrf_token

    log(f"Enviando POST a {BASE_URL}/login con campos: {list(login_data.keys())}")
    resp = session.post(
        f"{BASE_URL}/login",
        data=login_data,
        allow_redirects=True,
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{BASE_URL}/login",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    )

    log(f"URL tras login: {resp.url} (status {resp.status_code})")
    log(f"--- Fragmento HTML respuesta login (primeros 1500 chars) ---")
    print(resp.text[:1500])
    log(f"--- Fin fragmento ---")

    # Detectar login fallido
    login_failed = (
        "/login" in resp.url
        and "dashboard" not in resp.url
        and "members" not in resp.url
    )

    if login_failed:
        log("ERROR: No se pudo hacer login. Revisa usuario/contraseña en los Secrets de GitHub.")
        sys.exit(1)

    log("Login exitoso")

if __name__ == "__main__":
    renew_hosts()
