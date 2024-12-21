import json
import requests
import time

NTFY_TOPIC = ""
ICON = "https://www.wgzimmer.ch/.resources/wgzimmer/webresources/legacy/social-icons/android-icon-192x192.png"


def notify(listing):
    title = "🏠 WG Zimmer: {location}, {date}, {price} CHF"

    message = """
Location: {location}, {location_extra}
Posted on: {posted}
Date: {date}
Price: {price} CHF
URL: {url}
"""

    requests.post(
        "https://ntfy.sh/",
        data=json.dumps(
            {
                "topic": NTFY_TOPIC,
                "message": message.format(**listing),
                "title": title.format(**listing),
                "icon": ICON,
                "actions": [
                    {"action": "view", "label": "Show Listing", "url": listing["url"]}
                ],
            }
        ),
    )

def send_error(e):
    while True:
        try:
            requests.post(
                "https://ntfy.sh/",
                data=json.dumps(
                    {
                        "topic": NTFY_TOPIC,
                        "title": "❌ Error checking WG Zimmer!",
                        "message": str(e),
                        "icon": ICON,
                    }
                ),
                headers={"Priority": "2"},
            )

            break
        except Exception as eIn:
            print(e)
            time.sleep(5)

def send_done(new, cache):
    requests.post("https://ntfy.sh/", data=json.dumps({
                        "topic": NTFY_TOPIC,
                        "title": "Done checking for new listings!",
                        "message": f"Found {new} new listings\n\nLast checked:\n"
                        + "\n".join(
                            [f"- {k}: {v}" for k, v in cache["last_checked"].items()]
                        ),
                        "icon": ICON,
                    }
                ),
                headers={"Priority": "1", "Markdown": "yes"},
            )