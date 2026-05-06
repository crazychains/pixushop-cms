import requests
import sys
import os
from datetime import datetime

# Credenciales desde variables de entorno
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
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })

    # 1. Obtener página de login para el token CSRF
    log("Accediendo a la página de login...")
    resp = session.get(f"{BASE_URL}/login")
    if resp.status_code != 200:
        log(f"ERROR: No se pudo acceder al login (status {resp.status_code})")
        sys.exit(1)

    # Extraer token CSRF
    csrf_token = None
    for line in resp.text.split("\n"):
        if 'csrf_token' in line and 'value=' in line:
            try:
                csrf_token = line.split('value="')[1].split('"')[0]
                break
            except IndexError:
                pass

    # 2. Hacer login
    log("Iniciando sesión...")
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
    }
    if csrf_token:
        login_data["csrf_token"] = csrf_token

    resp = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)

    if "Invalid username" in resp.text or "Invalid password" in resp.text or resp.url == f"{BASE_URL}/login":
        log("ERROR: Credenciales incorrectas o login fallido")
        sys.exit(1)

    log("Login exitoso")

    # 3. Ir a la página de hostnames
    log("Accediendo a la página de hostnames...")
    resp = session.get(f"{BASE_URL}/dynamic-dns")
    if resp.status_code != 200:
        log(f"ERROR: No se pudo acceder a dynamic-dns (status {resp.status_code})")
        sys.exit(1)

    # 4. Buscar TODOS los botones/enlaces de confirmación
    confirmed = 0
    skipped = 0
    errors = 0
    confirm_urls = []

    lines = resp.text.split("\n")
    for line in lines:
        if "noip-confirm-host" in line or ("confirm" in line.lower() and "href" in line.lower()):
            try:
                href_start = line.find('href="') + 6
                href_end = line.find('"', href_start)
                confirm_url = line[href_start:href_end]

                if not confirm_url.startswith("http"):
                    confirm_url = BASE_URL + confirm_url

                # Evitar duplicados
                if confirm_url not in confirm_urls:
                    confirm_urls.append(confirm_url)
            except Exception:
                pass

    if confirm_urls:
        log(f"Se encontraron {len(confirm_urls)} hostname(s) pendientes de confirmación")
        for i, url in enumerate(confirm_urls, 1):
            log(f"[{i}/{len(confirm_urls)}] Confirmando: {url}")
            try:
                confirm_resp = session.get(url)
                if confirm_resp.status_code == 200:
                    log(f"  ✓ Confirmado correctamente")
                    confirmed += 1
                else:
                    log(f"  ✗ Error al confirmar (status {confirm_resp.status_code})")
                    errors += 1
            except Exception as e:
                log(f"  ✗ Excepción al confirmar: {e}")
                errors += 1
    else:
        log("No se encontraron hostnames pendientes de confirmación (puede que aún no sea necesario renovar)")
        skipped += 1

    # 5. Resumen final
    log("─" * 50)
    log(f"RESUMEN:")
    log(f"  ✓ Confirmados:          {confirmed}")
    log(f"  ─ Sin acción necesaria: {skipped}")
    log(f"  ✗ Errores:              {errors}")
    log("─" * 50)

    if errors > 0:
        log("ADVERTENCIA: Hubo errores en la confirmación. Revisa los logs.")
        sys.exit(1)

if __name__ == "__main__":
    renew_hosts()
