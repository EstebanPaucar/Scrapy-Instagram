import json
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import PRIMARY_USER, PRIMARY_PASS, BACKUP_USER, BACKUP_PASS, SESSION_FILE, RESULTS_DIR
from utils import random_pause


def persist_session(context):
    cookies = context.cookies()
    SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    print("✅ Cookies guardadas.")


def restore_session(context):
    if SESSION_FILE.exists():
        cookies = json.loads(SESSION_FILE.read_text())
        context.add_cookies(cookies)
        print("🍪 Cookies cargadas desde archivo.")
        return True
    return False


def check_session_alive(page) -> bool:
    """Visita Instagram y verifica si la sesión sigue activa."""
    try:
        page.goto("https://www.instagram.com/", timeout=20000)
        random_pause(2, 4)
        if page.locator('input[name="username"]').is_visible(timeout=4000):
            print("⚠️  Sesión expirada.")
            return False
        print("✅ Sesión activa.")
        return True
    except PlaywrightTimeoutError:
        return False


def detect_account_blocked(page) -> bool:
    """Detecta si la cuenta actual está bloqueada o suspendida por Instagram."""
    blocked_signals = [
        'text="We suspended your account"',
        'text="Tu cuenta fue suspendida"',
        'text="ve suspended your account"',
        'text="Hemos suspendido tu cuenta"',
        'text="Your account has been disabled"',
        'text="Tu cuenta fue desactivada"',
    ]
    for selector in blocked_signals:
        try:
            if page.locator(selector).is_visible(timeout=2000):
                print("🚫 Cuenta bloqueada/suspendida detectada.")
                return True
        except Exception:
            pass

    if "challenge" in page.url or "suspended" in page.url:
        print("🚫 Redirección a página de bloqueo detectada.")
        return True

    return False


def perform_login(page, context, username: str, password: str):
    """Realiza el login con las credenciales indicadas y guarda las cookies."""
    print(f"🔐 Iniciando sesión con: {username}")
    page.goto("https://www.instagram.com/accounts/login/", timeout=30000)
    random_pause(3, 5)

    try:
        print("✍️ Escribiendo credenciales...")
        username_input = page.locator('input[type="text"], input[name="username"]').first
        username_input.fill(username)
        random_pause(1, 2)

        password_input = page.locator('input[type="password"], input[name="password"]').first
        password_input.fill(password)
        random_pause(1, 2)

        print("🖱️ Presionando Enter para enviar el formulario...")
        password_input.press("Enter")
        random_pause(5, 8)

    except Exception as e:
        print(f"❌ Error llenando el formulario: {e}")
        page.screenshot(path=RESULTS_DIR / "error_formulario.png")
        raise RuntimeError("Los selectores del formulario fallaron. Revisa la captura.")

    try:
        not_now = page.locator("text=Ahora no, text=Not Now").first
        if not_now.is_visible(timeout=4000):
            not_now.click()
            random_pause(1, 2)
    except Exception:
        pass

    try:
        not_now2 = page.locator("text=Ahora no, text=Not Now").first
        if not_now2.is_visible(timeout=4000):
            not_now2.click()
            random_pause(1, 2)
    except Exception:
        pass

    if "login" in page.url:
        raise RuntimeError(f"❌ Login fallido para {username}. Meta rechazó las credenciales.")

    persist_session(context)
    print(f"✅ Login exitoso con: {username}")


def _switch_to_backup_account(page, context):
    """Limpia la sesión actual e inicia sesión con la cuenta de respaldo."""
    if not BACKUP_USER or not BACKUP_PASS:
        raise RuntimeError(
            "❌ La cuenta principal está bloqueada y no hay credenciales de respaldo definidas.\n"
            "   Añade INSTAGRAM_USERNAME_BACKUP y INSTAGRAM_PASSWORD_BACKUP en tu archivo .env"
        )
    SESSION_FILE.unlink(missing_ok=True)
    context.clear_cookies()
    perform_login(page, context, BACKUP_USER, BACKUP_PASS)


def initialize_auth(page, context):
    """
    Carga cookies o hace login con la cuenta principal.
    Si la cuenta principal está bloqueada, usa la cuenta de respaldo.
    """
    loaded = restore_session(context)
    if loaded and check_session_alive(page):
        if detect_account_blocked(page):
            print("🔄 Cambiando a cuenta de respaldo...")
            _switch_to_backup_account(page, context)
        return

    SESSION_FILE.unlink(missing_ok=True)

    try:
        perform_login(page, context, PRIMARY_USER, PRIMARY_PASS)
        random_pause(2, 4)
        if detect_account_blocked(page):
            print("🔄 Cuenta principal bloqueada. Cambiando a cuenta de respaldo...")
            _switch_to_backup_account(page, context)
    except RuntimeError:
        print("⚠️ Login principal falló. Intentando con cuenta de respaldo...")
        _switch_to_backup_account(page, context)


def refresh_auth_if_needed(page, context):
    """Re-verifica la sesión y cambia de cuenta si está bloqueada."""
    if not check_session_alive(page):
        perform_login(page, context, PRIMARY_USER, PRIMARY_PASS)
    elif detect_account_blocked(page):
        print("🔄 Cuenta bloqueada durante el scraping. Cambiando a respaldo...")
        _switch_to_backup_account(page, context)