
# Google Maps Reviews Scraper

A Python-based web scraper that collects user reviews from Google Maps pages of institutions and organizations. This tool extracts structured data including organization name, address, city, review content, author, rating, and date — saving everything to a JSON file for further analysis.

## Features

- Expands shortened Google Maps URLs (e.g., goo.gl, g.co)
- Headless Chrome support via Selenium
- Automatically detects and clicks the “Reviews” tab
- Extracts:
  - Institution Name
  - Category (if available)
  - Full Address
  - City (parsed from the address)
  - Author, Date, Rating, and Content of Reviews
- Filters reviews written within the last 3 years
- Handles dynamic loading via infinite scrolling
- Saves results as `.json` in a clean and safe format with fallback logic

## Requirements

- Python 3.7+
- Google Chrome installed
- Google ChromeDriver (auto-managed)

### Python Packages

Install required packages with:

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

## Usage

### 1. Scrape a single Google Maps link

```bash
python google-maps-scraper.py "https://www.google.com/maps/place/..." 50 true
```

### 2. Scrape multiple URLs from a file

Put one URL per line in a `.txt` file (e.g., `links.txt`), then run:

```bash
python google-maps-scraper.py links.txt 50 true
```

### Parameters

| Argument         | Description                                            |
|------------------|--------------------------------------------------------|
| `<url or file>`  | Google Maps link OR path to `.txt` file with URLs     |
| `[max_reviews]`  | Max reviews per location (default = 30)               |
| `[headless]`     | Optional: use `"false"` to see browser window         |

## Output

All JSON files are saved in the `all_reviews/` directory. Filenames are sanitized versions of the organization name.

Example output:
```json
[
  {
    "city": "Vinnytsia",
    "organization": "ЦНАП Вінниці",
    "author": "Ivan Petrenko",
    "date": "2023-08-10",
    "rating": "4.0",
    "content": "Зручно, швидко, персонал ввічливий."
  }
]
```

## Notes

- The scraper only saves reviews with non-empty content and recent dates (≤ 3 years old).
- The city name is heuristically extracted from the address.
- Layout changes on Google Maps may affect selector reliability.

## Troubleshooting

- No reviews loaded? Check if the page has a “Reviews” tab or if you’re blocked by CAPTCHA.
- ChromeDriver issues? Ensure your installed Chrome version matches the auto-installed ChromeDriver.

## License

MIT License. Feel free to fork, improve, and use this tool for civic tech, research, or other applications.
