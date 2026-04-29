import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PRIMARY_USER  = os.getenv("INSTAGRAM_USERNAME")
PRIMARY_PASS  = os.getenv("INSTAGRAM_PASSWORD")
BACKUP_USER   = os.getenv("INSTAGRAM_USERNAME_BACKUP")
BACKUP_PASS   = os.getenv("INSTAGRAM_PASSWORD_BACKUP")
SESSION_FILE  = Path("cookies.json")
RESULTS_DIR   = Path("output")
RESULTS_DIR.mkdir(exist_ok=True)