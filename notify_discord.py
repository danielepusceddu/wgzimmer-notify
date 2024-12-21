import requests
import json

DISCORD_WEBHOOK_URL = ""

def notify(listing):
    title = f"🏠 WG Zimmer: {listing['location']}, {listing['date']}, {listing['price']} CHF"
    description = (
        f"**Location:** {listing['location']}, {listing['location_extra']}\n"
        f"**Posted on:** {listing['posted']}\n"
        f"**Date:** {listing['date']}\n"
        f"**Price:** {listing['price']} CHF\n"
        f"[View Listing]({listing['url']})"
    )
    
    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "url": listing["url"],
                "color": 16776960,  # Yellow color
                "footer": {"text": "WG Zimmer Notifications"},
            }
        ]
    }

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )
    
    if response.status_code != 204:
        print(f"Failed to send message: {response.status_code}, {response.text}")

import time

def send_error(e):
    while True:
        try:
            payload = {
                "embeds": [
                    {
                        "title": "❌ Error checking WG Zimmer!",
                        "description": str(e),
                        "color": 15158332,  # Red color
                        "footer": {"text": "Error Notifications"},
                    }
                ]
            }

            response = requests.post(
                DISCORD_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
            )

            if response.status_code == 204:
                break  # Successfully sent the message
            else:
                print(f"Failed to send error: {response.status_code}, {response.text}")
        except Exception as eIn:
            print(f"Exception during error notification: {eIn}")
            time.sleep(5)

def notify_done(new, cache):
    last_checked = "\n".join([f"- {k}: {v}" for k, v in cache["last_checked"].items()])
    description = (
        f"**Found {new} new listings**\n\n"
        f"**Last checked:**\n{last_checked}"
    )

    payload = {
        "embeds": [
            {
                "title": "✅ Done checking for new listings!",
                "description": description,
                "color": 3066993,  # Green color
                "footer": {"text": "Check Completed Notifications"},
            }
        ]
    }

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )

    if response.status_code != 204:
        print(f"Failed to send done notification: {response.status_code}, {response.text}")
