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
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    })

    # 1. Página de login
    log("Accediendo a la página de login...")
    resp = session.get(f"{BASE_URL}/login")
    if resp.status_code != 200:
        log(f"ERROR: No se pudo acceder al login (status {resp.status_code})")
        sys.exit(1)

    # Extraer token CSRF
    csrf_token = None
    match = re.search(r'name=["\']csrf_token["\'].*?value=["\'](.*?)["\']', resp.text)
    if not match:
        match = re.search(r'value=["\'](.*?)["\'].*?name=["\']csrf_token["\']', resp.text)
    if match:
        csrf_token = match.group(1)
        log(f"Token CSRF encontrado")
    else:
        log("Aviso: No se encontró token CSRF, continuando sin él")

    # 2. Login
    log("Iniciando sesión...")
    login_data = {"username": USERNAME, "password": PASSWORD}
    if csrf_token:
        login_data["csrf_token"] = csrf_token

    resp = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)

    if "Invalid" in resp.text or resp.url.endswith("/login"):
        log("ERROR: Credenciales incorrectas o login fallido")
        log(f"URL final: {resp.url}")
        sys.exit(1)

    log(f"Login exitoso (redirigido a: {resp.url})")

    # 3. Probar distintas URLs donde pueden estar los hostnames
    hostnames_page = None
    candidate_urls = [
        f"{BASE_URL}/dns",
        f"{BASE_URL}/members/dns",
        f"{BASE_URL}/dynamic-dns",
        f"{BASE_URL}/members/dynamic-dns",
        f"{BASE_URL}/confirm-host",
    ]

    for url in candidate_urls:
        log(f"Probando URL: {url}")
        r = session.get(url)
        if r.status_code == 200 and ("hostname" in r.text.lower() or "confirm" in r.text.lower()):
            log(f"✓ Página de hostnames encontrada en: {url}")
            hostnames_page = r
            break
        else:
            log(f"  → No válida (status {r.status_code})")

    if not hostnames_page:
        log("ERROR: No se pudo encontrar la página de hostnames en ninguna URL conocida")
        log("Por favor abre una issue o revisa manualmente la URL correcta en noip.com")
        sys.exit(1)

    # 4. Buscar URLs de confirmación en el HTML
    confirmed = 0
    skipped = 0
    errors = 0
    confirm_urls = []

    # Buscar patrones de confirmación
    patterns = [
        r'href=["\'](/[^"\']*confirm[^"\']*)["\']',
        r'href=["\'](https://www\.noip\.com/[^"\']*confirm[^"\']*)["\']',
        r'href=["\'](/[^"\']*host[^"\']*confirm[^"\']*)["\']',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, hostnames_page.text, re.IGNORECASE)
        for m in matches:
            url = m if m.startswith("http") else BASE_URL + m
            if url not in confirm_urls:
                confirm_urls.append(url)

    # Filtrar URLs irrelevantes
    confirm_urls = [u for u in confirm_urls if not any(x in u for x in ["support", "knowledgebase", "faq", "login", "logout"])]

    if confirm_urls:
        log(f"Se encontraron {len(confirm_urls)} hostname(s) pendientes de confirmación")
        for i, url in enumerate(confirm_urls, 1):
            log(f"[{i}/{len(confirm_urls)}] Confirmando: {url}")
            try:
                r = session.get(url)
                if r.status_code == 200:
                    log(f"  ✓ Confirmado correctamente")
                    confirmed += 1
                else:
                    log(f"  ✗ Error (status {r.status_code})")
                    errors += 1
            except Exception as e:
                log(f"  ✗ Excepción: {e}")
                errors += 1
    else:
        log("No se encontraron hostnames pendientes de confirmación")
        log("(Puede que aún no sea necesario renovar, o que el HTML haya cambiado)")
        skipped += 1

    # 5. Resumen
    log("─" * 50)
    log("RESUMEN:")
    log(f"  ✓ Confirmados:          {confirmed}")
    log(f"  ─ Sin acción necesaria: {skipped}")
    log(f"  ✗ Errores:              {errors}")
    log("─" * 50)

    if errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    renew_hosts()
