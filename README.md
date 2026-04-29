## ¿Qué hace el programa?

Extrae información pública de posts de perfiles de Instagram de forma automatizada. Por cada post recolecta la fecha de publicación, el caption, la cantidad de likes, la cantidad de comentarios y las URLs de imágenes y videos. Los datos se guardan en un archivo `.json` dentro de la carpeta `output/`.

---

## ¿Cómo funciona el scraping?

1. **Autenticación**: El programa inicia sesión con las credenciales de Instagram y guarda las cookies en `cookies.json` para no tener que loguearse en cada ejecución. Si la cuenta principal está bloqueada o suspendida, cambia automáticamente a una cuenta de respaldo.

2. **Recolección de URLs**: Visita el perfil indicado y hace scroll hacia abajo para recolectar los enlaces de los posts hasta alcanzar el número configurado.

3. **Extracción de datos**: Entra a cada post individualmente y extrae la información desde la etiqueta meta `og:description` que Instagram incluye en el HTML, lo que hace la extracción más estable que depender del DOM visual.

4. **Pausas aleatorias** — Entre cada acción se introducen delays aleatorios para imitar comportamiento humano y reducir la probabilidad de bloqueos.

## Librerías utilizadas
Librería: Uso
`playwright`: Automatización del navegador (navegación, clicks, scroll) 
`python-dotenv`: Lectura de credenciales desde el archivo `.env` 
`re`: Expresiones regulares para extraer likes y comentarios 
`json`: Serialización de datos y manejo de cookies 
`pathlib`: Manejo de rutas de archivos 

> No se usa BeautifulSoup ni Selenium. Playwright fue elegido por su mayor estabilidad con sitios modernos que renderizan con JavaScript.

## ¿Cómo ejecutarlo?

**1. Instalar dependencias**
```bash
pip install playwright python-dotenv
playwright install chromium
```

**2. Configurar credenciales** — Crea un archivo `.env` en la raíz del proyecto:
```env
INSTAGRAM_USERNAME=tu_usuario
INSTAGRAM_PASSWORD=tu_contraseña
INSTAGRAM_USERNAME_BACKUP=usuario_respaldo
INSTAGRAM_PASSWORD_BACKUP=contraseña_respaldo
```

**3. Ejecutar**
```bash
python main.py
```

El programa pedirá el enlace del perfil a scrapear y extraerá 2 posts por defecto. Los resultados se guardarán en `output/`.