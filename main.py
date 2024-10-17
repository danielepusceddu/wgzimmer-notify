import requests
import json
import time
import random
from typing import Optional
from pprint import pprint
from bs4 import BeautifulSoup

from selenium import webdriver

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from fake_useragent import UserAgent

BASE = "https://www.wgzimmer.ch/wgzimmer/search/mate/ch/{0}.html"
ICON = "https://www.wgzimmer.ch/.resources/wgzimmer/webresources/legacy/social-icons/android-icon-192x192.png"

# The last one is the one for "Unterland" for some reason
WGSTATES = [
    "zurich-stadt",
    "zurich-oberland",
    "zurich-altstetten",
    "zurich-oerlikon",
    "zurich-lake",
    "zurich",
]

PRICEMAX = 800

PARAMS = {
    "priceMax": PRICEMAX,
    "student": "none",
    "permanent": "all",
    "typeofwg": "all",
}

SEEN_IDS = []


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
                "topic": TOPIC,
                "message": message.format(**listing),
                "title": title.format(**listing),
                "icon": ICON,
                "actions": [
                    {"action": "view", "label": "Show Listing", "url": listing["url"]}
                ],
            }
        ),
    )


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all("li", class_="search-result-entry", recursive=True)

    output = {}

    for result in results:
        if "search-result-entry-slot" in result["class"]:
            continue

        id = result["id"]
        output[id] = {
            "url": "https://www.wgzimmer.ch" + result.find("a", recursive=True)["href"]
        }

        posted = result.find("div", class_="create-date", recursive=True)
        if posted:
            output[id]["posted"] = posted.text.strip()

        location = result.find("span", class_="thumbState", recursive=True)
        if location:
            location_full = location.text.strip().split("\n")
            location = location_full[0]
            location_extra = (
                " ".join(location_full[1].split()) if len(location_full) > 1 else ""
            )

            output[id]["location"] = location
            output[id]["location_extra"] = location_extra

        date = result.find("span", class_="from-date", recursive=True)
        if date:
            output[id]["date"] = date.text.strip()

        price = result.find("span", class_="cost", recursive=True)
        if price:
            output[id]["price"] = price.text.strip()

    return output


def send_error(e):
    while True:
        try:
            requests.post(
                "https://ntfy.sh/",
                data=json.dumps(
                    {
                        "topic": TOPIC,
                        "title": "❌ Error checking WG Zimmer!",
                        "message": str(e),
                        "icon": ICON,
                    }
                ),
                headers={"Priority": "2"}
            )

            break
        except Exception as eIn:
            print(e)
            time.sleep(5)


def try_selenium(wgState: str) -> Optional[str]:
    try:
        userAgent = UserAgent().random

        profile = webdriver.FirefoxProfile()
        profile.set_preference("general.useragent.override", userAgent)

        geckodriver_path = "/snap/bin/geckodriver"
        driver_service = webdriver.FirefoxService(executable_path=geckodriver_path)

        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless")
        options.profile = profile

        driver = webdriver.Firefox(options=options, service=driver_service)

        driver.get("https://www.wgzimmer.ch/wgzimmer/search/mate.html")

        # Accept cookies
        try:
            driver.find_element(By.CLASS_NAME, "fc-cta-consent").click()
        except:
            pass

        time.sleep(random.randint(1, 5))

        # Price max
        price_max = Select(driver.find_element(By.NAME, "priceMax"))
        price_max.select_by_value(str(PRICEMAX))

        time.sleep(random.randint(1, 5))

        # Region
        region = Select(driver.find_element(By.NAME, "wgState"))
        region.select_by_value(wgState)

        time.sleep(random.randint(1, 5))

        # Search
        driver.find_element(By.CSS_SELECTOR, "input[value='Suchen']").click()

        time.sleep(5)

        return driver.page_source

    except Exception as e:
        print(e)
        return None

    finally:
        driver.close()


def main():
    while True:
        try:
            response = requests.get("https://one.one.one.one")
            break
        except Exception as e:
            print(e)
            time.sleep(5)
            pass

    try:
        listings = {}
        new = 0

        with open("seen.txt", "a+") as f:
            f.seek(0)
            SEEN_IDS.extend(f.read().splitlines())

        for wgstate in WGSTATES:
            response = requests.get(BASE.format(wgstate), params=PARAMS)

            if response.status_code == 200 and "search-result-list" in response.text:
                listings |= parse_html(response.text)
                continue

            print(f"Failed to get listings for {wgstate}, trying with Selenium...")

            html = try_selenium(wgstate)

            if html and "search-result-list" in html:
                listings |= parse_html(html)
            elif html and "Google reCaptcha" in html:
                send_error(f"Failed to get listings for {wgstate}, reCaptcha error.")
            else:
                send_error(f"Failed to get listings for {wgstate}, no results found.")

        for id, listing in listings.items():
            if id not in SEEN_IDS:
                SEEN_IDS.append(id)
                notify(listing)
                new += 1

        with open("seen.txt", "w") as f:
            f.write("\n".join(SEEN_IDS))

        requests.post(
            "https://ntfy.sh/",
            data=json.dumps(
                {
                    "topic": TOPIC,
                    "title": "Done checking for new listings!",
                    "message": f"Found {new} new listings",
                    "icon": ICON,
                }
            ),
            headers={"Priority": "1"}
        )

        print(f"Found {new} new listings")

    except Exception as eOut:
        send_error(eOut)


if __name__ == "__main__":
    main()
