import re
from datetime import datetime
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from config import RESULTS_DIR
from utils import random_pause


def collect_post_urls(page, profile_url: str, max_posts: int) -> list[str]:
    """Recolecta las URLs de los posts de un perfil."""
    print(f"\n📂 Visitando perfil: {profile_url}")
    page.goto(profile_url, timeout=30000)
    random_pause(2, 4)

    post_urls = set()
    last_count = 0
    stall_rounds = 0

    print(f"🔍 Recolectando URLs de posts (objetivo: {max_posts})...")

    while len(post_urls) < max_posts:
        anchors = page.locator('a[href*="/p/"]').all()
        for a in anchors:
            href = a.get_attribute("href")
            if href and "/p/" in href:
                post_urls.add("https://www.instagram.com" + href.split("?")[0])

        print(f"  → {len(post_urls)} URLs encontradas", end="\r")

        if len(post_urls) >= max_posts:
            break

        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        random_pause(2, 4)

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


def extract_post_data(page, post_url: str, index: int) -> dict | None:
    """Extrae todos los datos de un post individual."""
    try:
        page.goto(post_url, wait_until="networkidle", timeout=30000)
        random_pause(2, 4)

        page.evaluate("window.scrollBy(0, 100)")
        random_pause(1, 2)

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

        # ── 2 y 3. Caption, Likes y Comentarios vía meta tag ──────────
        try:
            meta_locator = page.locator('meta[property="og:description"], meta[name="description"]').first
            content = meta_locator.get_attribute("content", timeout=3000)

            if content:
                if ":" in content:
                    data["caption"] = content.split(":", 1)[1].strip().strip('"').strip('\u201c').strip('\u201d')
                else:
                    data["caption"] = content

                likes_match = re.search(r'([\d,.]+)\s*(likes|Me gusta)', content, re.IGNORECASE)
                if likes_match:
                    data["likes"] = likes_match.group(1).replace(',', '')

                comments_match = re.search(r'([\d,.]+)\s*(comments|comentarios)', content, re.IGNORECASE)
                if comments_match:
                    data["comments_count"] = comments_match.group(1).replace(',', '')

        except Exception as e:
            print(f"    [!] Aviso: No se pudo extraer la etiqueta meta en {post_url}: {e}")

        # ── 4. Imágenes y Videos ──────────────────────────────────────
        try:
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
        page.screenshot(path=RESULTS_DIR / f"timeout_post_{index}.png")
        return None
    except Exception as e:
        print(f"  [{index}] ❌ Error en {post_url}: {e}")
        return None