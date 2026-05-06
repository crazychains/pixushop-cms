import requests
import os
import sys

# Usamos los nombres de variables que ya tienes configurados
NOIP_USER = os.getenv("NOIP_USERNAME")
NOIP_PASS = os.getenv("NOIP_PASSWORD")
NOIP_HOSTS = os.getenv("NOIP_HOSTS")

def update_dns():
    # Validación de variables
    if not all([NOIP_USER, NOIP_PASS, NOIP_HOSTS]):
        print("❌ Error: Faltan variables de entorno.")
        print(f"   User: {'OK' if NOIP_USER else 'FALTA'}")
        print(f"   Pass: {'OK' if NOIP_PASS else 'FALTA'}")
        print(f"   Hosts: {'OK' if NOIP_HOSTS else 'FALTA'}")
        return False

    print(f"🔄 Iniciando actualización para hosts: {NOIP_HOSTS}")

    # La API de No-IP acepta múltiples hosts separados por comas
    # Dejamos 'myip' vacío para que No-IP detecte la IP automáticamente
    url = f"https://dynupdate.no-ip.com/nic/update?hostname={NOIP_HOSTS}&myip="

    try:
        # Realizamos la petición GET con Autenticación Básica
        response = requests.get(url, auth=(NOIP_USER, NOIP_PASS))
        
        print(f"📡 Código de estado HTTP: {response.status_code}")
        print(f"📝 Respuesta del servidor: {response.text}")

        # Analizamos la respuesta de No-IP
        if response.status_code == 200:
            # Si hay múltiples hosts, la respuesta puede contener múltiples líneas o códigos
            # Verificamos si NO hay errores conocidos en la respuesta completa
            if "nohost" in response.text:
                print("❌ Error: Uno de los hosts no existe en tu cuenta No-IP.")
                return False
            elif "badauth" in response.text:
                print("❌ Error: Usuario o contraseña incorrectos.")
                return False
            elif "badagent" in response.text:
                print("❌ Error: Agente de usuario no permitido (contacta a No-IP).")
                return False
            elif '!donator' in response.text:
                print("⚠️ Advertencia: Una función solicitada requiere cuenta de pago.")
                # Esto no es un error fatal de actualización, pero es un warning
                return True
            elif "good" in response.text or "nochg" in response.text:
                print("✅ Actualización completada con éxito.")
                return True
            else:
                # Código 200 pero respuesta desconocida (podría ser OK)
                print("⚠️ Respuesta inesperada del servidor (200 OK), pero formato desconocido.")
                return True
        else:
            print(f"❌ Error en la petición HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Excepción durante el proceso: {e}")
        return False

if __name__ == "__main__":
    success = update_dns()
    sys.exit(0 if success else 1)
