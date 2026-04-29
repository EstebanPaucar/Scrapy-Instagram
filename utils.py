import time
import random


def random_pause(min_s: float = 1.5, max_s: float = 3.5):
    """Pausa aleatoria para imitar comportamiento humano."""
    time.sleep(random.uniform(min_s, max_s))