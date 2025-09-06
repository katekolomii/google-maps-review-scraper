import sys
import time
import json
import requests
import pandas as pd
import dateparser
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import re
from urllib.parse import urlparse, parse_qs, unquote

# ---------- helpers ----------
def expand_google_maps_url(short_url):
    try:
        response = requests.get(short_url, allow_redirects=True, timeout=10)
        if "google.com/maps" in response.url:
            print(f"[INFO] Expanded URL: {response.url}")
            return response.url
        print("[WARN] Expanded URL does not appear to be Google Maps.")
        return None
    except Exception as e:
        print(f"[ERROR] URL expansion failed: {e}")
        return None

def setup_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def dismiss_consent(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Прийняти всі')]"
            ))
        ).click()
        print("[INFO] Dismissed cookie consent.")
        time.sleep(2)
    except:
        pass

def click_reviews_button(driver):
    wait = WebDriverWait(driver, 4)
    possible_xpaths = [
        "//button[contains(., 'Відгуки')]",
        "//button[contains(., 'Reviews')]",
        "//button[contains(., 'All reviews')]",
        "//button[@aria-label='All reviews']",
        "//div[contains(@aria-label, 'Відгуки') or contains(@aria-label, 'Reviews')]",
    ]
    start_time = time.time()
    for xpath in possible_xpaths:
        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", button)
            print(f"[INFO] Clicked 'Reviews' tab via {xpath} in {time.time() - start_time:.2f}s")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.m6QErb"))
            )
            return True
        except:
            continue
    print(f"[WARN] 'Reviews' tab not found after {time.time() - start_time:.2f}s")
    return False

def get_full_place_name(driver):
    def clean(s):
        if not s:
            return ""
        s = s.replace("\u200b", "").replace("\u200e", "").replace("\u200f", "")
        s = s.strip(" \n\t·-|—–")
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"(…|\.{3})$", "", s).strip()
        return s

    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1[role='heading'], h1.DUwDvf, h1"))
        )
        h1 = driver.find_element(By.CSS_SELECTOR, "h1[role='heading'], h1.DUwDvf, h1")
        name = clean(h1.text or h1.get_attribute("aria-label") or "")
        if name and not name.endswith(("…", "...")):
            return name
    except:
        pass

    try:
        og = driver.execute_script(
            "const m=document.querySelector(\"meta[property='og:title']\");"
            "return m && m.content ? m.content : '';"
        ) or ""
        og = clean(og)
        if og:
            if " · " in og:
                og = og.split(" · ")[0].strip()
            return og
    except:
        pass

    try:
        t = clean(driver.title)
        if t:
            t = re.sub(r"\s*[·\-\|]\s*Google Maps.*$", "", t, flags=re.IGNORECASE).strip()
            return t
    except:
        pass

    return ""

# --- NEW: coordinate extractor ---
def get_coordinates(driver):
    """Returns (lat, lng) or (None, None)."""
    # 1) try @lat,lng in current URL
    try:
        url = driver.current_url or ""
        m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+),', url)
        if m:
            return float(m.group(1)), float(m.group(2))
    except:
        pass

    # 2) try og:image center=lat,lng
    try:
        og_img = driver.execute_script(
            "const m=document.querySelector(\"meta[property='og:image']\");"
            "return m && m.content ? m.content : '';"
        ) or ""
        if og_img:
            qs = parse_qs(urlparse(og_img).query)
            if "center" in qs and qs["center"]:
                parts = unquote(qs["center"][0]).split(",")
                if len(parts) == 2:
                    return float(parts[0]), float(parts[1])
    except:
        pass

    # 3) fallback: canonical URL with @lat,lng
    try:
        canon = driver.execute_script(
            "const l=document.querySelector(\"link[rel='canonical']\");return l && l.href ? l.href : '';"
        ) or ""
        m2 = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+),', canon)
        if m2:
            return float(m2.group(1)), float(m2.group(2))
    except:
        pass

    return None, None

