# Jakarta Running Festival (JRF) 2026 — Race Analytics Dashboard & Results API

Complete official race telemetry, interactive HTML analytics dashboard, and OpenAPI 3.0.0 JSON datasets for the **Jakarta Running Festival (Day 1 & Day 2)** — covering **36,306 registered runners** and **30,602 official finishers** across all 4 distance categories.

---

## Interactive Race Analytics Dashboard (`dashboard.html` / `index.html`)

This repository includes a self-contained, zero-dependency interactive HTML dashboard (**`dashboard.html`** and **`index.html`**) that works offline in any browser or hosted directly via **GitHub Pages**:

- **Live GitHub Pages URL (once enabled in repo Settings → Pages):**
  `https://gbudidarma.github.io/jrf2026-results-api/`
- **Local File:** Open `dashboard.html` or `index.html` directly in Chrome, Safari, Edge, or Firefox.

### Dashboard Features
1. **Completion & Attrition Telemetry:** Real-time KPI cards and visual progress bars for **Finish Rate (`FINISHED %`)**, **Did Not Finish (`DNF %`)**, **Over Time Limit (`CUT %`)**, **Did Not Start (`DNS %`)**, **Average Pace (`/km`)**, and **Average/Median/Best Finish Time** across all events or filtered to a single race.
2. **Event-by-Event Performance Matrix & Finish Time Histogram:** Compare all 4 races side-by-side or inspect finish-time distribution buckets and Male vs. Female average paces for any specific distance.
3. **Country Joiners & Nationality Pie Charts:**
   - **All Joiners Pie Chart:** Domestic (`Indonesia`) vs. `International` participant split.
   - **International Joiners Pie Chart:** Share across foreign nations (`Malaysia`, `Japan`, `Singapore`, `Kenya`, `United States`, `Australia`, `China`, `India`, etc.).
   - **Top 10 Countries Table:** Click any country row or pie slice to filter the runner results table by nationality.
4. **Collapsible Category Winners & Podiums (`1st`, `2nd`, `3rd`):** Full podium cards and `#1` winner summary tables for every category (`TOP 3 OPEN`, `TOP 5 OPEN`, `TOP 3 NATIONAL`, `OPEN`, `NATIONAL`, `MASTER NATIONAL 40-49`, `MASTER NATIONAL 50+`) across Male and Female divisions, with per-event **Collapse / Expand** and global **Expand All / Collapse All** controls.
5. **All-Events Runner Search & Detailed Results Table (Footer):**
   - Instant search across all **36,306 runners** by **Runner Name**, **Bib Number**, or **Country**.
   - Multi-filter controls for **Event**, **Category**, **Gender**, and **Status** (`FINISHED`, `DNF`, `CUT`, `DNS`, `DQ`, `QRY`).
   - Displays **Overall Position / Status** and **Category Rank** (`🥇 #1`, `🥈 #2`, `🥉 #3`, `#4+`), defaulting to **10 rows per page** (`10`, `25`, `50`, or `100` selectable).
   - Click any runner row to open the **Checkpoint Split Times Drawer** (`KM 5`, `KM 10`, `KM 15`, `KM 20`, `KM 21.1`, `KM 25`, `KM 30`, `KM 35`, `KM 40`, and `FINISH`).

---

## Race Telemetry Summary (Day 1 & Day 2)

| Event | Race Day | Distance | Total Registered | Finishers (`%`) | DNF (`%`) | CUT (`%`) | DNS (`%`) | Avg Finish Time | Avg Pace |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: |
| **myBCA Jakarta Half Marathon** | Day 1 | `21.1 KM` | `14,684` | `12,684` (`86.38%`) | `714` (`4.86%`) | `118` (`0.80%`) | `1,167` (`7.95%`) | `02:45:17` | `7:50 /km` |
| **Samsung Galaxy 5K** | Day 1 | `5.0 KM` | `4,761` | `4,048` (`85.02%`) | `7` (`0.15%`) | `72` (`1.51%`) | `634` (`13.32%`) | `00:43:23` | `8:41 /km` |
| **Hydroplus Marathon** | Day 2 | `42.195 KM` | `4,420` | `2,637` (`59.66%`) | `1,146` (`25.93%`) | `64` (`1.45%`) | `545` (`12.33%`) | `04:25:49` | `6:18 /km` |
| **Le Minerale 10K** | Day 2 | `10.0 KM` | `12,441` | `11,233` (`90.29%`) | `25` (`0.20%`) | `180` (`1.45%`) | `1,003` (`8.06%`) | `01:26:54` | `8:41 /km` |
| **All 4 Events Combined** | **Day 1 & 2** | **—** | **`36,306`** | **`30,602` (`84.29%`)** | **`1,892` (`5.21%`)** | **`434` (`1.20%`)** | **`3,349` (`9.22%`)** | **—** | **`8:07 /km`** |

---

## Repository Files

