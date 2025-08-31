# 🗺️ Google Maps Scraper & Links Generator  

A Python-based toolkit for generating Google Maps search links and collecting **user reviews and metadata** from institution pages.  
It is designed for structured data extraction, making it suitable for research, civic tech, and large-scale institutional analysis.  

---

## 📂 Project Structure  

- **`links-generator.py`**  
  Generates Google Maps search links from a list of institution names or categories.  
  Useful for preparing input files for large-scale scraping.  

- **`google-maps-scraper.py`**  
  Scrapes institution data (name, address, city, reviews, etc.) from Google Maps pages using Selenium.  

---

## ✨ Features  

- 🔗 **Link Generation**:  
  - Converts institution lists into Google Maps search URLs.  
  - Ensures full, valid links for scraping.  

- 🖥️ **Scraper Core**:  
  - Supports **headless Chrome** automation via Selenium.  
  - Expands shortened Google Maps links (e.g., `goo.gl`, `g.co`).  
  - Automatically detects and clicks the “Reviews” tab.  
  - Scrolls dynamically to load more reviews.  

- 📍 **Metadata Extraction**:  
  - Institution/Organization Name  
  - Category (if available)  
  - Full Address  
  - City (parsed from address)  

- 📝 **Review Extraction**:  
  - Author Name  
  - Date (normalized with `dateparser`)  
  - Rating (1–5 stars)  
  - Review Text  

- 🕒 **Filtering**: Keeps reviews from the **last 3 years** only.  

- 📂 **Output**:  
  - Saves each institution as a `.json` file in `all_reviews/`.  
  - Skips saving if no reviews are found.  
  - Handles duplicate filenames by appending `_1`, `_2`, etc.  

---

## ⚙️ Requirements  

- **Python 3.7+**  
- **Google Chrome** installed  
- **Google ChromeDriver** (managed by `webdriver-manager`)  

### Python Packages  

Install dependencies with:  

```bash
pip install -r requirements.txt
```  

**requirements.txt**  
```
selenium
webdriver-manager
pandas
dateparser
requests
```

---

## 🚀 Usage  

### 1. Generate Google Maps Links  

From a CSV or TXT file with institution names:  

```bash
python links-generator.py --input institutions.csv --output links.txt
```  

- `--input` → CSV/TXT file with institution names or categories  
- `--output` → File where generated Google Maps links will be saved  

---

### 2. Scrape Google Maps Data  

Using a single URL:  

```bash
python google-maps-scraper.py "https://www.google.com/maps/place/..." 50 true
```  

Using multiple URLs from a file:  

```bash
python google-maps-scraper.py links.txt 50 true
```  

---

## 🔧 Scraper Parameters  

| Argument         | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `<url or file>`  | Google Maps link **OR** path to `.txt` file containing multiple URLs        |
| `[max_reviews]`  | Max number of reviews per location (default = `30`)                         |
| `[headless]`     | Run headless Chrome (`true` = no UI, `false` = visible browser window)       |

---

## 📊 Output Example  

All results are saved inside the `all_reviews/` directory.  

Example JSON output:  

```json
[
  {
    "city": "Vinnytsia",
    "organization": "ЦНАП Вінниці",
    "author": "Ivan Petrenko",
    "date": "2023-08-10",
    "rating": "4.0",
    "content": "Зручно, швидко, персонал ввічливий."
  },
  {
    "city": "Vinnytsia",
    "organization": "ЦНАП Вінниці",
    "author": "Olena Koval",
    "date": "2024-04-02",
    "rating": "5.0",
    "content": "Чудовий сервіс!"
  }
]
```

---

## 🛠️ Troubleshooting  

- **No reviews loaded?**  
  - Ensure the place has a “Reviews” tab.  
  - Check for CAPTCHA restrictions on Google Maps.  

- **ChromeDriver issues?**  
  - Ensure your Chrome version matches the auto-installed driver.  
  - Clear cache in `~/.wdm/` if needed.  

- **Empty JSON file?**  
  - Script skips saving if no valid reviews are found.  
  - Double-check URLs are valid Google Maps links.  

---

## ⚖️ Notes  

- Only **non-empty, recent (≤ 3 years old)** reviews are saved.  
- City names are parsed heuristically and may require cleaning.  
- Google Maps layout updates can break selectors — adjust code if needed.  
- Intended for **educational, research, and civic tech purposes only**.  
  Respect Google’s [Terms of Service](https://policies.google.com/terms).  

---

## 📜 License  

MIT License.  
Free to fork, improve, and adapt for your projects.  
