import os
import requests

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def send_log(message: str):
    """
    Mengirim log ke Discord via Webhook.
    Jika DISCORD_WEBHOOK tidak di-set, fungsi tetap jalan tanpa error.
    """

    if not WEBHOOK:
        print("[WARN] DISCORD_WEBHOOK tidak ditemukan, skip notifikasi.", flush=True)
        return

    payload = {
        "content": message
    }

    try:
        r = requests.post(WEBHOOK, json=payload, timeout=5)
        if r.status_code != 204 and r.status_code != 200:
            print(f"[WARN] Discord response: {r.status_code} {r.text}", flush=True)
    except Exception as e:
        print(f"[WARN] Gagal mengirim ke Discord: {e}", flush=True)
