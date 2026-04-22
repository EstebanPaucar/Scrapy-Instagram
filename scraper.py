import os
import re
import json
import time
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
load_dotenv()

USERNAME       = os.getenv("INSTAGRAM_USERNAME")
PASSWORD       = os.getenv("INSTAGRAM_PASSWORD")
COOKIES_FILE   = Path("cookies.json")
OUTPUT_DIR     = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def human_delay(min_s: float = 1.5, max_s: float = 3.5):
    """Pausa aleatoria para imitar comportamiento humano."""
    time.sleep(random.uniform(min_s, max_s))


def save_cookies(context):
    cookies = context.cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print("✅ Cookies guardadas.")


def load_cookies(context):
    if COOKIES_FILE.exists():
        cookies = json.loads(COOKIES_FILE.read_text())
        context.add_cookies(cookies)
        print("🍪 Cookies cargadas desde archivo.")
        return True
    return False


def is_session_valid(page) -> bool:
    """Visita Instagram y verifica si la sesión sigue activa."""
    try:
        page.goto("https://www.instagram.com/", timeout=20000)
        human_delay(2, 4)
        # Si aparece el botón de login, la sesión expiró
        if page.locator('input[name="username"]').is_visible(timeout=4000):
            print("⚠️  Sesión expirada.")
            return False
        print("✅ Sesión activa.")
        return True
    except PlaywrightTimeoutError:
        return False


def do_login(page, context):
    """Realiza el login y guarda las cookies nuevas."""
    print("🔐 Iniciando sesión...")
    page.goto("https://www.instagram.com/accounts/login/", timeout=30000)
    human_delay(3, 5)

    # 1. LLENAR EL FORMULARIO
    try:
        print("✍️ Escribiendo credenciales...")
        
        username_input = page.locator('input[type="text"], input[name="username"]').first
        username_input.fill(USERNAME)
        human_delay(1, 2)
        
        password_input = page.locator('input[type="password"], input[name="password"]').first
        password_input.fill(PASSWORD)
        human_delay(1, 2)
        
        print("🖱️ Presionando Enter para enviar el formulario...")
        password_input.press("Enter")
        human_delay(5, 8) # Pausa larga para que cargue el dashboard
        
    except Exception as e:
        print(f"❌ Error llenando el formulario: {e}")
        page.screenshot(path=OUTPUT_DIR / "error_formulario.png")
        raise RuntimeError("Los selectores del formulario fallaron. Revisa la captura.")

    # 2. MANEJAR MODAL "GUARDAR INFO"
    try:
        not_now = page.locator("text=Ahora no, text=Not Now").first
        if not_now.is_visible(timeout=4000):
            not_now.click()
            human_delay(1, 2)
    except Exception:
        pass

    # 3. MANEJAR MODAL "NOTIFICACIONES"
    try:
        not_now2 = page.locator("text=Ahora no, text=Not Now").first
        if not_now2.is_visible(timeout=4000):
            not_now2.click()
            human_delay(1, 2)
    except Exception:
        pass

    # 4. VERIFICAR ÉXITO
    if "login" in page.url:
        raise RuntimeError("❌ Login fallido. Meta rechazó las credenciales.")

    save_cookies(context)
    print("✅ Login exitoso.")

def ensure_authenticated(page, context):
    """Carga cookies o hace login según corresponda."""
    loaded = load_cookies(context)
    if loaded and is_session_valid(page):
        return
    # Cookies inválidas o inexistentes → login completo
    COOKIES_FILE.unlink(missing_ok=True)
    do_login(page, context)


# ─────────────────────────────────────────────
#  SCRAPING
# ─────────────────────────────────────────────
def get_post_urls(page, profile_url: str, max_posts: int) -> list[str]:
    """Recolecta las URLs de los posts de un perfil."""
    print(f"\n📂 Visitando perfil: {profile_url}")
    page.goto(profile_url, timeout=30000)
    human_delay(2, 4)

    post_urls = set()
    last_count = 0
    stall_rounds = 0

    print(f"🔍 Recolectando URLs de posts (objetivo: {max_posts})...")

    while len(post_urls) < max_posts:
        # Buscar todos los links de posts visibles
        anchors = page.locator('a[href*="/p/"]').all()
        for a in anchors:
            href = a.get_attribute("href")
            if href and "/p/" in href:
                post_urls.add("https://www.instagram.com" + href.split("?")[0])

        print(f"  → {len(post_urls)} URLs encontradas", end="\r")

        if len(post_urls) >= max_posts:
            break

        # Scroll hacia abajo
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        human_delay(2, 4)

        # Detectar si dejó de crecer (fin del perfil)
        if len(post_urls) == last_count:
            stall_rounds += 1
            if stall_rounds >= 3:
                print("\n⚠️  No se encontraron más posts.")
                break
        else:
            stall_rounds = 0

        last_count = len(post_urls)

    final = list(post_urls)[:max_posts]
    print(f"\n✅ {len(final)} URLs recolectadas.")
    return final


