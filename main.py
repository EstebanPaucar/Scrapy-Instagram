import json
from datetime import datetime
from playwright.sync_api import sync_playwright

from config import PRIMARY_USER, PRIMARY_PASS, RESULTS_DIR
from auth import initialize_auth, refresh_auth_if_needed
from scraper import collect_post_urls, extract_post_data
from utils import random_pause


def main():
    if not PRIMARY_USER or not PRIMARY_PASS:
        raise RuntimeError("❌ Define INSTAGRAM_USERNAME y INSTAGRAM_PASSWORD en tu archivo .env")

    TARGET_PROFILE = input("🔗 Ingresa el enlace del perfil de Instagram a scrapear → ").strip()
    MAX_POSTS = 2

    print("\n" + "═" * 50)
    print("  Instagram Scraper")
    print("═" * 50)
    print(f"  Perfil : {TARGET_PROFILE}")
    print(f"  Posts  : {MAX_POSTS}")
    print("═" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
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
        initialize_auth(page, context)

        # 2) Recolectar URLs de posts
        post_urls = collect_post_urls(page, TARGET_PROFILE, MAX_POSTS)

        # 3) Scraping post a post
        print(f"\n📥 Scrapeando {len(post_urls)} posts...")
        results = []
        for i, url in enumerate(post_urls, 1):
            if i % 20 == 0:
                refresh_auth_if_needed(page, context)

            post_data = extract_post_data(page, url, i)
            if post_data:
                results.append(post_data)

            random_pause(5, 10)

        # 4) Guardar resultados
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        profile_name = TARGET_PROFILE.rstrip("/").split("/")[-1]
        output_path = RESULTS_DIR / f"{profile_name}_{timestamp}.json"

        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Datos guardados en: {output_path}")
        print(f"📊 Posts extraídos exitosamente: {len(results)} / {len(post_urls)}")

        browser.close()


if __name__ == "__main__":
    main()