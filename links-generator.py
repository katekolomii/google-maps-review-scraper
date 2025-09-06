import requests
import time

API_KEY = ''  # Insert your real API key here

radius = 50000  # 50 km

locations = [
    "50.4501,30.5234",  # Київ — центр
    "50.9000,30.5234",  # Північ (Димерський/Іванківський напрямок)
    "50.7500,31.2000",  # Пн.-схід (Бровари/Баришівка), в межах області
    "50.4500,31.2230",  # Схід (не виходимо в Полтавську)
    "50.1000,31.1500",  # Пд.-схід (Переяслав)
    "49.9990,30.5234",  # Південь (Обухів/Українка/Ржищів)
    "50.0500,29.9500",  # Пд.-захід (Васильків/Фастів)
    "50.4500,29.8230",  # Захід (Макарів)
    "50.8000,29.9500",  # Пн.-захід (Буча/Ірпінь/Бородянка)
]

place_types = [
    "local_government_office",
    "city_hall",
    "courthouse",
    "university",
]

EXCLUDE_KEYWORDS = [
    # Visa / docs
    "візовий", "visa", "вфс", "vfs", "пп документ",

    # Addiction treatment
    "addiction treatment center", "rehab", "rehabilitation", "detox", "detoxification",
    "drug treatment", "substance abuse", "alcohol rehab", "drug rehab", "methadone clinic",
    "sobriety center", "treatment facility", "12-step program",
    "наркоцентр", "наркологічний центр", "лікування залежностей", "лікування адикцій",
    "реабілітаційний центр", "реабілітація", "центр реабілітації",
    "центр лікування наркоманії", "центр лікування алкоголю",
    "наркологія", "наркологічна клініка", "лікування від наркотиків",
    "лікування від алкоголю", "клініка залежностей", "терапія залежностей",
    "нарко центр", "реаб центр", "реаб. центр", "rehab center", "reab", "реаб",

    # Private hospitals / clinics
    "приватна лікарня", "приватна клініка", "приватний медичний центр",
    "приватний госпіталь", "приватний медцентр", "приватний мед заклад",
    "private hospital", "private clinic", "private medical center",
    "private healthcare", "private infirmary",

    # Lawyers / legal
    "адвокат", "адвокатське бюро", "адвокатська компанія", "адвокатське об'єднання",
    "юридична фірма", "юридична компанія", "юридичні послуги", "правова допомога",
    "правова консультація", "юрист", "юридичн",  # стем ловить: юридична/юридичні/…
    "lawyer", "attorney", "law firm", "legal services", "legal aid", "solicitor", "barrister", 

    # Private schools
    "приватна школа", "приватний навчальний заклад", "приватний ліцей", "приватний коледж",
    "private school", "private high school", "private academy", "private college",

    # Private universities
    "приватний університет", "приватний інститут", "приватна академія",
    "private university", "private institute", "private academy",
]

# ---------- helpers ----------

EXCLUDE_KEYWORDS_LOWER = [k.lower() for k in EXCLUDE_KEYWORDS]

def name_excluded(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in EXCLUDE_KEYWORDS_LOWER)

def is_in_kyiv_region(address_components):
    """True для Київської області (Київська область)."""
    allowed_regions = {
        "Kyiv Oblast", "Kyivs'ka oblast", "Kyivska oblast", "Київська область"
    }
    for comp in address_components or []:
        types = set(comp.get("types", []))
        if "administrative_area_level_1" in types:
            ln = comp.get("long_name", "")
            sn = comp.get("short_name", "")
            if ln in allowed_regions or sn in allowed_regions:
                return True
    return False

def is_in_kyiv_city(address_components):
    """True для міста Київ (окремий адмін-субʼєкт)."""
    allowed_cities = {"Kyiv", "Київ", "misto Kyiv", "місто Київ"}
    for comp in address_components or []:
        types = set(comp.get("types", []))
        if "locality" in types or "administrative_area_level_1" in types:
            ln = comp.get("long_name", "")
            sn = comp.get("short_name", "")
            if ln in allowed_cities or sn in allowed_cities:
                return True
    return False

def accept_kyiv_region_or_city(address_components):
    return is_in_kyiv_region(address_components) or is_in_kyiv_city(address_components)

def fetch_place_details(place_id: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "address_components,name,url",
        "key": API_KEY
    }
    r = requests.get(url, params=params, timeout=15)
    if not r.ok:
        return {}
    data = r.json()
    return data.get("result", {})

def nearby_page(params: dict) -> dict:
    """Обробка паузи для next_page_token (2–5s) за рекомендацією Google."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    for _ in range(6):  # ~12–15s максимум
        resp = requests.get(url, params=params, timeout=20)
        data = resp.json()
        status = data.get("status")
    
        if status == "OK" and "results" in data:
            return data
        if status == "INVALID_REQUEST" and "pagetoken" in params:
            time.sleep(2.5)
            continue
        # для ZERO_RESULTS/OVER_QUERY_LIMIT/ін. — повертаємо як є
        return data
    return data

# ---------- main ----------

results = set()       # лінки (по place_id) — фінальний вивід
seen_place_ids = set()  # щоб не дублювати між точками/типами

for place_type in place_types:
    for location in locations:
        params = {
            "location": location,
            "radius": radius,
            "type": place_type,
            "key": API_KEY
        }

        data = nearby_page(params)
        while True:
            for place in data.get("results", []):
                place_id = place.get("place_id")
                if not place_id or place_id in seen_place_ids:
                    continue

                # "мʼякий" фільтр по назві (виключення)
                if name_excluded(place.get("name")):
                    continue

                # Жорсткий фільтр за областю/містом — тягнемо Place Details
                details = fetch_place_details(place_id)
                comps = details.get("address_components", [])
                if not accept_kyiv_region_or_city(comps):
                    continue

                # Пройшло фільтр — додаємо
                maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                results.add(maps_link)
                seen_place_ids.add(place_id)

            token = data.get("next_page_token")
            if not token:
                break

            # При використанні pagetoken, Google вимагає тільки key + pagetoken
            data = nearby_page({"pagetoken": token, "key": API_KEY})

# ---------- save ----------

output_path = "kyiv_gov_links_only.txt"
with open(output_path, "w", encoding="utf-8") as f:
    for link in sorted(results):
        f.write(link + "\n")

print(f"Збережено {len(results)} унікальних посилань у '{output_path}'")