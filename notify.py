import os
import requests

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_log(message):
    """Kirim pesan ke Discord menggunakan Webhook."""
    if not WEBHOOK:
        print("[WARN] DISCORD_WEBHOOK tidak ditemukan, skip notif.")
        return

    try:
        payload = {"content": message}
        requests.post(WEBHOOK, json=payload, timeout=5)
    except Exception as e:
        print(f"[WARN] Gagal kirim Discord: {e}")