def get_review_rating(review):
    """
    Tries multiple locale-safe selectors and pulls the number from aria-label/text.
    Returns a string like '4.0' or '' if not found.
    """
    candidates = [
        "span[aria-label*='stars']",
        "span[aria-label*='Rated']",
        "span[aria-label*='Оцінка']",      # uk
        "span[aria-label*='рейтинг']",     # uk/ru
        "span[aria-label*='зв']",          # ru: звезды/звездами
        "span[aria-label*='estrellas']",   # es
    ]
    for sel in candidates:
        try:
            els = review.find_elements(By.CSS_SELECTOR, sel)
            if els:
                text = (els[0].get_attribute("aria-label") or els[0].text or "").strip()
                m = re.search(r"(\d+(?:[.,]\d+)?)", text)
                if m:
                    return m.group(1).replace(",", ".")
        except:
            pass

    # Fallback: sometimes the rating is on a role="img" node
    try:
        els = review.find_elements(By.CSS_SELECTOR, "[role='img'][aria-label]")
        for el in els:
            txt = (el.get_attribute("aria-label") or "").lower()
            if any(k in txt for k in ["star", "зір", "звезд", "оцінк", "rate"]):
                m = re.search(r"(\d+(?:[.,]\d+)?)", txt)
                if m:
                    return m.group(1).replace(",", ".")
    except:
        pass

    return ""

# ---------- page parsers ----------
def collect_place_info(driver):
    wait = WebDriverWait(driver, 10)
    info = {}

    try:
        name_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf")))
        name = (name_elem.text or "").strip()
    except:
        name = ""
    if not name or name.endswith(("…", "...")):
        name = get_full_place_name(driver)
    info["Name"] = name or ""

    try:
        category_elem = driver.find_element(By.CSS_SELECTOR, "button.DkEaL")
        info["Category"] = category_elem.text.strip()
    except:
        info["Category"] = ""

    try:
        address_elem = driver.find_element(By.XPATH, "//button[@data-item-id='address']")
        info["Address"] = address_elem.text.strip()
    except:
        try:
            address_elem = driver.find_element(By.CSS_SELECTOR, "span.UsdlK")
            info["Address"] = address_elem.text.strip()
        except:
            try:
                address_elem = driver.find_element(By.CSS_SELECTOR, "div.LrzXr")
                info["Address"] = address_elem.text.strip()
            except:
                info["Address"] = ""

    # NEW: coordinates
    lat, lng = get_coordinates(driver)
    info["Lat"] = lat
    info["Lng"] = lng

    return info

def parse_relative_date(text):
    cleaned_text = text.lower().replace("edited", "").replace("змінено", "").strip()
    parsed_date = dateparser.parse(
        cleaned_text,
        settings={
            "RELATIVE_BASE": datetime.now(),
            "PREFER_DATES_FROM": "past",
            "DATE_ORDER": "DMY"
        },
        languages=["uk", "ru", "en"]
    )

    if not parsed_date:
        now = datetime.now()
        if "рік тому" in cleaned_text or "a year ago" in cleaned_text:
            parsed_date = now - timedelta(days=365)
        elif re.search(r"\d+\s+роки? тому", cleaned_text):
            years = int(re.search(r"\d+", cleaned_text).group())
            parsed_date = now - timedelta(days=365 * years)
        elif "місяць тому" in cleaned_text or "a month ago" in cleaned_text:
            parsed_date = now - timedelta(days=30)
        elif re.search(r"\d+\s+місяц[яів]+ тому", cleaned_text):
            months = int(re.search(r"\d+", cleaned_text).group())
            parsed_date = now - timedelta(days=30 * months)
        elif "тиждень тому" in cleaned_text or "a week ago" in cleaned_text:
            parsed_date = now - timedelta(weeks=1)
        elif re.search(r"\d+\s+тижн[яів]+ тому", cleaned_text):
            weeks = int(re.search(r"\d+", cleaned_text).group())
            parsed_date = now - timedelta(weeks=weeks)
        elif "день тому" in cleaned_text or "a day ago" in cleaned_text:
            parsed_date = now - timedelta(days=1)
        elif re.search(r"\d+\s+дн[яів]+ тому", cleaned_text):
            days = int(re.search(r"\d+", cleaned_text).group())
            parsed_date = now - timedelta(days=days)

    return parsed_date.strftime("%Y-%m-%d") if parsed_date else "Unknown"

