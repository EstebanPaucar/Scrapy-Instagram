# Instagram Scraper

Scraper de perfiles de Instagram usando Playwright con manejo automático de sesión.

## Datos que extrae por post
- URL del post
- Caption / descripción
- Likes
- Fecha de publicación
- URLs de imágenes y videos
- Comentarios visibles (hasta 20)

## Instalación

```bash
# 1. Clonar el repo e instalar dependencias
pip install -r requirements.txt
playwright install chromium

# 2. Configurar credenciales
cp .env.example .env
# Edita .env con tu usuario y contraseña de Instagram
```

## Configuración

Edita el archivo `.env`:
```
INSTAGRAM_USERNAME=tu_usuario
INSTAGRAM_PASSWORD=tu_contraseña
```

Edita la variable `TARGET_PROFILE` en `scraper.py`:
```python
TARGET_PROFILE = "https://www.instagram.com/el_perfil_que_quieras/"
```

## Uso

```bash
python scraper.py
```

El script te preguntará cuántos posts extraer. Los resultados se guardan en `output/`.

## Estructura del JSON de salida

```json
[
  {
    "url": "https://www.instagram.com/p/ABC123/",
    "scraped_at": "2024-01-15T10:30:00Z",
    "caption": "Texto del post...",
    "likes": "1,234 Me gusta",
    "comments_count": null,
    "date": "2024-01-10T08:00:00.000Z",
    "media_urls": ["https://...jpg"],
    "comments": ["Comentario 1", "Comentario 2"]
  }
]
```

## Notas importantes

- Usa una cuenta secundaria, no tu cuenta principal
- El scraper incluye delays aleatorios para evitar detección
- Las cookies se reutilizan para no hacer login en cada ejecución
- Si la sesión expira, el scraper hace login automáticamente
- `headless=False` está activado por defecto (ves el navegador) — cámbialo a `True` cuando estés seguro de que funciona