def scrape_post(page, post_url: str, index: int) -> dict | None:
    """Extrae todos los datos de un post individual."""
    try:
        # Esperamos a que la red esté tranquila (networkidle), no a una etiqueta en específico.
        page.goto(post_url, wait_until="networkidle", timeout=30000)
        human_delay(2, 4)

        # EL TRUCO DEL SCROLL MÁGICO: Hacemos un scroll diminuto para forzar a React a renderizar las imágenes.
        page.evaluate("window.scrollBy(0, 100)")
        human_delay(1, 2)

        data = {
            "url": post_url,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "caption": None,
            "likes": None,
            "date": None,
            "media_urls": [],
        }

        # ── 1. Fecha ──────────────────────────────────────────────────
        try:
            time_el = page.locator("time").first
            data["date"] = time_el.get_attribute("datetime", timeout=3000)
        except Exception:
            pass

        # ── 2 y 3. El Atajo SEO (Caption, Likes y Comentarios) ──────────
        try:
            # Buscamos la etiqueta meta oculta. No podemos usar is_visible() porque las etiquetas meta son invisibles por naturaleza.
            meta_locator = page.locator('meta[property="og:description"], meta[name="description"]').first
            
            # Extraemos el contenido directamente
            content = meta_locator.get_attribute("content", timeout=3000)
            
            if content:
                # El texto suele ser: "213 likes, 4 comments - cuenta en Fecha: El caption va aquí..."
                # o en español: "213 Me gusta, 4 comentarios - cuenta en Fecha: El caption..."
                
                # 1. Extraer el Caption (todo lo que está después de los primeros dos puntos)
                if ":" in content:
                    data["caption"] = content.split(":", 1)[1].strip().strip('"').strip('“').strip('”')
                else:
                    data["caption"] = content # Respaldo si no hay dos puntos
                
                # 2. Extraer Likes usando expresiones regulares (busca números antes de la palabra "likes" o "Me gusta")
                import re
                likes_match = re.search(r'([\d,.]+)\s*(likes|Me gusta)', content, re.IGNORECASE)
                if likes_match:
                    data["likes"] = likes_match.group(1).replace(',', '')

                # 3. Extraer Comentarios
                comments_match = re.search(r'([\d,.]+)\s*(comments|comentarios)', content, re.IGNORECASE)
                if comments_match:
                    data["comments_count"] = comments_match.group(1).replace(',', '')
                    
        except Exception as e:
            print(f"    [!] Aviso: No se pudo extraer la etiqueta meta en {post_url}: {e}")

        # ── 4. Imágenes y Videos ──────────────────────────────────────
        try:
            # Quitamos la restricción del 'article'. Buscamos cualquier imagen grande de Instagram.
            imgs = page.locator('img[style*="object-fit: cover"]').all() 
            for img in imgs:
                src = img.get_attribute("src")
                if src and ("scontent" in src or "fbcdn" in src or "instagram" in src):
                    if src not in data["media_urls"]:
                        data["media_urls"].append(src)

            videos = page.locator("video").all()
            for vid in videos:
                src = vid.get_attribute("src")
                if src and src not in data["media_urls"]:
                    data["media_urls"].append(src)
        except Exception:
            pass

        print(f"  [{index}] ✅ Post extraído: {post_url}")
        return data

    except PlaywrightTimeoutError:
        print(f"  [{index}] ⏱️  Timeout cargando {post_url}")
        # Hacemos una captura en caso de timeout para ver con qué se trabó
        page.screenshot(path=OUTPUT_DIR / f"timeout_post_{index}.png")
        return None
    except Exception as e:
        print(f"  [{index}] ❌ Error en {post_url}: {e}")
        return None

# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────
def main():
    if not USERNAME or not PASSWORD:
        raise RuntimeError("❌ Define INSTAGRAM_USERNAME y INSTAGRAM_PASSWORD en tu archivo .env")

    # ── Configuración del scraping ──────────────
    TARGET_PROFILE = "https://www.instagram.com/sdquito/"   # ← Cambia esto
    MAX_POSTS       = int(input("¿Cuántos posts quieres extraer? → ").strip())

    print("\n" + "═" * 50)
    print("  Instagram Scraper")
    print("═" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,          # False = ves el navegador (más seguro al inicio)
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 1) Autenticación
        ensure_authenticated(page, context)

        # 2) Recolectar URLs de posts
        post_urls = get_post_urls(page, TARGET_PROFILE, MAX_POSTS)

        # 3) Scraping post a post
        print(f"\n📥 Scrapeando {len(post_urls)} posts...")
        results = []
        for i, url in enumerate(post_urls, 1):
            # Re-verificar sesión cada 20 posts
            if i % 20 == 0:
                if not is_session_valid(page):
                    do_login(page, context)

            post_data = scrape_post(page, url, i)
            if post_data:
                results.append(post_data)

            human_delay(5, 10)  # Pausa entre posts

        # 4) Guardar resultados
        timestamp  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        profile_name = TARGET_PROFILE.rstrip("/").split("/")[-1]
        output_path = OUTPUT_DIR / f"{profile_name}_{timestamp}.json"

        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Datos guardados en: {output_path}")
        print(f"📊 Posts extraídos exitosamente: {len(results)} / {len(post_urls)}")

        browser.close()


if __name__ == "__main__":
    main()
