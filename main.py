import requests
import json
import time
import random
import tomllib
from datetime import datetime
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
NTFY_TOPIC = ""

SEEN_IDS = []


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


def try_selenium(wgState: str, priceMax: str) -> Optional[str]:
    driver = None

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
        price_max.select_by_value(priceMax)

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
        if driver:
            driver.close()


def main():
    global SEEN_IDS

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
        config = {}
        params = {}
        cache = {}
        new = 0

        with open("config.toml", "rb") as f:
            config = tomllib.load(f)
            params = {
                "priceMax": config["wgzimmer"]["priceMax"],
                "student": config["wgzimmer"]["student"],
                "permanent": config["wgzimmer"]["permanent"],
                "typeofwg": config["wgzimmer"]["typeofwg"],
            }

            notifiertype = config["notifier"]["type"]
            if notifiertype == "discord":
                from notify_discord import DiscordNotifier
                notifier = DiscordNotifier(config["discord"]["main_webhook"], config["discord"]["log_webhook"])
            elif notifiertype == "ntfy":
                from notify_ntfy import NtfyNotifier
                notifier = NtfyNotifier(config["ntfy"]["topic"])


        with open("cache.json", "r") as f:
            cache = json.load(f)
            SEEN_IDS = cache["seen"]

        print("Loaded config and cache")

        for wgstate in config["wgzimmer"]["wgStates"]:
            response = requests.get(BASE.format(wgstate), params=params)

            if response.status_code == 200 and "search-result-list" in response.text:
                listings |= parse_html(response.text)
            else:

                print(f"Failed to get listings for {wgstate}, trying with Selenium...")
                html = try_selenium(wgstate, str(config["wgzimmer"]["priceMax"]))

                if html and "search-result-list" in html:
                    listings |= parse_html(html)
                elif html and "Google reCaptcha" in html:
                    # send_error(f"Failed to get listings for {wgstate}, reCaptcha error.")
                    continue
                else:
                    # send_error(f"Failed to get listings for {wgstate}, no results found.")
                    continue

            if "last_checked" not in cache:
                cache["last_checked"] = {}

            cache["last_checked"][wgstate] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        for id, listing in listings.items():
            if id not in SEEN_IDS:
                SEEN_IDS.append(id)
                notifier.notify(listing)
                new += 1

        with open("cache.json", "w") as f:
            cache["seen"] = SEEN_IDS
            json.dump(cache, f, indent=4)

        notifier.notify_done(new, cache)

        print(f"Found {new} new listings")

    except Exception as eOut:
        print(eOut)
        notifier.send_error(eOut)


if __name__ == "__main__":
    main()
