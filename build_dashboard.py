import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
ARTIFACT_PATH = Path(
    "/Users/gbudidarma/.gemini/antigravity/brain/c6ce6403-c8c9-4e9f-ac00-8d48764a74f9/jrf_race_dashboard.html"
)


def time_to_sec(t: str | None) -> int | None:
    if not t:
        return None
    parts = [int(x) for x in t.strip().split(":") if x.strip().isdigit()]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None


def sec_to_hms(s: float | None) -> str:
    if s is None:
        return "-"
    sec = int(round(s))
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def sec_to_pace(s_per_km: float | None) -> str:
    if s_per_km is None:
        return "-"
    sec = int(round(s_per_km))
    return f"{sec // 60}:{sec % 60:02d} /km"


CATEGORY_ORDER = [
    "TOP 3 OPEN",
    "TOP 5 OPEN",
    "TOP 3 NATIONAL",
    "OPEN",
    "NATIONAL",
    "MASTER NATIONAL 40-49",
    "MASTER NATIONAL 50+",
    "PACER",
]


def compute_dashboard_data() -> dict:
    raw = json.loads((WORKSPACE / "jrf_all_results.json").read_text(encoding="utf-8"))
    events_meta = raw["events"]
    all_results = raw["results"]

    events_analytics = []
    total_all = len(all_results)
    status_all = Counter(r["status"] for r in all_results)
    all_paces = []

    # Lookup dictionaries for compact encoding of all 36,306 runner records
    event_lookup = []
    event_slug_to_idx = {}
    event_dist_by_idx = {}
    event_splits_by_idx = {}

    for idx, ev in enumerate(events_meta):
        slug = ev["event_slug"]
        clean_splits = [s for s in ev["split_checkpoints"] if s != "RTW"]
        event_slug_to_idx[slug] = idx
        event_dist_by_idx[idx] = float(ev["distance_km"])
        event_splits_by_idx[idx] = clean_splits
        event_lookup.append(
            {
                "slug": slug,
                "name": ev["event_name"],
                "day": ev["race_day"],
                "dist": float(ev["distance_km"]),
                "splits": clean_splits,
            }
        )

    for ev in events_meta:
        slug = ev["event_slug"]
        dist = float(ev["distance_km"])
        rows = [r for r in all_results if r["event_slug"] == slug]
        total = len(rows)
        counts = Counter(r["status"] for r in rows)

        fin_count = counts.get("FINISHED", 0)
        dnf_count = counts.get("DNF", 0)
        cut_count = counts.get("CUT", 0)
        dns_count = counts.get("DNS", 0)
        dq_count = counts.get("DQ", 0) + counts.get("DSQ", 0)
        qry_count = counts.get("QRY", 0)

        fin_rows = [r for r in rows if r["status"] == "FINISHED" and time_to_sec(r["time"])]
        fin_secs = [time_to_sec(r["time"]) for r in fin_rows]
        male_secs = [time_to_sec(r["time"]) for r in fin_rows if r.get("gender") == "Male"]
        female_secs = [time_to_sec(r["time"]) for r in fin_rows if r.get("gender") == "Female"]

        avg_sec = statistics.mean(fin_secs) if fin_secs else None
        med_sec = statistics.median(fin_secs) if fin_secs else None
        min_sec = min(fin_secs) if fin_secs else None
        max_sec = max(fin_secs) if fin_secs else None

        avg_pace_sec = (avg_sec / dist) if avg_sec else None
        med_pace_sec = (med_sec / dist) if med_sec else None
        best_pace_sec = (min_sec / dist) if min_sec else None
        male_pace_sec = (statistics.mean(male_secs) / dist) if male_secs else None
        female_pace_sec = (statistics.mean(female_secs) / dist) if female_secs else None

        all_paces.extend([s / dist for s in fin_secs])

        buckets = []
        if fin_secs and min_sec is not None and max_sec is not None:
            bucket_count = 8
            span = max(max_sec - min_sec, bucket_count)
            step = span / bucket_count
            b_counts = [0] * bucket_count
            for s in fin_secs:
                idx = min(int((s - min_sec) / step), bucket_count - 1)
                b_counts[idx] += 1
            for i in range(bucket_count):
                b_start = min_sec + i * step
                b_end = min_sec + (i + 1) * step
                buckets.append(
                    {
                        "label": f"{sec_to_hms(b_start)[:5]}–{sec_to_hms(b_end)[:5]}",
                        "pace_label": f"{sec_to_pace(b_start / dist)} – {sec_to_pace(b_end / dist)}",
                        "count": b_counts[i],
                        "pct": round(b_counts[i] * 100.0 / len(fin_secs), 1),
                    }
                )

        cat_groups = defaultdict(list)
        cat_all_rows = defaultdict(list)
        for r in rows:
            cat = r.get("category") or "Unknown"
            gen = r.get("gender") or "Unknown"
            if cat in ("Unknown", "PACER") or gen == "Unknown":
                continue
            cat_all_rows[(cat, gen)].append(r)
            if r["status"] == "FINISHED" and time_to_sec(r["time"]):
                cat_groups[(cat, gen)].append(r)

        def sort_key(cg):
            c, g = cg
            c_idx = CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else 99
            g_idx = 0 if g == "Male" else 1
            return (c_idx, c, g_idx)

        categories_data = []
        podium_bibs = set()
        cat_rank_by_bib = {}
        for cat, gen in sorted(cat_groups.keys(), key=sort_key):
            group_finishers = sorted(cat_groups[(cat, gen)], key=lambda x: time_to_sec(x["time"]) or 999999)
            group_total = len(cat_all_rows[(cat, gen)])
            group_secs = [time_to_sec(x["time"]) for x in group_finishers]
            g_avg_sec = statistics.mean(group_secs)
            for r_idx, runner in enumerate(group_finishers, start=1):
                cat_rank_by_bib[runner["bib_no"]] = r_idx
                if r_idx <= 3 or cat in ("TOP 3 OPEN", "TOP 5 OPEN", "TOP 3 NATIONAL"):
                    podium_bibs.add(runner["bib_no"])
            podium = []
            for rank_idx, runner in enumerate(group_finishers[:3], start=1):
                r_sec = time_to_sec(runner["time"])
                podium.append(
                    {
                        "category_rank": rank_idx,
                        "overall_pos": runner["position"],
                        "bib_no": runner["bib_no"],
                        "name": runner["name"],
                        "country": runner.get("country") or "-",
                        "time": runner["time"],
                        "pace": sec_to_pace(r_sec / dist) if r_sec else "-",
                    }
                )
            categories_data.append(
                {
                    "category": cat,
                    "gender": gen,
                    "total_entered": group_total,
                    "finishers_count": len(group_finishers),
                    "finish_pct": round(len(group_finishers) * 100.0 / group_total, 1) if group_total else 0.0,
                    "avg_time": sec_to_hms(g_avg_sec),
                    "avg_pace": sec_to_pace(g_avg_sec / dist),
                    "winner": podium[0] if podium else None,
                    "podium": podium,
                }
            )

        ev["_podium_bibs"] = podium_bibs
        ev["_cat_rank_by_bib"] = cat_rank_by_bib

        events_analytics.append(
            {
                "event_slug": slug,
                "event_name": ev["event_name"],
                "race_day": ev["race_day"],
                "distance_km": dist,
                "total": total,
                "finished": fin_count,
                "finished_pct": round(fin_count * 100.0 / total, 2),
                "dnf": dnf_count,
                "dnf_pct": round(dnf_count * 100.0 / total, 2),
                "cut": cut_count,
                "cut_pct": round(cut_count * 100.0 / total, 2),
                "dnf_plus_cut": dnf_count + cut_count,
                "dnf_plus_cut_pct": round((dnf_count + cut_count) * 100.0 / total, 2),
                "dns": dns_count,
                "dns_pct": round(dns_count * 100.0 / total, 2),
                "other": dq_count + qry_count,
                "other_pct": round((dq_count + qry_count) * 100.0 / total, 2),
                "avg_time": sec_to_hms(avg_sec),
                "median_time": sec_to_hms(med_sec),
                "best_time": sec_to_hms(min_sec),
                "avg_pace": sec_to_pace(avg_pace_sec),
                "median_pace": sec_to_pace(med_pace_sec),
                "best_pace": sec_to_pace(best_pace_sec),
                "male_avg_pace": sec_to_pace(male_pace_sec),
                "female_avg_pace": sec_to_pace(female_pace_sec),
                "male_finishers": len(male_secs),
                "female_finishers": len(female_secs),
                "buckets": buckets,
                "categories": categories_data,
            }
        )

    # Encode all 36,306 runners into a compact array for instant client-side search & pagination
    # Format per runner:
    # [0: event_idx, 1: pos_or_null, 2: status_str, 3: bib_no, 4: name, 5: time_str,
    #  6: pace_str, 7: category, 8: gender, 9: country, 10: splits_array, 11: is_podium (1/0), 12: cat_rank]
    compact_runners = []
    for r in all_results:
        ev_idx = event_slug_to_idx[r["event_slug"]]
        ev_obj = events_meta[ev_idx]
        dist = event_dist_by_idx[ev_idx]
        split_cols = event_splits_by_idx[ev_idx]
        t_str = r.get("time") or ""
        t_sec = time_to_sec(t_str) if r["status"] == "FINISHED" else None
        p_str = sec_to_pace(t_sec / dist).replace(" /km", "") if t_sec else ""
        splits_arr = [r["splits"].get(c) or "" for c in split_cols]
        bib = r["bib_no"]
        pos = r["position"]
        is_pod = 1 if (bib in ev_obj.get("_podium_bibs", set()) or (pos is not None and pos <= 3)) else 0
        cat_rk = ev_obj.get("_cat_rank_by_bib", {}).get(bib)
        compact_runners.append(
            [
                ev_idx,
                pos,
                r["status"],
                bib,
                r["name"],
                t_str,
                p_str,
                r.get("category") or "Unknown",
                r.get("gender") or "Unknown",
                r.get("country") or "-",
                splits_arr,
                is_pod,
                cat_rk,
            ]
        )

    fin_all = status_all.get("FINISHED", 0)
    dnf_all = status_all.get("DNF", 0)
    cut_all = status_all.get("CUT", 0)
    dns_all = status_all.get("DNS", 0)
    other_all = status_all.get("DQ", 0) + status_all.get("DSQ", 0) + status_all.get("QRY", 0)

    return {
        "overall": {
            "total": total_all,
            "finished": fin_all,
            "finished_pct": round(fin_all * 100.0 / total_all, 2),
            "dnf": dnf_all,
            "dnf_pct": round(dnf_all * 100.0 / total_all, 2),
            "cut": cut_all,
            "cut_pct": round(cut_all * 100.0 / total_all, 2),
            "dnf_plus_cut": dnf_all + cut_all,
            "dnf_plus_cut_pct": round((dnf_all + cut_all) * 100.0 / total_all, 2),
            "dns": dns_all,
            "dns_pct": round(dns_all * 100.0 / total_all, 2),
            "other": other_all,
            "other_pct": round(other_all * 100.0 / total_all, 2),
            "avg_pace": sec_to_pace(statistics.mean(all_paces)),
            "median_pace": sec_to_pace(statistics.median(all_paces)),
        },
        "events": events_analytics,
        "event_lookup": event_lookup,
        "runners": compact_runners,
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Jakarta Running Festival — Race Analytics &amp; Runner Search Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased p-4 md:p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header Banner -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-semibold tracking-wide uppercase mb-2">
          <span>Official Race Telemetry</span>
          <span>•</span>
          <span>36,306 Registered Runners</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)]">
          Jakarta Running Festival — Race Analytics &amp; Results Explorer
        </h1>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">
          Finish rates, DNF / Cut-off / DNS percentages, average pace metrics, category podiums, and full 36,306-runner search across Day 1 &amp; Day 2.
        </p>
      </div>
      <!-- Event Selector Pills -->
      <div id="eventTabs" class="flex flex-wrap gap-2"></div>
    </div>

    <!-- Top KPI Cards -->
    <div id="kpiGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"></div>

    <!-- Status Breakdown Bar + Event Comparison Table -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left: Status Breakdown & Pace Details -->
      <div class="lg:col-span-5 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between space-y-4">
        <div>
          <h2 id="statusCardTitle" class="text-base font-semibold text-[var(--foreground)]">Completion &amp; Attrition Breakdown</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Percentage of Finishers, DNF, Cut-Off (OTL), and Did Not Start (DNS)</p>
        </div>
        <div id="statusVisual" class="space-y-4"></div>
        <div id="paceGenderCards" class="grid grid-cols-2 gap-3 pt-2 border-t border-[var(--border)]"></div>
      </div>

      <!-- Right: All 4 Events Comparison Matrix OR Finish Time Histogram -->
      <div class="lg:col-span-7 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 id="rightPanelTitle" class="text-base font-semibold text-[var(--foreground)]">Event-by-Event Performance Matrix</h2>
            <p id="rightPanelSubtitle" class="text-xs text-[var(--muted-foreground)] mt-0.5">Click any event row to filter the dashboard to that specific race</p>
          </div>
        </div>
        <div id="rightPanelContent"></div>
      </div>
    </div>

    <!-- Country Joiners Pie Chart & Nationality Breakdown Section -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-4 border-b border-[var(--border)]">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 id="countrySectionTitle" class="text-lg font-bold text-[var(--foreground)]">Country Joiners — Participant Nationality Breakdown</h2>
            <span id="countryTotalBadge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500"></span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Distribution of registered runners by country (Overall Domestic vs International + Top International Countries Pie Chart) — click any country to filter the runner table
          </p>
        </div>
      </div>
      <div id="countryChartsContainer" class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch"></div>
    </div>

    <!-- Category Winners & Podium Section -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[var(--border)]">
        <div>
          <h2 class="text-lg font-bold text-[var(--foreground)]">Category Winners &amp; Podiums (All Events)</h2>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            1st, 2nd, and 3rd place finishers for every race category &amp; gender division, plus category average pace and finish rate
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <!-- Gender Filter -->
          <div id="genderFilterBtns" class="inline-flex rounded-lg border border-[var(--border)] p-1 bg-[var(--background)]">
            <button data-gender="ALL" class="gender-btn px-3 py-1 rounded-md text-xs font-medium">All Genders</button>
            <button data-gender="Male" class="gender-btn px-3 py-1 rounded-md text-xs font-medium">Male</button>
            <button data-gender="Female" class="gender-btn px-3 py-1 rounded-md text-xs font-medium">Female</button>
          </div>
          <!-- View Mode Toggle -->
          <div id="viewModeBtns" class="inline-flex rounded-lg border border-[var(--border)] p-1 bg-[var(--background)]">
            <button data-mode="cards" class="mode-btn px-3 py-1 rounded-md text-xs font-medium">Podium Cards (Top 3)</button>
            <button data-mode="table" class="mode-btn px-3 py-1 rounded-md text-xs font-medium">Summary Table (#1 Winners)</button>
          </div>
          <!-- Expand / Collapse All Events -->
          <div class="inline-flex rounded-lg border border-[var(--border)] p-1 bg-[var(--background)]">
            <button onclick="expandAllWinnerEvents()" class="px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">Expand All</button>
            <button onclick="collapseAllWinnerEvents()" class="px-2.5 py-1 rounded-md text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">Collapse All</button>
          </div>
          <!-- Search input -->
          <input
            id="winnerSearch"
            type="text"
            placeholder="Search winner, bib, category..."
            class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs focus:outline-none"
          />
        </div>
      </div>

      <div id="winnersContainer"></div>
    </div>

    <!-- All-Events Detailed Runner Search & Results Table -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-[var(--border)]">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-[var(--foreground)]">All-Events Race Results — All Runners (With Podium)</h2>
            <span id="runnerResultCountBadge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500">36,306 runners</span>
            <span class="px-2 py-0.5 rounded-md text-xs font-medium bg-[var(--background)] border border-[var(--border)] text-[var(--muted-foreground)]">Includes All Podium Winners &amp; General Field</span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Search any runner by Name, Bib Number, or Country across all 4 events — click any row to inspect full checkpoint splits
          </p>
        </div>
        <button
          id="resetRunnerFiltersBtn"
          class="self-start lg:self-auto px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition"
        >
          Reset Filters
        </button>
      </div>

      <!-- Search & Filter Controls Bar -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        <div class="sm:col-span-2">
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Search Runner (Name, Bib No, Country)</label>
          <input
            id="runnerSearchInput"
            type="text"
            placeholder="e.g. KIPRONO, A14328, ROBI, Indonesia..."
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Event</label>
          <select
            id="runnerEventSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All 4 Events (36,306)</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Category</label>
          <select
            id="runnerCategorySelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Categories</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Gender</label>
          <select
            id="runnerGenderSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Genders</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Status</label>
          <select
            id="runnerStatusSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="FINISHED">FINISHED (Official)</option>
            <option value="DNF">DNF (Did Not Finish)</option>
            <option value="CUT">CUT (Over Time Limit)</option>
            <option value="DNS">DNS (Did Not Start)</option>
            <option value="DQ">DQ (Disqualified)</option>
            <option value="QRY">QRY (Query)</option>
          </select>
        </div>
      </div>

      <!-- Selected Runner Split Detail Drawer (shown when a runner row is clicked) -->
      <div id="runnerDetailDrawer" class="hidden rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-4 space-y-3"></div>

      <!-- Detailed Runner Table -->
      <div class="overflow-x-auto border border-[var(--border)] rounded-xl">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-[var(--background)] border-b border-[var(--border)] text-[var(--muted-foreground)]">
              <th class="py-3 px-3 font-semibold">Overall Pos / Status</th>
              <th class="py-3 px-2 font-semibold">Cat Rank</th>
              <th class="py-3 px-2.5 font-semibold">Bib No</th>
              <th class="py-3 px-3 font-semibold">Runner Name</th>
              <th class="py-3 px-2.5 font-semibold">Event</th>
              <th class="py-3 px-2.5 font-semibold">Category</th>
              <th class="py-3 px-2 font-semibold">Gender</th>
              <th class="py-3 px-2.5 font-semibold">Country</th>
              <th class="py-3 px-2.5 font-semibold text-right">Finish Time</th>
              <th class="py-3 px-2.5 font-semibold text-right">Avg Pace</th>
              <th class="py-3 px-3 font-semibold">Checkpoint Splits</th>
            </tr>
          </thead>
          <tbody id="runnerTableBody" class="divide-y divide-[var(--border)]"></tbody>
        </table>
      </div>

      <!-- Pagination Controls -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
        <div id="runnerPaginationInfo" class="text-xs text-[var(--muted-foreground)]"></div>
        <div class="flex items-center gap-2">
          <label class="text-xs text-[var(--muted-foreground)]">Rows:</label>
          <select
            id="runnerPageSizeSelect"
            class="px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs"
          >
            <option value="10" selected>10</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
          <button
            id="prevPageBtn"
            class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium disabled:opacity-40"
          >
            ← Prev
          </button>
          <span id="pageIndicator" class="text-xs font-semibold px-2"></span>
          <button
            id="nextPageBtn"
            class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Footer Copyright -->
    <footer class="bg-[var(--card)] border border-[var(--border)] rounded-2xl px-6 py-4 shadow-sm flex items-center justify-center text-xs text-[var(--muted-foreground)]">
      <div class="font-medium text-[var(--foreground)]">
        &copy; 2026 <a href="https://www.instagram.com/gbudidarma/" target="_blank" rel="noopener noreferrer" class="font-bold text-emerald-500 hover:underline">@gbudidarma</a> All rights reserved.
      </div>
    </footer>

  </div>

  <script>
    (function ensureStandaloneTheme() {
      const root = document.documentElement;
      const bg = getComputedStyle(root).getPropertyValue('--background').trim();
      if (!bg) {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        const vars = prefersDark
          ? {
              '--background': '#0b0f19',
              '--card': '#111827',
              '--foreground': '#f9fafb',
              '--muted-foreground': '#9ca3af',
              '--border': '#1f2937',
              '--primary': '#10b981',
              '--secondary': '#1e293b'
            }
          : {
              '--background': '#f8fafc',
              '--card': '#ffffff',
              '--foreground': '#0f172a',
              '--muted-foreground': '#64748b',
              '--border': '#e2e8f0',
              '--primary': '#059669',
              '--secondary': '#f1f5f9'
            };
        Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
      }
    })();

    const DASHBOARD_DATA = __DASHBOARD_JSON__;

    let selectedEventSlug = 'ALL';
    let selectedGender = 'ALL';
    let selectedViewMode = 'cards';
    let searchQuery = '';

    // Runner Table State
    let runnerQuery = '';
    let runnerEventFilter = 'ALL';
    let runnerCategoryFilter = 'ALL';
    let runnerGenderFilter = 'ALL';
    let runnerStatusFilter = 'ALL';
    let runnerPage = 1;
    let runnerPageSize = 10;
    let filteredRunners = [];

    // Non-Podium Runner Table State (Excludes all podium winners: r[11] === 0)
    let npQuery = '';
    let npEventFilter = 'ALL';
    let npCategoryFilter = 'ALL';
    let npGenderFilter = 'ALL';
    let npStatusFilter = 'ALL';
    let npPage = 1;
    let npPageSize = 10;
    let filteredNpRunners = [];

    function fmtNum(n) {
      return Number(n).toLocaleString('en-US');
    }

    function escapeHtml(str) {
      return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function getActiveContext() {
      if (selectedEventSlug === 'ALL') {
        return { isAll: true, stats: DASHBOARD_DATA.overall, events: DASHBOARD_DATA.events };
      }
      const ev = DASHBOARD_DATA.events.find(e => e.event_slug === selectedEventSlug);
      return { isAll: false, stats: ev, events: [ev] };
    }

    function initRunnerFilterOptions() {
      const evOptions = `<option value="ALL">All 4 Events (${fmtNum(DASHBOARD_DATA.overall.total)})</option>` +
        DASHBOARD_DATA.event_lookup.map((ev, idx) =>
          `<option value="${idx}">${ev.name} (${ev.dist}K)</option>`
        ).join('');
      document.getElementById('runnerEventSelect').innerHTML = evOptions;

      const cats = new Set();
      DASHBOARD_DATA.runners.forEach(r => {
        if (r[7] && r[7] !== 'Unknown') {
          cats.add(r[7]);
        }
      });
      document.getElementById('runnerCategorySelect').innerHTML = `<option value="ALL">All Categories</option>` +
        Array.from(cats).map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }

    function catRankBadgeHtml(catRank) {
      if (!catRank) return '<span class="text-[var(--muted-foreground)]">—</span>';
      if (catRank <= 3) {
        const medal = catRank === 1 ? '🥇 ' : catRank === 2 ? '🥈 ' : '🥉 ';
        return `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 font-bold">${medal}#${fmtNum(catRank)}</span>`;
      }
      return `<span class="font-mono text-xs text-sky-500 font-semibold">#${fmtNum(catRank)}</span>`;
    }

    function filterRunnersList() {
      const q = runnerQuery.trim().toLowerCase();
      const evIdx = runnerEventFilter === 'ALL' ? null : Number(runnerEventFilter);

      filteredRunners = DASHBOARD_DATA.runners.filter(r => {
        if (evIdx !== null && r[0] !== evIdx) return false;
        if (runnerCategoryFilter !== 'ALL' && r[7] !== runnerCategoryFilter) return false;
        if (runnerGenderFilter !== 'ALL' && r[8] !== runnerGenderFilter) return false;
        if (runnerStatusFilter !== 'ALL' && r[2] !== runnerStatusFilter) return false;
        if (q) {
          const bib = (r[3] || '').toLowerCase();
          const name = (r[4] || '').toLowerCase();
          const country = (r[9] || '').toLowerCase();
          if (!bib.includes(q) && !name.includes(q) && !country.includes(q)) return false;
        }
        return true;
      });

      runnerPage = 1;
      renderRunnerTable();
    }

    function statusBadgeHtml(pos, status) {
      if (status === 'FINISHED' && pos !== null) {
        const medal = pos === 1 ? '🥇 ' : pos === 2 ? '🥈 ' : pos === 3 ? '🥉 ' : '#';
        const cls = pos <= 3
          ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 font-bold'
          : 'bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)] font-semibold';
        return `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono ${cls}">${medal}${fmtNum(pos)}</span>`;
      }
      const colors = {
        DNF: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
        CUT: 'bg-orange-500/15 text-orange-500 border-orange-500/30',
        DNS: 'bg-rose-500/15 text-rose-500 border-rose-500/30',
        DQ: 'bg-purple-500/15 text-purple-500 border-purple-500/30',
        QRY: 'bg-purple-500/15 text-purple-500 border-purple-500/30'
      };
      const c = colors[status] || 'bg-[var(--background)] text-[var(--muted-foreground)] border-[var(--border)]';
      return `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold border ${c}">${escapeHtml(status)}</span>`;
    }

    function showRunnerDetail(idxInFiltered) {
      const r = filteredRunners[idxInFiltered];
      if (!r) return;
      const ev = DASHBOARD_DATA.event_lookup[r[0]];
      const drawer = document.getElementById('runnerDetailDrawer');
      drawer.classList.remove('hidden');

      const splitsHtml = ev.splits.map((label, sIdx) => {
        const val = r[10][sIdx] || '—';
        return `
          <div class="p-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)] text-center">
            <div class="text-xs text-[var(--muted-foreground)] font-medium">${escapeHtml(label)}</div>
            <div class="text-sm font-mono font-bold text-[var(--foreground)] mt-0.5">${escapeHtml(val)}</div>
          </div>
        `;
      }).join('');

      drawer.innerHTML = `
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              ${statusBadgeHtml(r[1], r[2])}
              ${r[12] ? `<span class="px-2 py-0.5 rounded bg-sky-500/10 text-sky-500 border border-sky-500/30 font-mono text-xs font-semibold">Cat Rank #${fmtNum(r[12])}</span>` : ''}
              <span class="text-base font-bold text-[var(--foreground)]">${escapeHtml(r[4] || '(No Name)')}</span>
              <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs text-[var(--muted-foreground)]">Bib: ${escapeHtml(r[3])}</span>
            </div>
            <div class="text-xs text-[var(--muted-foreground)] mt-1">
              <strong>${escapeHtml(ev.name)}</strong> (${ev.dist} KM • ${escapeHtml(ev.day)}) • Category: <strong>${escapeHtml(r[7])}</strong> • Gender: <strong>${escapeHtml(r[8])}</strong> • Country: <strong>${escapeHtml(r[9])}</strong>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-xs text-[var(--muted-foreground)]">Finish Time / Pace</div>
              <div class="text-sm font-mono font-bold text-emerald-500">${escapeHtml(r[5] || '—')} ${r[6] ? `(${escapeHtml(r[6])} /km)` : ''}</div>
            </div>
            <button
              onclick="document.getElementById('runnerDetailDrawer').classList.add('hidden')"
              class="px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--card)] text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              ✕ Close
            </button>
          </div>
        </div>
        <div>
          <div class="text-xs font-semibold text-[var(--muted-foreground)] mb-2">Checkpoint Split Times (Segment Intervals)</div>
          <div class="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-2">${splitsHtml}</div>
        </div>
      `;
    }

    function renderRunnerTable() {
      const total = filteredRunners.length;
      const totalPages = Math.max(1, Math.ceil(total / runnerPageSize));
      if (runnerPage > totalPages) runnerPage = totalPages;

      const startIdx = (runnerPage - 1) * runnerPageSize;
      const endIdx = Math.min(startIdx + runnerPageSize, total);
      const pageSlice = filteredRunners.slice(startIdx, endIdx);

      document.getElementById('runnerResultCountBadge').textContent = `${fmtNum(total)} runners`;
      document.getElementById('runnerPaginationInfo').textContent =
        total > 0
          ? `Showing ${fmtNum(startIdx + 1)}–${fmtNum(endIdx)} of ${fmtNum(total)} matching runners`
          : 'No matching runners found';
      document.getElementById('pageIndicator').textContent = `Page ${fmtNum(runnerPage)} of ${fmtNum(totalPages)}`;
      document.getElementById('prevPageBtn').disabled = runnerPage <= 1;
      document.getElementById('nextPageBtn').disabled = runnerPage >= totalPages;

      const tbody = document.getElementById('runnerTableBody');
      if (!pageSlice.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="11" class="py-8 text-center text-sm text-[var(--muted-foreground)]">
              No runners match your search filters. Try clearing or adjusting the search terms.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = pageSlice.map((r, idx) => {
        const globalFilteredIdx = startIdx + idx;
        const ev = DASHBOARD_DATA.event_lookup[r[0]];
        const nonEmptySplits = ev.splits
          .map((lbl, i) => (r[10][i] ? `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] font-mono text-xs"><span class="text-[var(--muted-foreground)]">${escapeHtml(lbl)}:</span>${escapeHtml(r[10][i])}</span>` : ''))
          .filter(Boolean);
        const splitsPreview = nonEmptySplits.length
          ? nonEmptySplits.slice(0, 4).join(' ') + (nonEmptySplits.length > 4 ? ` <span class="text-xs text-emerald-500 font-medium">+${nonEmptySplits.length - 4} more</span>` : '')
          : '<span class="text-[var(--muted-foreground)]">—</span>';

        return `
          <tr onclick="showRunnerDetail(${globalFilteredIdx})" class="hover:bg-[var(--background)] cursor-pointer transition">
            <td class="py-2.5 px-3 whitespace-nowrap">${statusBadgeHtml(r[1], r[2])}</td>
            <td class="py-2.5 px-2 whitespace-nowrap">${catRankBadgeHtml(r[12])}</td>
            <td class="py-2.5 px-2.5 font-mono font-semibold text-[var(--foreground)] whitespace-nowrap">${escapeHtml(r[3])}</td>
            <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">${escapeHtml(r[4] || '—')}</td>
            <td class="py-2.5 px-2.5 whitespace-nowrap">
              <span class="text-[var(--foreground)] font-medium">${escapeHtml(ev.name)}</span>
            </td>
            <td class="py-2.5 px-2.5 text-[var(--muted-foreground)] whitespace-nowrap">${escapeHtml(r[7])}</td>
            <td class="py-2.5 px-2 whitespace-nowrap">
              <span class="px-2 py-0.5 rounded text-xs font-medium ${
                r[8] === 'Male' ? 'bg-sky-500/10 text-sky-500' : r[8] === 'Female' ? 'bg-pink-500/10 text-pink-500' : 'text-[var(--muted-foreground)]'
              }">${escapeHtml(r[8])}</span>
            </td>
            <td class="py-2.5 px-2.5 text-[var(--muted-foreground)] whitespace-nowrap">${escapeHtml(r[9])}</td>
            <td class="py-2.5 px-2.5 text-right font-mono font-bold text-emerald-500 whitespace-nowrap">${escapeHtml(r[5] || '—')}</td>
            <td class="py-2.5 px-2.5 text-right font-mono text-sky-500 whitespace-nowrap">${r[6] ? `${escapeHtml(r[6])} /km` : '—'}</td>
            <td class="py-2.5 px-3"><div class="flex flex-wrap gap-1">${splitsPreview}</div></td>
          </tr>
        `;
      }).join('');
    }

    function renderTabs() {
      const container = document.getElementById('eventTabs');
      const tabs = [
        { slug: 'ALL', label: 'All Events (36,306)' },
        ...DASHBOARD_DATA.events.map(e => ({
          slug: e.event_slug,
          label: `${e.event_name} (${e.distance_km}K)`
        }))
      ];
      container.innerHTML = tabs.map(t => {
        const active = t.slug === selectedEventSlug;
        return `
          <button
            onclick="selectEvent('${t.slug}')"
            class="px-3.5 py-2 rounded-xl text-xs font-semibold transition border ${
              active
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                : 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:border-emerald-500/50'
            }"
          >
            ${t.label}
          </button>
        `;
      }).join('');
    }

    function renderKPIs() {
      const { isAll, stats } = getActiveContext();
      const grid = document.getElementById('kpiGrid');

      const cards = [
        {
          title: 'Finish Rate (FINISHED)',
          value: `${stats.finished_pct}%`,
          sub: `${fmtNum(stats.finished)} of ${fmtNum(stats.total)} runners`,
          badge: 'Official Finishers',
          color: 'text-emerald-500',
          barColor: 'bg-emerald-500',
          pct: stats.finished_pct
        },
        {
          title: 'Did Not Finish (DNF)',
          value: `${stats.dnf_pct}%`,
          sub: `${fmtNum(stats.dnf)} DNF (${stats.dnf_plus_cut_pct}% incl. ${fmtNum(stats.cut)} CUT)`,
          badge: `CUT / OTL: ${stats.cut_pct}%`,
          color: 'text-amber-500',
          barColor: 'bg-amber-500',
          pct: stats.dnf_plus_cut_pct
        },
        {
          title: 'Did Not Start (DNS)',
          value: `${stats.dns_pct}%`,
          sub: `${fmtNum(stats.dns)} registered no-shows`,
          badge: 'Pre-race attrition',
          color: 'text-rose-500',
          barColor: 'bg-rose-500',
          pct: stats.dns_pct
        },
        {
          title: 'Average Pace',
          value: stats.avg_pace,
          sub: isAll ? `Median Pace: ${stats.median_pace}` : `Median Pace: ${stats.median_pace} • Best: ${stats.best_pace}`,
          badge: isAll ? 'Across all 30,602 finishers' : `${stats.distance_km} KM Distance`,
          color: 'text-sky-500',
          barColor: 'bg-sky-500',
          pct: 100
        },
        {
          title: isAll ? 'Total Finishers' : 'Average Finish Time',
          value: isAll ? fmtNum(stats.finished) : stats.avg_time,
          sub: isAll ? `Across 4 Race Events (Day 1 & Day 2)` : `Median: ${stats.median_time} • Best: ${stats.best_time}`,
          badge: isAll ? 'JRF 2026 Dataset' : stats.race_day,
          color: 'text-indigo-500',
          barColor: 'bg-indigo-500',
          pct: 100
        }
      ];

      grid.innerHTML = cards.map(c => `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-medium text-[var(--muted-foreground)]">${c.title}</span>
              <span class="text-xs px-2 py-0.5 rounded-md bg-[var(--background)] border border-[var(--border)] text-[var(--muted-foreground)]">${c.badge}</span>
            </div>
            <div class="text-2xl font-bold mt-2 ${c.color}">${c.value}</div>
            <div class="text-xs text-[var(--muted-foreground)] mt-1">${c.sub}</div>
          </div>
          <div class="w-full h-1.5 bg-[var(--background)] rounded-full overflow-hidden mt-3">
            <div class="h-full ${c.barColor} rounded-full" style="width: ${Math.min(100, Math.max(4, c.pct))}%"></div>
          </div>
        </div>
      `).join('');
    }

    function renderStatusAndRightPanel() {
      const { isAll, stats } = getActiveContext();
      const statusVisual = document.getElementById('statusVisual');
      const paceGenderCards = document.getElementById('paceGenderCards');

      const segments = [
        { label: 'Finished', count: stats.finished, pct: stats.finished_pct, color: 'bg-emerald-500', dot: 'bg-emerald-500' },
        { label: 'DNF (Stopped)', count: stats.dnf, pct: stats.dnf_pct, color: 'bg-amber-500', dot: 'bg-amber-500' },
        { label: 'CUT (Over Time Limit)', count: stats.cut, pct: stats.cut_pct, color: 'bg-orange-500', dot: 'bg-orange-500' },
        { label: 'DNS (Did Not Start)', count: stats.dns, pct: stats.dns_pct, color: 'bg-rose-500', dot: 'bg-rose-500' },
      ];
      if (stats.other > 0) {
        segments.push({ label: 'DQ / QRY', count: stats.other, pct: stats.other_pct, color: 'bg-purple-500', dot: 'bg-purple-500' });
      }

      statusVisual.innerHTML = `
        <div class="w-full h-4 rounded-xl overflow-hidden flex bg-[var(--background)] border border-[var(--border)]">
          ${segments.map(s => `<div class="${s.color} h-full" style="width:${s.pct}%" title="${s.label}: ${s.pct}% (${fmtNum(s.count)})"></div>`).join('')}
        </div>
        <div class="space-y-2.5">
          ${segments.map(s => `
            <div class="flex items-center justify-between text-xs">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full ${s.dot}"></span>
                <span class="font-medium text-[var(--foreground)]">${s.label}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[var(--muted-foreground)]">${fmtNum(s.count)} runners</span>
                <span class="font-semibold text-[var(--foreground)] w-14 text-right">${s.pct}%</span>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      if (isAll) {
        paceGenderCards.innerHTML = `
          <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
            <div class="text-xs text-[var(--muted-foreground)]">Overall Mean Pace</div>
            <div class="text-base font-bold text-[var(--foreground)] mt-0.5">${stats.avg_pace}</div>
            <div class="text-xs text-[var(--muted-foreground)]">All 4 distances weighted</div>
          </div>
          <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
            <div class="text-xs text-[var(--muted-foreground)]">Overall Combined DNF + CUT</div>
            <div class="text-base font-bold text-amber-500 mt-0.5">${stats.dnf_plus_cut_pct}%</div>
            <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(stats.dnf_plus_cut)} non-finishers on course</div>
          </div>
        `;
      } else {
        paceGenderCards.innerHTML = `
          <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
            <div class="text-xs text-[var(--muted-foreground)]">Male Avg Pace</div>
            <div class="text-base font-bold text-sky-500 mt-0.5">${stats.male_avg_pace}</div>
            <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(stats.male_finishers)} Male finishers</div>
          </div>
          <div class="p-3 rounded-xl bg-[var(--background)] border border-[var(--border)]">
            <div class="text-xs text-[var(--muted-foreground)]">Female Avg Pace</div>
            <div class="text-base font-bold text-pink-500 mt-0.5">${stats.female_avg_pace}</div>
            <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(stats.female_finishers)} Female finishers</div>
          </div>
        `;
      }

      const rightTitle = document.getElementById('rightPanelTitle');
      const rightSubtitle = document.getElementById('rightPanelSubtitle');
      const rightContent = document.getElementById('rightPanelContent');

      if (isAll) {
        rightTitle.textContent = 'Event-by-Event Finish, DNF, DNS & Pace Comparison';
        rightSubtitle.textContent = 'Click any event row to filter the dashboard to that specific race';
        rightContent.innerHTML = `
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th class="py-2.5 pr-3 font-semibold">Event</th>
                  <th class="py-2.5 px-2 font-semibold text-right">Total</th>
                  <th class="py-2.5 px-2 font-semibold text-right text-emerald-500">Finish %</th>
                  <th class="py-2.5 px-2 font-semibold text-right text-amber-500">DNF %</th>
                  <th class="py-2.5 px-2 font-semibold text-right text-orange-500">CUT %</th>
                  <th class="py-2.5 px-2 font-semibold text-right text-rose-500">DNS %</th>
                  <th class="py-2.5 px-2 font-semibold text-right">Avg Time</th>
                  <th class="py-2.5 pl-2 font-semibold text-right text-sky-500">Avg Pace</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border)] text-xs">
                ${DASHBOARD_DATA.events.map(ev => `
                  <tr onclick="selectEvent('${ev.event_slug}')" class="hover:bg-[var(--background)] cursor-pointer transition">
                    <td class="py-3 pr-3">
                      <div class="font-semibold text-[var(--foreground)]">${ev.event_name}</div>
                      <div class="text-xs text-[var(--muted-foreground)]">${ev.race_day} • ${ev.distance_km} KM</div>
                    </td>
                    <td class="py-3 px-2 text-right font-medium">${fmtNum(ev.total)}</td>
                    <td class="py-3 px-2 text-right">
                      <span class="font-semibold text-emerald-500">${ev.finished_pct}%</span>
                      <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(ev.finished)}</div>
                    </td>
                    <td class="py-3 px-2 text-right">
                      <span class="font-semibold text-amber-500">${ev.dnf_pct}%</span>
                      <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(ev.dnf)}</div>
                    </td>
                    <td class="py-3 px-2 text-right">
                      <span class="font-semibold text-orange-500">${ev.cut_pct}%</span>
                      <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(ev.cut)}</div>
                    </td>
                    <td class="py-3 px-2 text-right">
                      <span class="font-semibold text-rose-500">${ev.dns_pct}%</span>
                      <div class="text-xs text-[var(--muted-foreground)]">${fmtNum(ev.dns)}</div>
                    </td>
                    <td class="py-3 px-2 text-right font-mono font-medium">${ev.avg_time}</td>
                    <td class="py-3 pl-2 text-right font-mono font-semibold text-sky-500">${ev.avg_pace}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else {
        rightTitle.textContent = `${stats.event_name} — Finish Time & Pace Distribution`;
        rightSubtitle.textContent = `Distribution across ${fmtNum(stats.finished)} official finishers (Fastest: ${stats.best_time} • Median: ${stats.median_time})`;
        const maxBucket = Math.max(...stats.buckets.map(b => b.count), 1);
        rightContent.innerHTML = `
          <div class="space-y-2.5">
            ${stats.buckets.map(b => `
              <div class="grid grid-cols-12 items-center gap-2 text-xs">
                <div class="col-span-3 font-mono text-[var(--foreground)] font-medium">${b.label}</div>
                <div class="col-span-6">
                  <div class="w-full h-5 bg-[var(--background)] rounded-lg overflow-hidden border border-[var(--border)]">
                    <div class="h-full bg-emerald-500/80 rounded-lg" style="width: ${(b.count / maxBucket) * 100}%"></div>
                  </div>
                </div>
                <div class="col-span-3 text-right">
                  <span class="font-semibold text-[var(--foreground)]">${fmtNum(b.count)}</span>
                  <span class="text-[var(--muted-foreground)] ml-1">(${b.pct}%)</span>
                </div>
              </div>
            `).join('')}
          </div>
        `;
      }
    }

    let collapsedWinnerEvents = new Set();

    function toggleWinnerEvent(slug) {
      if (collapsedWinnerEvents.has(slug)) {
        collapsedWinnerEvents.delete(slug);
      } else {
        collapsedWinnerEvents.add(slug);
      }
      renderWinners();
    }

    function expandAllWinnerEvents() {
      collapsedWinnerEvents.clear();
      renderWinners();
    }

    function collapseAllWinnerEvents() {
      DASHBOARD_DATA.events.forEach(ev => collapsedWinnerEvents.add(ev.event_slug));
      renderWinners();
    }

    function renderWinners() {
      const { events } = getActiveContext();
      const container = document.getElementById('winnersContainer');
      const q = searchQuery.trim().toLowerCase();

      document.querySelectorAll('.gender-btn').forEach(btn => {
        const active = btn.dataset.gender === selectedGender;
        btn.className = `gender-btn px-3 py-1 rounded-md text-xs font-medium transition ${
          active ? 'bg-emerald-600 text-white' : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
        }`;
      });
      document.querySelectorAll('.mode-btn').forEach(btn => {
        const active = btn.dataset.mode === selectedViewMode;
        btn.className = `mode-btn px-3 py-1 rounded-md text-xs font-medium transition ${
          active ? 'bg-emerald-600 text-white' : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
        }`;
      });

      const sectionsHtml = events.map(ev => {
        const isCollapsed = collapsedWinnerEvents.has(ev.event_slug);
        const filteredCats = ev.categories.filter(c => {
          if (selectedGender !== 'ALL' && c.gender !== selectedGender) return false;
          if (!q) return true;
          const matchCat = c.category.toLowerCase().includes(q) || c.gender.toLowerCase().includes(q);
          const matchRunner = c.podium.some(
            p =>
              p.name.toLowerCase().includes(q) ||
              p.bib_no.toLowerCase().includes(q) ||
              p.country.toLowerCase().includes(q)
          );
          return matchCat || matchRunner;
        });

        if (!filteredCats.length) return '';

        if (selectedViewMode === 'table') {
          return `
            <div class="space-y-3 mb-5 last:mb-0">
              <div
                onclick="toggleWinnerEvent('${ev.event_slug}')"
                class="flex flex-wrap items-center justify-between gap-2 bg-[var(--background)] px-4 py-2.5 rounded-xl border border-[var(--border)] hover:border-emerald-500/40 cursor-pointer select-none transition"
              >
                <div class="flex items-center gap-2.5">
                  <span class="inline-flex items-center justify-center w-5 h-5 rounded bg-[var(--card)] border border-[var(--border)] text-xs font-bold text-[var(--foreground)]">${isCollapsed ? '▶' : '▼'}</span>
                  <span class="text-sm font-bold text-[var(--foreground)]">${ev.event_name}</span>
                  <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 font-semibold">${ev.distance_km} KM • ${ev.race_day}</span>
                  <span class="text-xs text-[var(--muted-foreground)]">(${filteredCats.length} categories)</span>
                </div>
                <div class="flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                  <span>Finish Rate: <strong class="text-emerald-500">${ev.finished_pct}%</strong> • Avg Pace: <strong class="text-sky-500">${ev.avg_pace}</strong></span>
                  <span class="px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] font-medium">${isCollapsed ? 'Expand' : 'Collapse'}</span>
                </div>
              </div>
              <div class="${isCollapsed ? 'hidden' : 'overflow-x-auto'}">
                <table class="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr class="border-b border-[var(--border)] text-[var(--muted-foreground)]">
                      <th class="py-2.5 px-3 font-semibold">Category</th>
                      <th class="py-2.5 px-2 font-semibold">Gender</th>
                      <th class="py-2.5 px-2 font-semibold">#1 Winner Name</th>
                      <th class="py-2.5 px-2 font-semibold">Bib No</th>
                      <th class="py-2.5 px-2 font-semibold">Country</th>
                      <th class="py-2.5 px-2 font-semibold text-right">Winning Time</th>
                      <th class="py-2.5 px-2 font-semibold text-right">Winner Pace</th>
                      <th class="py-2.5 px-2 font-semibold text-right">Cat Finishers</th>
                      <th class="py-2.5 px-3 font-semibold text-right">Cat Avg Pace</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-[var(--border)]">
                    ${filteredCats.map(c => {
                      const w = c.winner;
                      return `
                        <tr class="hover:bg-[var(--background)]">
                          <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">${c.category}</td>
                          <td class="py-2.5 px-2">
                            <span class="px-2 py-0.5 rounded text-xs font-medium ${
                              c.gender === 'Male' ? 'bg-sky-500/10 text-sky-500' : 'bg-pink-500/10 text-pink-500'
                            }">${c.gender}</span>
                          </td>
                          <td class="py-2.5 px-2 font-bold text-[var(--foreground)]">🏆 ${w ? w.name : '-'}</td>
                          <td class="py-2.5 px-2 font-mono text-[var(--muted-foreground)]">${w ? w.bib_no : '-'}</td>
                          <td class="py-2.5 px-2 text-[var(--muted-foreground)]">${w ? w.country : '-'}</td>
                          <td class="py-2.5 px-2 text-right font-mono font-bold text-emerald-500">${w ? w.time : '-'}</td>
                          <td class="py-2.5 px-2 text-right font-mono text-sky-500">${w ? w.pace : '-'}</td>
                          <td class="py-2.5 px-2 text-right text-[var(--muted-foreground)]">${fmtNum(c.finishers_count)} / ${fmtNum(c.total_entered)} (${c.finish_pct}%)</td>
                          <td class="py-2.5 px-3 text-right font-mono text-[var(--muted-foreground)]">${c.avg_pace}</td>
                        </tr>
                      `;
                    }).join('')}
                  </tbody>
                </table>
              </div>
            </div>
          `;
        }

        return `
          <div class="space-y-4 mb-5 last:mb-0">
            <div
              onclick="toggleWinnerEvent('${ev.event_slug}')"
              class="flex flex-wrap items-center justify-between gap-2 bg-[var(--background)] px-4 py-3 rounded-xl border border-[var(--border)] hover:border-emerald-500/40 cursor-pointer select-none transition"
            >
              <div class="flex items-center gap-2.5">
                <span class="inline-flex items-center justify-center w-5 h-5 rounded bg-[var(--card)] border border-[var(--border)] text-xs font-bold text-[var(--foreground)]">${isCollapsed ? '▶' : '▼'}</span>
                <span class="text-base font-bold text-[var(--foreground)]">${ev.event_name}</span>
                <span class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-semibold">${ev.distance_km} KM • ${ev.race_day}</span>
                <span class="text-xs text-[var(--muted-foreground)]">(${filteredCats.length} categories)</span>
              </div>
              <div class="flex flex-wrap items-center gap-4 text-xs text-[var(--muted-foreground)]">
                <span>Finish: <strong class="text-emerald-500">${ev.finished_pct}%</strong> (${fmtNum(ev.finished)})</span>
                <span>DNF: <strong class="text-amber-500">${ev.dnf_pct}%</strong> (${fmtNum(ev.dnf)})</span>
                <span>CUT: <strong class="text-orange-500">${ev.cut_pct}%</strong> (${fmtNum(ev.cut)})</span>
                <span>DNS: <strong class="text-rose-500">${ev.dns_pct}%</strong> (${fmtNum(ev.dns)})</span>
                <span>Avg Pace: <strong class="text-sky-500">${ev.avg_pace}</strong></span>
                <span class="px-2.5 py-0.5 rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] font-medium">${isCollapsed ? 'Expand' : 'Collapse'}</span>
              </div>
            </div>
            <div class="${isCollapsed ? 'hidden' : 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4'}">
              ${filteredCats.map(c => `
                <div class="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4 flex flex-col justify-between space-y-3">
                  <div class="flex items-start justify-between gap-2 border-b border-[var(--border)] pb-2.5">
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-bold text-[var(--foreground)]">${c.category}</span>
                        <span class="px-2 py-0.5 rounded text-xs font-semibold ${
                          c.gender === 'Male' ? 'bg-sky-500/10 text-sky-500' : 'bg-pink-500/10 text-pink-500'
                        }">${c.gender}</span>
                      </div>
                      <div class="text-xs text-[var(--muted-foreground)] mt-0.5">
                        ${fmtNum(c.finishers_count)} finishers (${c.finish_pct}% of ${fmtNum(c.total_entered)})
                      </div>
                    </div>
                    <div class="text-right">
                      <div class="text-xs text-[var(--muted-foreground)]">Cat Avg Pace</div>
                      <div class="text-xs font-mono font-semibold text-sky-500">${c.avg_pace}</div>
                    </div>
                  </div>
                  <div class="space-y-2">
                    ${c.podium.map((p, idx) => {
                      const medals = ['🥇 1st', '🥈 2nd', '🥉 3rd'];
                      const highlight = idx === 0 ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-[var(--card)] border-[var(--border)]';
                      return `
                        <div class="p-2.5 rounded-lg border ${highlight} flex items-center justify-between gap-2 text-xs">
                          <div class="min-w-0">
                            <div class="flex items-center gap-1.5">
                              <span class="font-bold text-[var(--foreground)]">${medals[idx] || '#' + p.category_rank}</span>
                              <span class="font-semibold text-[var(--foreground)] truncate">${p.name}</span>
                            </div>
                            <div class="text-xs text-[var(--muted-foreground)] mt-0.5">
                              Bib: <span class="font-mono">${p.bib_no}</span> • ${p.country} ${p.overall_pos ? '• Overall #' + p.overall_pos : ''}
                            </div>
                          </div>
                          <div class="text-right shrink-0">
                            <div class="font-mono font-bold text-emerald-500">${p.time}</div>
                            <div class="font-mono text-xs text-[var(--muted-foreground)]">${p.pace}</div>
                          </div>
                        </div>
                      `;
                    }).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }).join('');

      container.innerHTML = sectionsHtml || `
        <div class="text-center py-8 text-sm text-[var(--muted-foreground)]">
          No category winners match your current filter criteria.
        </div>
      `;
    }

    function selectEvent(slug) {
      selectedEventSlug = slug;
      if (slug === 'ALL') {
        runnerEventFilter = 'ALL';
      } else {
        const idx = DASHBOARD_DATA.event_lookup.findIndex(e => e.slug === slug);
        const val = idx >= 0 ? String(idx) : 'ALL';
        runnerEventFilter = val;
      }
      document.getElementById('runnerEventSelect').value = runnerEventFilter;
      renderAll();
      filterRunnersList();
    }

    const PIE_COLORS = [
      '#10b981', '#0ea5e9', '#f59e0b', '#ec4899', '#8b5cf6',
      '#ef4444', '#14b8a6', '#f97316', '#6366f1', '#84cc16', '#64748b'
    ];

    function buildPieSvg(slices, total, centerLabelTop, centerLabelBottom) {
      if (!total || !slices.length) {
        return `<div class="text-xs text-[var(--muted-foreground)] py-8 text-center">No country data</div>`;
      }
      const cx = 90, cy = 90, r = 74, innerR = 44;
      let cumAngle = -Math.PI / 2;
      const paths = slices.map((s, idx) => {
        const frac = s.count / total;
        const angle = frac * Math.PI * 2;
        const startAngle = cumAngle;
        const endAngle = cumAngle + angle;
        cumAngle = endAngle;
        const color = s.color || PIE_COLORS[idx % PIE_COLORS.length];

        if (frac >= 0.9999) {
          return `
            <circle cx="${cx}" cy="${cy}" r="${(r + innerR) / 2}" fill="none" stroke="${color}" stroke-width="${r - innerR}">
              <title>${escapeHtml(s.label)}: ${fmtNum(s.count)} (${s.pct}%)</title>
            </circle>
          `;
        }
        const x1 = cx + r * Math.cos(startAngle);
        const y1 = cy + r * Math.sin(startAngle);
        const x2 = cx + r * Math.cos(endAngle);
        const y2 = cy + r * Math.sin(endAngle);
        const ix1 = cx + innerR * Math.cos(endAngle);
        const iy1 = cy + innerR * Math.sin(endAngle);
        const ix2 = cx + innerR * Math.cos(startAngle);
        const iy2 = cy + innerR * Math.sin(startAngle);
        const largeArc = angle > Math.PI ? 1 : 0;
        const d = [
          `M ${x1.toFixed(2)} ${y1.toFixed(2)}`,
          `A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`,
          `L ${ix1.toFixed(2)} ${iy1.toFixed(2)}`,
          `A ${innerR} ${innerR} 0 ${largeArc} 0 ${ix2.toFixed(2)} ${iy2.toFixed(2)}`,
          'Z'
        ].join(' ');
        const clickAttr = s.clickable ? `onclick="filterByCountry('${escapeHtml(s.label)}')" class="cursor-pointer hover:opacity-85 transition"` : '';
        return `<path d="${d}" fill="${color}" stroke="var(--card)" stroke-width="1.5" ${clickAttr}><title>${escapeHtml(s.label)}: ${fmtNum(s.count)} runners (${s.pct}%)</title></path>`;
      }).join('');

      return `
        <svg viewBox="0 0 180 180" class="w-44 h-44 shrink-0 mx-auto">
          ${paths}
          <text x="${cx}" y="${cy - 4}" text-anchor="middle" fill="var(--foreground)" class="text-sm font-bold" style="font-size:14px;font-weight:700;">${escapeHtml(centerLabelTop)}</text>
          <text x="${cx}" y="${cy + 13}" text-anchor="middle" fill="var(--muted-foreground)" class="text-xs" style="font-size:10px;">${escapeHtml(centerLabelBottom)}</text>
        </svg>
      `;
    }

    function filterByCountry(countryName) {
      if (!countryName || countryName === 'Other Countries' || countryName === 'International') return;
      runnerQuery = countryName;
      document.getElementById('runnerSearchInput').value = countryName;
      filterRunnersList();
      document.getElementById('runnerSearchInput').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function renderCountryJoiners() {
      const { isAll, stats } = getActiveContext();
      const evIdx = isAll ? null : DASHBOARD_DATA.event_lookup.findIndex(e => e.slug === selectedEventSlug);
      const rows = evIdx === null
        ? DASHBOARD_DATA.runners
        : DASHBOARD_DATA.runners.filter(r => r[0] === evIdx);

      const total = rows.length;
      const counts = {};
      rows.forEach(r => {
        const c = (r[9] && r[9] !== '-') ? r[9] : 'Unknown';
        counts[c] = (counts[c] || 0) + 1;
      });

      const knownCountries = Object.entries(counts)
        .filter(([country]) => country !== 'Unknown')
        .map(([country, count]) => ({
          country,
          count,
          pct: total ? Number((count * 100 / total).toFixed(2)) : 0
        }))
        .sort((a, b) => b.count - a.count);

      const distinctCountriesCount = knownCountries.length;
      const idnCount = counts['Indonesia'] || 0;
      const intlCountries = knownCountries.filter(c => c.country !== 'Indonesia');
      const intlKnownTotal = intlCountries.reduce((acc, c) => acc + c.count, 0);
      const unknownCount = counts['Unknown'] || 0;
      const knownTotal = idnCount + intlKnownTotal;

      const idnPct = knownTotal ? (idnCount * 100 / knownTotal).toFixed(2) : '0.00';
      const intlPct = knownTotal ? (intlKnownTotal * 100 / knownTotal).toFixed(2) : '0.00';

      document.getElementById('countrySectionTitle').textContent = isAll
        ? 'Country Joiners — Participant Nationality Breakdown (All Events)'
        : `Country Joiners — ${stats.event_name}`;
      document.getElementById('countryTotalBadge').textContent = `${distinctCountriesCount} Countries • ${fmtNum(intlKnownTotal)} International (${intlPct}%)`;

      // Pie 1: Domestic (Indonesia) vs International
      const overallSlices = [
        { label: 'Indonesia', count: idnCount, pct: idnPct, color: '#10b981', clickable: true },
        { label: 'International', count: intlKnownTotal, pct: intlPct, color: '#0ea5e9', clickable: false }
      ].filter(s => s.count > 0);

      // Pie 2: International Joiners Breakdown (excluding Indonesia)
      const topIntl = intlCountries.slice(0, 8).map((c, idx) => ({
        label: c.country,
        count: c.count,
        pct: intlKnownTotal ? (c.count * 100 / intlKnownTotal).toFixed(1) : '0.0',
        color: PIE_COLORS[(idx + 1) % PIE_COLORS.length],
        clickable: true
      }));
      const otherIntlCount = intlCountries.slice(8).reduce((acc, c) => acc + c.count, 0);
      if (otherIntlCount > 0) {
        topIntl.push({
          label: 'Other Countries',
          count: otherIntlCount,
          pct: intlKnownTotal ? (otherIntlCount * 100 / intlKnownTotal).toFixed(1) : '0.0',
          color: '#64748b',
          clickable: false
        });
      }

      const pie1Html = buildPieSvg(overallSlices, knownTotal, `${idnPct}%`, 'Indonesia');
      const pie2Html = buildPieSvg(topIntl, intlKnownTotal, fmtNum(intlKnownTotal), 'Foreign Joiners');

      const topTableRows = knownCountries.slice(0, 10).map((c, idx) => {
        const badgeColor = c.country === 'Indonesia' ? '#10b981' : PIE_COLORS[idx % PIE_COLORS.length];
        return `
          <tr onclick="filterByCountry('${escapeHtml(c.country)}')" class="hover:bg-[var(--card)] cursor-pointer transition">
            <td class="py-1.5 px-2.5 text-xs font-mono text-[var(--muted-foreground)]">#${idx + 1}</td>
            <td class="py-1.5 px-2.5 text-xs font-semibold text-[var(--foreground)]">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:${badgeColor}"></span>
                <span class="truncate">${escapeHtml(c.country)}</span>
              </div>
            </td>
            <td class="py-1.5 px-2.5 text-xs text-right font-mono font-semibold text-[var(--foreground)]">${fmtNum(c.count)}</td>
            <td class="py-1.5 px-2.5 text-xs text-right font-mono text-emerald-500">${c.pct.toFixed(2)}%</td>
          </tr>
        `;
      }).join('');

      document.getElementById('countryChartsContainer').innerHTML = `
        <!-- Left: Pie 1 (All Joiners: Indonesia vs International) -->
        <div class="lg:col-span-3 h-full bg-[var(--background)] border border-[var(--border)] rounded-xl p-5 flex flex-col justify-between">
          <div class="text-center border-b border-[var(--border)] pb-3">
            <div class="text-sm font-bold text-[var(--foreground)]">All Joiners (Domestic vs Foreign)</div>
            <div class="text-xs text-[var(--muted-foreground)] mt-0.5">${fmtNum(total)} total participants</div>
          </div>
          <div class="my-auto py-3 flex items-center justify-center">
            ${pie1Html}
          </div>
          <div class="w-full space-y-2 text-xs border-t border-[var(--border)] pt-3">
            <div onclick="filterByCountry('Indonesia')" class="flex items-center justify-between cursor-pointer hover:opacity-80">
              <span class="flex items-center gap-2 font-medium text-[var(--foreground)]"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0"></span>Indonesia</span>
              <span class="font-mono font-semibold text-[var(--foreground)]">${fmtNum(idnCount)} (${idnPct}%)</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="flex items-center gap-2 font-medium text-[var(--foreground)]"><span class="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0"></span>International (${Math.max(0, distinctCountriesCount - 1)} nations)</span>
              <span class="font-mono font-semibold text-[var(--foreground)]">${fmtNum(intlKnownTotal)} (${intlPct}%)</span>
            </div>
            ${unknownCount > 0 ? `
              <div class="flex items-center justify-between text-[var(--muted-foreground)]">
                <span class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-slate-400 shrink-0"></span>Unspecified / Other</span>
                <span class="font-mono">${fmtNum(unknownCount)}</span>
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Middle: Pie 2 (International Joiners by Country Pie Chart) -->
        <div class="lg:col-span-5 h-full bg-[var(--background)] border border-[var(--border)] rounded-xl p-5 flex flex-col justify-between">
          <div class="text-center border-b border-[var(--border)] pb-3">
            <div class="text-sm font-bold text-[var(--foreground)]">International Joiners Pie Chart</div>
            <div class="text-xs text-[var(--muted-foreground)] mt-0.5">Share among ${fmtNum(intlKnownTotal)} foreign runners (${Math.max(0, distinctCountriesCount - 1)} countries)</div>
          </div>
          <div class="my-auto py-3 flex flex-col sm:flex-row items-center justify-center gap-5">
            ${pie2Html}
            <div class="w-full flex-1 space-y-1.5 text-xs">
              ${topIntl.map(s => `
                <div ${s.clickable ? `onclick="filterByCountry('${escapeHtml(s.label)}')" class="flex items-center justify-between gap-2 py-0.5 px-1.5 rounded hover:bg-[var(--card)] cursor-pointer transition"` : 'class="flex items-center justify-between gap-2 py-0.5 px-1.5"'}>
                  <span class="flex items-center gap-2 min-w-0">
                    <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:${s.color}"></span>
                    <span class="font-medium text-[var(--foreground)] truncate">${escapeHtml(s.label)}</span>
                  </span>
                  <span class="font-mono font-semibold text-[var(--foreground)] whitespace-nowrap shrink-0">${fmtNum(s.count)} <span class="text-[var(--muted-foreground)]">(${s.pct}%)</span></span>
                </div>
              `).join('')}
            </div>
          </div>
          <div class="text-center text-xs text-[var(--muted-foreground)] border-t border-[var(--border)] pt-3">
            Click any slice or country name to filter runner results below
          </div>
        </div>

        <!-- Right: Top 10 Countries Table -->
        <div class="lg:col-span-4 h-full bg-[var(--background)] border border-[var(--border)] rounded-xl p-5 flex flex-col justify-between">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <div>
              <div class="text-sm font-bold text-[var(--foreground)]">Top 10 Countries by Runner Count</div>
              <div class="text-xs text-[var(--muted-foreground)] mt-0.5">Click any country row to search</div>
            </div>
          </div>
          <div class="overflow-x-auto my-auto py-1">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="border-b border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  <th class="py-1.5 px-2.5 font-semibold">Rank</th>
                  <th class="py-1.5 px-2.5 font-semibold">Country</th>
                  <th class="py-1.5 px-2.5 font-semibold text-right">Runners</th>
                  <th class="py-1.5 px-2.5 font-semibold text-right">Share %</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border)]">
                ${topTableRows}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    function renderAll() {
      renderTabs();
      renderKPIs();
      renderStatusAndRightPanel();
      renderCountryJoiners();
      renderWinners();
    }

    // Event listeners for Runner Table
    document.getElementById('runnerSearchInput').addEventListener('input', e => {
      runnerQuery = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerEventSelect').addEventListener('change', e => {
      runnerEventFilter = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerCategorySelect').addEventListener('change', e => {
      runnerCategoryFilter = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerGenderSelect').addEventListener('change', e => {
      runnerGenderFilter = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerStatusSelect').addEventListener('change', e => {
      runnerStatusFilter = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerPageSizeSelect').addEventListener('change', e => {
      runnerPageSize = Number(e.target.value);
      runnerPage = 1;
      renderRunnerTable();
    });
    document.getElementById('prevPageBtn').addEventListener('click', () => {
      if (runnerPage > 1) {
        runnerPage--;
        renderRunnerTable();
      }
    });
    document.getElementById('nextPageBtn').addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredRunners.length / runnerPageSize));
      if (runnerPage < totalPages) {
        runnerPage++;
        renderRunnerTable();
      }
    });
    document.getElementById('resetRunnerFiltersBtn').addEventListener('click', () => {
      runnerQuery = '';
      runnerEventFilter = 'ALL';
      runnerCategoryFilter = 'ALL';
      runnerGenderFilter = 'ALL';
      runnerStatusFilter = 'ALL';
      document.getElementById('runnerSearchInput').value = '';
      document.getElementById('runnerEventSelect').value = 'ALL';
      document.getElementById('runnerCategorySelect').value = 'ALL';
      document.getElementById('runnerGenderSelect').value = 'ALL';
      document.getElementById('runnerStatusSelect').value = 'ALL';
      document.getElementById('runnerDetailDrawer').classList.add('hidden');
      filterRunnersList();
    });

    // Event listeners for Category Winners
    document.querySelectorAll('.gender-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedGender = btn.dataset.gender;
        renderWinners();
      });
    });

    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedViewMode = btn.dataset.mode;
        renderWinners();
      });
    });

    document.getElementById('winnerSearch').addEventListener('input', e => {
      searchQuery = e.target.value;
      renderWinners();
    });

    initRunnerFilterOptions();
    renderAll();
    filterRunnersList();
  </script>
</body>
</html>
"""


def main():
    data = compute_dashboard_data()
    html = HTML_TEMPLATE.replace("__DASHBOARD_JSON__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out_file = WORKSPACE / "dashboard.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Created {out_file} ({len(html)} bytes)")
    index_file = WORKSPACE / "index.html"
    index_file.write_text(html, encoding="utf-8")
    print(f"Created {index_file} ({len(html)} bytes)")
    if ARTIFACT_PATH.parent.exists():
        ARTIFACT_PATH.write_text(html, encoding="utf-8")
        print(f"Updated artifact {ARTIFACT_PATH} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