| File | Description |
| :--- | :--- |
| `dashboard.html` / `index.html` | Interactive Race Analytics & 36,306-Runner Search Dashboard |
| `openapi.json` | OpenAPI `3.0.0` specification ready for RapidAPI Hub import |
| `events.json` | Summary metadata for all 4 events, participant counts, and checkpoint lists |
| `jrf_all_results.json` | Combined JSON dataset of all `36,306` runners across all 4 events |
| `hydroplus_marathon_results.json` | Full Marathon (`42.195 KM`) JSON results (`4,420` records) |
| `mybca_jakarta_half_marathon_results.json` | Half Marathon (`21.1 KM`) JSON results (`14,684` records) |
| `le_minerale_10k_results.json` | 10K (`10.0 KM`) JSON results (`12,441` records) |
| `samsung_galaxy_5k_results.json` | 5K (`5.0 KM`) JSON results (`4,761` records) |
| `*_results.csv` | Raw scraped CSV files for each of the 4 events |
| `scrape_results.py` | Browser-based scraper script for ScoreNow race results |
| `export_json_and_openapi.py` | Converter script generating JSON datasets and `openapi.json` |
| `build_dashboard.py` | Generator script that builds `dashboard.html` and `index.html` |

---

## Available API Endpoints (RapidAPI / GitHub Raw)

| Method | Endpoint | Description | Records |
| :--- | :--- | :--- | ---: |
| `GET` | `/events.json` | Summary of all 4 race events, distances, participant counts, and checkpoint lists | 4 events |
| `GET` | `/{event_slug}_results.json` | Fetch results by event slug (`hydroplus_marathon`, `le_minerale_10k`, `mybca_jakarta_half_marathon`, `samsung_galaxy_5k`) | Varies |
| `GET` | `/hydroplus_marathon_results.json` | Full Marathon (42.2K) results & 10 split checkpoints | 4,420 |
| `GET` | `/mybca_jakarta_half_marathon_results.json` | Half Marathon (21.1K) results & 5 split checkpoints | 14,684 |
| `GET` | `/le_minerale_10k_results.json` | 10K race results & split checkpoints (`KM 3.9`, `KM 8.8`, `FINISH`) | 12,441 |
| `GET` | `/samsung_galaxy_5k_results.json` | 5K race results & split checkpoints (`KM 3.4`, `FINISH`) | 4,761 |
| `GET` | `/jrf_all_results.json` | Complete combined dataset across all 4 events | 36,306 |

---

## Quick Start API Tutorial

### 1. List All Race Events (`GET /events.json`)

```python
import requests

url = "https://YOUR-RAPIDAPI-HOST.p.rapidapi.com/events.json"
headers = {
    "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",
    "X-RapidAPI-Host": "YOUR-RAPIDAPI-HOST.p.rapidapi.com"
}

response = requests.get(url, headers=headers)
data = response.json()
for event in data["events"]:
    print(f"{event['event_name']} ({event['distance_km']} KM): {event['finishers_count']}/{event['total_participants']} finishers")
```

### 2. Fetch Event Results & Search for a Runner by Bib or Name

```javascript
const url = 'https://YOUR-RAPIDAPI-HOST.p.rapidapi.com/hydroplus_marathon_results.json';
const options = {
  method: 'GET',
  headers: {
    'X-RapidAPI-Key': 'YOUR_RAPIDAPI_KEY',
    'X-RapidAPI-Host': 'YOUR-RAPIDAPI-HOST.p.rapidapi.com'
  }
};

const response = await fetch(url, options);
const { metadata, results } = await response.json();

// Find a runner by Bib Number
const runner = results.find(r => r.bib_no === 'A14328');
console.log(runner);
```

### Example Runner Record
```json
{
  "event_slug": "hydroplus_marathon",
  "event_name": "Hydroplus Marathon",
  "race_day": "Day 2",
  "position": 1,
  "status": "FINISHED",
  "bib_no": "A14328",
  "name": "KIPRONO KOECH",
  "time": "02:15:41",
  "category": "TOP 3 OPEN",
  "gender": "Male",
  "country": "Kenya",
  "splits": {
    "KM 5": "15:41",
    "KM 10": "15:30",
    "KM 15": "16:04",
    "KM 20": "15:52",
    "KM 21.1": "3:27",
    "KM 25": "12:31",
    "KM 30": "16:16",
    "KM 35": "16:24",
    "KM 40": "16:43",
    "FINISH": "7:09"
  }
}
```

---

## Status Codes in `status` Field
| Status | Meaning |
| :--- | :--- |
| `FINISHED` | Official finisher with recorded finish time and `position` rank |
| `CUT` | Reached course cut-off time (Over Time Limit / OTL) |
| `DNF` | Did Not Finish (started the race but stopped before the finish line) |
| `DNS` | Did Not Start |
| `DQ` / `DSQ` | Disqualified |
| `QRY` | Under timing query / review |

---

## Author & Copyright

**© 2026 Gelar Budidarma Djamal. All rights reserved.**
