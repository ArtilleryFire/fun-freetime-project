import os
import requests

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_log(message: str):
    """Kirim pesan teks ke Discord."""
    if not WEBHOOK:
        return

    try:
        requests.post(WEBHOOK, json={"content": message})
    except Exception:
        pass


def send_embed(title: str, description: str, color: int = 0x00FFAA):
    """Kirim embed Discord (opsional untuk notifikasi penting)."""
    if not WEBHOOK:
        return
    
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color
        }]
    }

    try:
        requests.post(WEBHOOK, json=payload)
    except Exception:
        pass