# NEW: include lat/lng in each record
def scrape_reviews(driver, max_reviews, institution_name, city, organization, lat, lng):
    wait = WebDriverWait(driver, 15)
    reviews = []
    try:
        scrollable = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde")
        ))
    except:
        scrollable = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.m6QErb")))

    print("[INFO] Located scrollable reviews container.")

    stagnant_scrolls = 0
    start_time = time.time()

    while len(reviews) < max_reviews and (time.time() - start_time) < 300:
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable)
        for _ in range(5):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable)
            time.sleep(0.2)
        new_reviews = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")

        if len(new_reviews) == len(reviews):
            stagnant_scrolls += 1
        else:
            stagnant_scrolls = 0

        reviews = new_reviews
        if stagnant_scrolls > 15:
            print("[INFO] No more reviews are loading.")
            break

    if not reviews:
        return []

    data = []
    for review in reviews:
        try:
            author = review.find_element(By.CSS_SELECTOR, 'div.d4r55').text
        except:
            try:
                author = review.find_element(By.CSS_SELECTOR, 'span.X5PpBb').text
            except:
                author = None

        rating = get_review_rating(review)

        try:
            date_text = review.find_element(By.CSS_SELECTOR, "span.rsqaWe").text.strip()
            date = parse_relative_date(date_text)
        except:
            date = "Unknown"

        try:
            read_more = review.find_element(By.CSS_SELECTOR, "button.LkLjZd.ScJHi.OzU4dc")
            driver.execute_script("arguments[0].click();", read_more)
            time.sleep(0.1)
        except:
            pass

        try:
            content = review.find_element(By.CSS_SELECTOR, "span.wiI7pd").text.strip()
        except:
            content = ""

        if content and len(content) > 5:
            data.append({
                "city": city,
                "organization": organization,
                "author": author,
                "date": date,
                "rating": rating,
                "content": content,
                "lat": lat,
                "lng": lng
            })

        if len(data) >= max_reviews:
            break

    return data

# ---------- main ----------
def main():
    if len(sys.argv) < 2:
        print("Usage: python google-maps-scraper.py <input_file_or_url> [max_reviews] [headless]")
        sys.exit(1)

    input_arg = sys.argv[1]
    max_reviews = int(sys.argv[2]) if len(sys.argv) >= 3 else 30
    headless_mode = not (len(sys.argv) >= 4 and sys.argv[3].lower() == "false")

    if input_arg.endswith(".txt"):
        with open(input_arg, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    else:
        urls = [input_arg]

    driver = setup_driver(headless=headless_mode)
    all_reviews = []

    combined_output_path = os.path.join("all_reviews", "all_reviews_combined.json")
    os.makedirs("all_reviews", exist_ok=True)
    if os.path.exists(combined_output_path):
        with open(combined_output_path, "r", encoding="utf-8") as f:
            try:
                all_reviews = json.load(f)
            except:
                all_reviews = []

    for idx, url in enumerate(urls, start=1):
        if any(short in url for short in ["goo.gl", "g.co", "maps.app.goo.gl"]):
            expanded_url = expand_google_maps_url(url)
            if expanded_url:
                url = expanded_url
            else:
                continue

        driver.get(url)
        dismiss_consent(driver)
        time.sleep(2)

        place_info = collect_place_info(driver)
        if not click_reviews_button(driver):
            continue


        name = place_info.get("Name", "") or get_full_place_name(driver) or "Unknown"
        organization = name
        address = place_info.get("Address", "")
        parts = [part.strip() for part in address.split(",")] if address else []
        city = parts[-3] if len(parts) >= 3 else "Unknown"

        lat = place_info.get("Lat")
        lng = place_info.get("Lng")

         # 📌 Print with organization #
        print(f"[INFO] Organization #{idx}: {organization} ({city}) [{lat}, {lng}]")

        reviews = scrape_reviews(driver, max_reviews, name, city, organization, lat, lng)
        if reviews:
            all_reviews.extend(reviews)

    driver.quit()

    with open(combined_output_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved all {len(all_reviews)} reviews to {combined_output_path}.")

if __name__ == "__main__":
    main()