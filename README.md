# Jakarta Running Festival (JRF) 2026 — Race Analytics Dashboard & Results API

[![Live Demo](https://img.shields.io/badge/Live%20Dashboard-GitHub%20Pages-10b981?style=for-the-badge&logo=github)](https://gbudidarma.github.io/jrf2026-results-api/)
[![Runners](https://img.shields.io/badge/Runners-36%2C306-0ea5e9?style=for-the-badge)](https://gbudidarma.github.io/jrf2026-results-api/)
[![Finishers](https://img.shields.io/badge/Finishers-30%2C602-10b981?style=for-the-badge)](https://gbudidarma.github.io/jrf2026-results-api/)
[![OpenAPI 3.0](https://img.shields.io/badge/API%20Spec-OpenAPI%203.0-6366f1?style=for-the-badge&logo=openapiinitiative)](openapi.json)
[![Support on Ko-fi](https://img.shields.io/badge/Support-Buy%20Me%20a%20Coffee-ff5e5b?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/V7V2JM8S4)

Complete official race telemetry, interactive HTML analytics dashboard, and OpenAPI 3.0.0 JSON datasets for the **Jakarta Running Festival (Day 1 & Day 2)** — covering **36,306 registered runners**, **30,602 official finishers**, and **1,172 double-category (Day 1 + Day 2) runners** across all 4 distance categories (Marathon, Half Marathon, 10K, and 5K).

🌐 **Live Interactive Dashboard:** **[https://gbudidarma.github.io/jrf2026-results-api/](https://gbudidarma.github.io/jrf2026-results-api/)**

> **Data Source:** All official race results and checkpoint split timings are sourced from **[https://results.scorenow.co.id](https://results.scorenow.co.id)**
> - **Day 1 (`myBCA Jakarta Half Marathon` & `Samsung Galaxy 5K`):** [https://results.scorenow.co.id/Results.aspx?CId=19723&RId=337](https://results.scorenow.co.id/Results.aspx?CId=19723&RId=337)
> - **Day 2 (`Hydroplus Marathon` & `Le Minerale 10K`):** [https://results.scorenow.co.id/Results.aspx?CId=19723&RId=338](https://results.scorenow.co.id/Results.aspx?CId=19723&RId=338)

---

## Interactive Race Analytics Dashboard (`dashboard.html` / `index.html`)

This repository includes a self-contained, zero-dependency interactive HTML dashboard (**`dashboard.html`** and **`index.html`**) that works offline in any browser or hosted directly via **GitHub Pages**:

- **Live GitHub Pages URL:** **[https://gbudidarma.github.io/jrf2026-results-api/](https://gbudidarma.github.io/jrf2026-results-api/)**
- **Local File:** Open `dashboard.html` or `index.html` directly in Chrome, Safari, Edge, or Firefox.

### Dashboard Features
1. **Global Remark & Class Filter (`Kelas Bersama Silaban`):** Header filter (joined by **BIB No** from [KelasBersamaSIlaban.csv](KelasBersamaSIlaban.csv)) to show only `Kelas Bersama Silaban` runners and/or a specific Class (`TT1`, `TT2`, `TT3`, `TT-DSC`, `TT5`, `TT6`, `TT7`, `TT8`, `TT9`, `TTp`, `TT-Cheering`). It dynamically recalculates **every** section — KPIs, event matrix, finish-time distribution, country joiners, category winners & podiums, runner table, and double-category tracker.
2. **Collapsible Sticky Quick-Jump Navigation Menu:** Jump directly to **Overview & Pace**, **Country Joiners**, **Category Winners & Podiums**, **All Runners Results**, **Double Category Runners**, or **↑ Top**, with a **`Hide Menu` / `Menu`** toggle button that saves screen space on mobile devices (auto-collapsing after clicking a section on mobile).
3. **Light & Dark Mode Switcher:** Clean header toggle (`Light` | `Dark`) that switches the entire dashboard theme and persists your preference in `localStorage`.
4. **Bruto & Netto Finish Times:** Displays both **Bruto Time** (official gun finish time) and **Netto Time** (chip time computed by summing each runner's checkpoint split intervals) across KPI cards, Event Performance Matrix, Category Winners & Podiums, All Runners Table, Double Category Tracker, and Split Detail Drawer.
5. **Completion & Attrition Telemetry:** Real-time KPI cards and visual progress bars for **Finish Rate (`FINISHED %`)**, **Did Not Finish (`DNF %`)**, **Over Time Limit (`CUT %`)**, **Did Not Start (`DNS %`)**, **Average Pace (`/km`)**, and **Average/Best Finish Time (Bruto & Netto)** across all events or filtered to a single race.
6. **Interactive Finish Time & Pace Distribution (with Cut-Off Time Buckets):**
   - Compare all 4 races side-by-side (`Avg Bruto`, `Avg Netto`, `Avg Pace`) or inspect event-specific finish-time interval buckets up to and beyond each race's official Cut-Off Time (COT):
     - **Half Marathon (21.1K):** 15-minute intervals + `> 3:45:00` (`COT 3h45m`)
     - **Marathon (42.2K):** 30-minute intervals + `> 5:00:00` (`COT 5h00m`)
     - **10K (10.0K):** 10-minute intervals + `> 2:00:00` (`COT 2h00m`)
     - **5K (5.0K):** 5-minute intervals + `> 1:00:00` (`COT 1h00m`)
   - **Click any Finish Time bar** to actively filter the All-Events Race Results table to the exact runners in that pace/time bucket.
7. **Country Joiners & Nationality Pie Charts:**
   - **All Joiners Pie Chart:** Domestic (`Indonesia`) vs. `International` participant split.
   - **International Joiners Pie Chart:** Share across foreign nations (`Malaysia`, `Japan`, `Singapore`, `Kenya`, `United States`, `Australia`, `China`, `India`, etc.).
   - **Top 10 Countries Table:** Click any country row or pie slice to filter the runner results table by nationality.
8. **Collapsible Category Winners & Podiums (`1st`, `2nd`, `3rd`):** Full podium cards and `#1` winner summary tables (with both Bruto and Netto times) for every category (`TOP 3 OPEN`, `TOP 5 OPEN`, `TOP 3 NATIONAL`, `OPEN`, `NATIONAL`, `MASTER NATIONAL 40-49`, `MASTER NATIONAL 50+`) across Male and Female divisions, with per-event **Collapse / Expand** and global **Expand All / Collapse All** controls (collapsed by default on initial page load).
9. **All-Events Race Results — All Runners (With Podium) Table:**
   - Instant search across all **36,306 runners** by **Runner Name**, **Bib Number**, or **Country**.
   - Multi-filter controls for **Event**, **Category**, **Gender**, **Status** (`FINISHED`, `DNF`, `CUT`, `DNS`, `DQ`, `QRY`), **Remark**, **Class**, and active **Finish Time Bucket**.
   - **Interactive Column Sorting:** Click any column header (**Overall Pos / Status**, **Cat Rank**, **Bib No**, **Runner Name**, **Event**, **Category**, **Gender**, **Country**, **Bruto Time**, **Netto Time**, **Avg Pace**) to toggle ascending (`▲`) or descending (`▼`) sort with visual indicators.
   - Displays **Overall Position / Status**, **Category Rank** (`🥇 #1`, `🥈 #2`, `🥉 #3`, `#4+`), **`Double` badge** for multi-day runners, **Class badge**, **Bruto Time**, **Netto Time**, and **Avg Pace**, defaulting to **10 rows per page** (`10`, `25`, `50`, or `100` selectable).
   - Click any runner row to open the **Checkpoint Split Times Drawer** (`KM 5`, `KM 10`, `KM 15`, `KM 20`, `KM 21.1`, `KM 25`, `KM 30`, `KM 35`, `KM 40`, and `FINISH`).
10. **Double Category Runners — Day 1 & Day 2 Multi-Event Tracker:**
    - Automatically identifies **1,172 runners** registered across both **Day 1** (`Half Marathon` or `5K`) and **Day 2** (`Marathon` or `10K`), including **873 runners** who officially finished both races.
    - Interactive combo cards (`HM + Marathon 63.3K`, `HM + 10K 31.1K`, `5K + Marathon 47.2K`, `5K + 10K 15.0K`), status filters (`Finished Both`, `Finished 1 of 2`, `DNS / DNF Both`), search bar, gender breakdown (`Male Finished` & `Female Finished`), and side-by-side **Day 1 + Day 2 Combined Distance, Bruto, Netto, and Avg Pace** breakdown. Click Either Day 1 or Day 2 result cell to inspect checkpoint splits.

---

## Race Telemetry Summary (Day 1 & Day 2)

| Event | Race Day | Distance | Total Registered | Finishers (`%`) | DNF (`%`) | CUT (`%`) | DNS (`%`) | Avg Bruto Time | Avg Netto Time | Avg Pace |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| **myBCA Jakarta Half Marathon** | Day 1 | `21.1 KM` | `14,684` | `12,684` (`86.38%`) | `714` (`4.86%`) | `118` (`0.80%`) | `1,167` (`7.95%`) | `02:45:17` | `02:38:07` | `7:50 /km` |
| **Samsung Galaxy 5K** | Day 1 | `5.0 KM` | `4,761` | `4,048` (`85.02%`) | `7` (`0.15%`) | `72` (`1.51%`) | `634` (`13.32%`) | `00:43:23` | `00:39:42` | `8:41 /km` |
| **Hydroplus Marathon** | Day 2 | `42.195 KM` | `4,420` | `2,637` (`59.66%`) | `1,146` (`25.93%`) | `64` (`1.45%`) | `545` (`12.33%`) | `04:25:49` | `04:23:16` | `6:18 /km` |
| **Le Minerale 10K** | Day 2 | `10.0 KM` | `12,441` | `11,233` (`90.29%`) | `25` (`0.20%`) | `180` (`1.45%`) | `1,003` (`8.06%`) | `01:26:54` | `01:18:55` | `8:41 /km` |
| **All 4 Events Combined** | **Day 1 & 2** | **—** | **`36,306`** | **`30,602` (`84.29%`)** | **`1,892` (`5.21%`)** | **`434` (`1.20%`)** | **`3,349` (`9.22%`)** | **—** | **—** | **`8:07 /km`** |

### Double Category Runners Summary (Day 1 + Day 2)

| Day 1 + Day 2 Combination | Total Distance | Registered Runners | Finished Both (`%`) | Male Finished (`%`) | Female Finished (`%`) |
| :--- | :---: | ---: | ---: | ---: | ---: |
| **HM (Day 1) + 10K (Day 2)** | `31.1 KM` | `590` (`459` M / `131` F) | `481` (`81.5%`) | `382 / 459` (`83.2%`) | `99 / 131` (`75.6%`) |
| **HM (Day 1) + Marathon (Day 2)** | `63.3 KM` | `286` (`275` M / `11` F) | `177` (`61.9%`) | `173 / 275` (`62.9%`) | `4 / 11` (`36.4%`) |
| **5K (Day 1) + 10K (Day 2)** | `15.0 KM` | `213` (`117` M / `96` F) | `166` (`77.9%`) | `88 / 117` (`75.2%`) | `78 / 96` (`81.2%`) |
| **5K (Day 1) + Marathon (Day 2)** | `47.2 KM` | `83` (`76` M / `7` F) | `49` (`59.0%`) | `45 / 76` (`59.2%`) | `4 / 7` (`57.1%`) |
| **All Double Combinations** | **—** | **`1,172` (`927` M / `245` F)** | **`873` (`74.5%`)** | **`688 / 927` (`74.2%`)** | **`185 / 245` (`75.5%`)** |

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

## Data Source, Author & Copyright

- **Data Source:** [https://results.scorenow.co.id](https://results.scorenow.co.id)
- **Author & Copyright:** **© 2026 [@gbudidarma](https://www.instagram.com/gbudidarma/) All rights reserved.**

---

## Support & Buy Me a Coffee

If you found this race analytics dashboard, API datasets, or runner telemetry helpful, you can support the project here:

<a href='https://ko-fi.com/V7V2JM8S4' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi5.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>
