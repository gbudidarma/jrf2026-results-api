import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
ARTIFACT_PATH = Path(
    "/Users/gbudidarma/.gemini/antigravity/brain/c6ce6403-c8c9-4e9f-ac00-8d48764a74f9/jrf_race_dashboard.html"
)

SILABAN_CLASS_ORDER = [
    "TT1",
    "TT2",
    "TT3",
    "TT-DSC",
    "TT5",
    "TT6",
    "TT7",
    "TT8",
    "TT9",
    "TTp",
    "TT-Cheering",
]


def load_silaban_csv() -> dict[str, dict[str, str]]:
    csv_path = WORKSPACE / "KelasBersamaSIlaban.csv"
    mapping: dict[str, dict[str, str]] = {}
    if not csv_path.exists():
        return mapping
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        sample = f.read(1024)
        f.seek(0)
        delim = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            bib = (row.get("BIB") or "").strip().upper()
            if bib:
                mapping[bib] = {
                    "class": (row.get("Class") or "").strip(),
                    "remark": (row.get("Remark") or "").strip(),
                    "category": (row.get("Category") or "").strip(),
                }
    return mapping


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


def compute_netto_sec(splits_dict: dict | None, split_cols: list[str]) -> int | None:
    if not splits_dict or not split_cols:
        return None
    vals = [time_to_sec(splits_dict.get(c)) for c in split_cols]
    if not vals or vals[-1] is None:
        return None
    if any(v is None for v in vals):
        last_none = max(i for i, v in enumerate(vals) if v is None)
        tail = vals[last_none + 1 :]
        return sum(tail) if tail else None
    return sum(vals)


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

EVENT_BUCKET_CONFIG = {
    "mybca_jakarta_half_marathon": {
        "start_sec": 1 * 3600,
        "cot_sec": 3 * 3600 + 45 * 60,
        "step_sec": 15 * 60,
        "cot_label": "03:45:00",
        "over_cot_label": "> 3:45:00",
        "step_label": "15-min range",
    },
    "hydroplus_marathon": {
        "start_sec": 2 * 3600,
        "cot_sec": 5 * 3600,
        "step_sec": 30 * 60,
        "cot_label": "05:00:00",
        "over_cot_label": "> 5:00:00",
        "step_label": "30-min range",
    },
    "le_minerale_10k": {
        "start_sec": 30 * 60,
        "cot_sec": 2 * 3600,
        "step_sec": 10 * 60,
        "cot_label": "02:00:00",
        "over_cot_label": "> 2:00:00",
        "step_label": "10-min range",
    },
    "samsung_galaxy_5k": {
        "start_sec": 10 * 60,
        "cot_sec": 1 * 3600,
        "step_sec": 5 * 60,
        "cot_label": "01:00:00",
        "over_cot_label": "> 1:00:00",
        "step_label": "5-min range",
    },
}


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
        clean_splits = [s for s in ev["split_checkpoints"] if s != "RTW"]
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
        netto_secs = [
            ns for ns in (compute_netto_sec(r.get("splits"), clean_splits) for r in fin_rows) if ns is not None
        ]
        male_secs = [time_to_sec(r["time"]) for r in fin_rows if r.get("gender") == "Male"]
        female_secs = [time_to_sec(r["time"]) for r in fin_rows if r.get("gender") == "Female"]

        avg_sec = statistics.mean(fin_secs) if fin_secs else None
        med_sec = statistics.median(fin_secs) if fin_secs else None
        min_sec = min(fin_secs) if fin_secs else None
        max_sec = max(fin_secs) if fin_secs else None

        avg_netto_sec = statistics.mean(netto_secs) if netto_secs else None
        med_netto_sec = statistics.median(netto_secs) if netto_secs else None
        min_netto_sec = min(netto_secs) if netto_secs else None

        avg_pace_sec = (avg_sec / dist) if avg_sec else None
        med_pace_sec = (med_sec / dist) if med_sec else None
        best_pace_sec = (min_sec / dist) if min_sec else None
        male_pace_sec = (statistics.mean(male_secs) / dist) if male_secs else None
        female_pace_sec = (statistics.mean(female_secs) / dist) if female_secs else None

        all_paces.extend([s / dist for s in fin_secs])

        buckets = []
        b_cfg = EVENT_BUCKET_CONFIG.get(slug)
        if fin_secs and b_cfg:
            b_start_sec = b_cfg["start_sec"]
            b_cot_sec = b_cfg["cot_sec"]
            b_step_sec = b_cfg["step_sec"]
            bucket_count = int((b_cot_sec - b_start_sec) // b_step_sec)
            for i in range(bucket_count):
                b_start = b_start_sec + i * b_step_sec
                b_end = b_start_sec + (i + 1) * b_step_sec
                min_s = 0 if i == 0 else b_start
                max_s = b_cot_sec if i == bucket_count - 1 else (b_end - 1)
                cnt = sum(1 for s in fin_secs if min_s <= s <= max_s)
                buckets.append(
                    {
                        "label": f"{sec_to_hms(b_start)[:5]}–{sec_to_hms(b_end)[:5]}",
                        "pace_label": f"{sec_to_pace(b_start / dist)} – {sec_to_pace(b_end / dist)}",
                        "count": cnt,
                        "pct": round(cnt * 100.0 / len(fin_secs), 1),
                        "min_sec": min_s,
                        "max_sec": max_s,
                        "is_over_cot": False,
                    }
                )
            over_min_s = b_cot_sec + 1
            over_max_s = 999999
            over_cnt = sum(1 for s in fin_secs if s >= over_min_s)
            buckets.append(
                {
                    "label": b_cfg["over_cot_label"],
                    "pace_label": f"> {sec_to_pace(b_cot_sec / dist)}",
                    "count": over_cnt,
                    "pct": round(over_cnt * 100.0 / len(fin_secs), 1),
                    "min_sec": over_min_s,
                    "max_sec": over_max_s,
                    "is_over_cot": True,
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
                r_netto_sec = compute_netto_sec(runner.get("splits"), clean_splits)
                podium.append(
                    {
                        "category_rank": rank_idx,
                        "overall_pos": runner["position"],
                        "bib_no": runner["bib_no"],
                        "name": runner["name"],
                        "country": runner.get("country") or "-",
                        "time": runner["time"],
                        "netto_time": sec_to_hms(r_netto_sec) if r_netto_sec is not None else runner["time"],
                        "pace": sec_to_pace(r_sec / dist) if r_sec else "-",
                        "netto_pace": sec_to_pace(r_netto_sec / dist) if r_netto_sec else (sec_to_pace(r_sec / dist) if r_sec else "-"),
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
                "avg_netto_time": sec_to_hms(avg_netto_sec),
                "median_netto_time": sec_to_hms(med_netto_sec),
                "best_netto_time": sec_to_hms(min_netto_sec),
                "avg_pace": sec_to_pace(avg_pace_sec),
                "median_pace": sec_to_pace(med_pace_sec),
                "best_pace": sec_to_pace(best_pace_sec),
                "male_avg_pace": sec_to_pace(male_pace_sec),
                "female_avg_pace": sec_to_pace(female_pace_sec),
                "male_finishers": len(male_secs),
                "female_finishers": len(female_secs),
                "cot_label": b_cfg["cot_label"] if b_cfg else "-",
                "step_label": b_cfg["step_label"] if b_cfg else "-",
                "buckets": buckets,
                "categories": categories_data,
            }
        )

    silaban_by_bib = load_silaban_csv()
    silaban_class_counts = Counter()
    silaban_remark_counts = Counter()

    # Encode all 36,306 runners into a compact array for instant client-side search & pagination
    # Format per runner:
    # [0: event_idx, 1: pos_or_null, 2: status_str, 3: bib_no, 4: name, 5: bruto_time_str,
    #  6: bruto_pace_str, 7: category, 8: gender, 9: country, 10: splits_array, 11: is_podium (1/0),
    #  12: cat_rank, 13: netto_time_str, 14: netto_pace_str, 15: partner_runner_idx,
    #  16: remark_str, 17: silaban_class_str]
    compact_runners = []
    for r in all_results:
        ev_idx = event_slug_to_idx[r["event_slug"]]
        ev_obj = events_meta[ev_idx]
        dist = event_dist_by_idx[ev_idx]
        split_cols = event_splits_by_idx[ev_idx]
        t_str = r.get("time") or ""
        t_sec = time_to_sec(t_str) if r["status"] == "FINISHED" else None
        p_str = sec_to_pace(t_sec / dist).replace(" /km", "") if t_sec else ""
        netto_sec = compute_netto_sec(r.get("splits"), split_cols) if r["status"] == "FINISHED" else None
        netto_str = sec_to_hms(netto_sec) if netto_sec is not None else ""
        netto_p_str = sec_to_pace(netto_sec / dist).replace(" /km", "") if netto_sec else p_str
        splits_arr = [r["splits"].get(c) or "" for c in split_cols]
        bib = r["bib_no"]
        pos = r["position"]
        is_pod = 1 if (bib in ev_obj.get("_podium_bibs", set()) or (pos is not None and pos <= 3)) else 0
        cat_rk = ev_obj.get("_cat_rank_by_bib", {}).get(bib)
        s_info = silaban_by_bib.get(bib.strip().upper(), {})
        remark_str = s_info.get("remark") or r.get("remark") or ""
        class_str = s_info.get("class") or r.get("class") or ""
        if remark_str:
            silaban_remark_counts[remark_str] += 1
        if class_str:
            silaban_class_counts[class_str] += 1

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
                netto_str,
                netto_p_str,
                -1,
                remark_str,
                class_str,
            ]
        )

    ordered_classes = [
        {"code": c, "count": silaban_class_counts[c]}
        for c in SILABAN_CLASS_ORDER
        if silaban_class_counts[c] > 0
    ] + [
        {"code": c, "count": cnt}
        for c, cnt in sorted(silaban_class_counts.items())
        if c not in SILABAN_CLASS_ORDER
    ]
    silaban_meta = {
        "total": sum(silaban_remark_counts.values()),
        "remarks": [{"name": k, "count": v} for k, v in silaban_remark_counts.items()],
        "classes": ordered_classes,
    }

    # Identify Double Category Runners (registered in both Day 1 and Day 2)
    by_day1 = defaultdict(list)
    by_day2 = defaultdict(list)
    for r_idx, r in enumerate(all_results):
        nm = " ".join((r.get("name") or "").strip().upper().split())
        if not nm or nm in ("UNKNOWN", "-") or nm.startswith("PACER"):
            continue
        gen = r.get("gender") or "Unknown"
        ctry = r.get("country") or "-"
        if r["race_day"] == "Day 1":
            by_day1[(nm, gen, ctry)].append(r_idx)
        elif r["race_day"] == "Day 2":
            by_day2[(nm, gen, ctry)].append(r_idx)

    matched_pairs_idx = []
    used_d1 = set()
    used_d2 = set()

    # Pass 1: Exact 1-to-1 normalized (name, gender, country) matches across Day 1 and Day 2
    for key, d1_indices in by_day1.items():
        if key in by_day2 and len(d1_indices) == 1 and len(by_day2[key]) == 1:
            i1 = d1_indices[0]
            i2 = by_day2[key][0]
            matched_pairs_idx.append((i1, i2))
            used_d1.add(i1)
            used_d2.add(i2)

    # Pass 2: 2+ word prefix matches for unmatched singletons with same (gender, country)
    # e.g., "CUT NOOSY" (Day 1 HM) <-> "CUT NOOSY KEUMALA FAJRI" (Day 2 10K)
    d1_prefix2 = defaultdict(list)
    d2_prefix2 = defaultdict(list)
    for (nm, gen, ctry), d1_indices in by_day1.items():
        if len(d1_indices) == 1 and d1_indices[0] not in used_d1:
            words = nm.split()
            if len(words) >= 2:
                d1_prefix2[(words[0], words[1], gen, ctry)].append((words, d1_indices[0]))

    for (nm, gen, ctry), d2_indices in by_day2.items():
        if len(d2_indices) == 1 and d2_indices[0] not in used_d2:
            words = nm.split()
            if len(words) >= 2:
                d2_prefix2[(words[0], words[1], gen, ctry)].append((words, d2_indices[0]))

    for pkey, list1 in d1_prefix2.items():
        if pkey in d2_prefix2 and len(list1) == 1 and len(d2_prefix2[pkey]) == 1:
            w1, i1 = list1[0]
            w2, i2 = d2_prefix2[pkey][0]
            min_len = min(len(w1), len(w2))
            if w1[:min_len] == w2[:min_len]:
                matched_pairs_idx.append((i1, i2))
                used_d1.add(i1)
                used_d2.add(i2)

    combo_order = {"HM_FM": 0, "HM_10K": 1, "5K_FM": 2, "5K_10K": 3}
    double_pairs_raw = []
    combo_stats = {
        "ALL": {"reg": 0, "reg_m": 0, "reg_f": 0, "fin_both": 0, "fin_m": 0, "fin_f": 0},
        "HM_FM": {"reg": 0, "reg_m": 0, "reg_f": 0, "fin_both": 0, "fin_m": 0, "fin_f": 0},
        "HM_10K": {"reg": 0, "reg_m": 0, "reg_f": 0, "fin_both": 0, "fin_m": 0, "fin_f": 0},
        "5K_FM": {"reg": 0, "reg_m": 0, "reg_f": 0, "fin_both": 0, "fin_m": 0, "fin_f": 0},
        "5K_10K": {"reg": 0, "reg_m": 0, "reg_f": 0, "fin_both": 0, "fin_m": 0, "fin_f": 0},
    }

    for i1, i2 in matched_pairs_idx:
        compact_runners[i1][15] = i2
        compact_runners[i2][15] = i1
        r1 = compact_runners[i1]
        r2 = compact_runners[i2]
        ev1_slug = event_lookup[r1[0]]["slug"]
        ev2_slug = event_lookup[r2[0]]["slug"]
        d1_short = "HM" if ev1_slug == "mybca_jakarta_half_marathon" else "5K"
        d2_short = "FM" if ev2_slug == "hydroplus_marathon" else "10K"
        combo_code = f"{d1_short}_{d2_short}"
        total_dist = event_lookup[r1[0]]["dist"] + event_lookup[r2[0]]["dist"]
        gen = r1[8]

        fin1 = r1[2] == "FINISHED" and time_to_sec(r1[5]) is not None
        fin2 = r2[2] == "FINISHED" and time_to_sec(r2[5]) is not None
        both_fin = 1 if (fin1 and fin2) else 0

        combo_stats["ALL"]["reg"] += 1
        combo_stats[combo_code]["reg"] += 1
        if gen == "Male":
            combo_stats["ALL"]["reg_m"] += 1
            combo_stats[combo_code]["reg_m"] += 1
        elif gen == "Female":
            combo_stats["ALL"]["reg_f"] += 1
            combo_stats[combo_code]["reg_f"] += 1

        if both_fin:
            combo_stats["ALL"]["fin_both"] += 1
            combo_stats[combo_code]["fin_both"] += 1
            if gen == "Male":
                combo_stats["ALL"]["fin_m"] += 1
                combo_stats[combo_code]["fin_m"] += 1
            elif gen == "Female":
                combo_stats["ALL"]["fin_f"] += 1
                combo_stats[combo_code]["fin_f"] += 1
            b_sum = (time_to_sec(r1[5]) or 0) + (time_to_sec(r2[5]) or 0)
            n_sum = (time_to_sec(r1[13]) or time_to_sec(r1[5]) or 0) + (time_to_sec(r2[13]) or time_to_sec(r2[5]) or 0)
            comb_bruto = sec_to_hms(b_sum)
            comb_netto = sec_to_hms(n_sum)
            comb_pace = sec_to_pace(n_sum / total_dist)
            sort_time = n_sum
        else:
            comb_bruto = "-"
            comb_netto = "-"
            comb_pace = "-"
            sort_time = 999999

        double_pairs_raw.append(
            (
                0 if both_fin else 1,
                combo_order.get(combo_code, 9),
                sort_time,
                [i1, i2, combo_code, both_fin, comb_bruto, comb_netto, comb_pace],
            )
        )

    double_pairs_raw.sort(key=lambda x: (x[0], x[1], x[2]))
    double_pairs = [x[3] for x in double_pairs_raw]

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
        "double_summary": combo_stats,
        "double_pairs": double_pairs,
        "silaban_meta": silaban_meta,
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
    <div id="topHeaderSection" class="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-[var(--foreground)]">
            Jakarta Running Festival — Race Analytics &amp; Results Explorer
          </h1>
          <p class="text-sm text-[var(--muted-foreground)] mt-1">
            Finish rates, DNF / Cut-off / DNS percentages, Bruto &amp; Netto finish times, average pace metrics, category podiums, and full 36,306-runner search. Data from <a href="https://results.scorenow.co.id" target="_blank" rel="noopener noreferrer" class="font-medium text-emerald-500 hover:underline">https://results.scorenow.co.id</a>
          </p>
        </div>
        <!-- Simple Light / Dark Mode Switcher -->
        <div class="inline-flex items-center rounded-lg border border-[var(--border)] p-0.5 bg-[var(--background)] self-start shrink-0" role="group" aria-label="Theme Switch">
          <button
            id="themeLightBtn"
            onclick="setTheme('light')"
            class="px-3 py-1 rounded-md text-xs font-medium transition"
          >
            Light
          </button>
          <button
            id="themeDarkBtn"
            onclick="setTheme('dark')"
            class="px-3 py-1 rounded-md text-xs font-medium transition"
          >
            Dark
          </button>
        </div>
      </div>
      <!-- Event Selector Bar -->
      <div class="pt-4 border-t border-[var(--border)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] shrink-0">Race Event Filter</span>
        <div id="eventTabs" class="flex flex-wrap items-center gap-2"></div>
      </div>
      <!-- Global Remark & Class Filter Bar (KelasBersamaSIlaban.csv joined by BIB No) -->
      <div class="pt-4 border-t border-[var(--border)] flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] shrink-0">Global Remark &amp; Class Filter</span>
          <div id="globalRemarkTabs" class="inline-flex flex-wrap items-center gap-1.5"></div>
          <div class="flex items-center gap-1.5">
            <label for="globalClassSelect" class="text-xs font-medium text-[var(--muted-foreground)] ml-1">Class:</label>
            <select
              id="globalClassSelect"
              onchange="selectGlobalClass(this.value)"
              class="px-3 py-1.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs font-semibold focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">All Classes</option>
            </select>
          </div>
          <button
            id="resetGlobalFilterBtn"
            onclick="resetGlobalFilter()"
            class="hidden px-2.5 py-1.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-500 text-xs font-semibold hover:bg-rose-500/20 transition"
          >
            ✕ Reset Global Filter
          </button>
        </div>
        <div id="globalFilterActiveBadge" class="hidden text-xs font-medium px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500"></div>
      </div>
    </div>

    <!-- Sticky Section Navigation Menu -->
    <div class="sticky top-2 z-40 flex flex-col items-end">
      <nav id="stickyNavExpanded" class="w-full bg-[var(--card)]/95 backdrop-blur-md border border-[var(--border)] rounded-xl px-3.5 py-2 shadow-sm flex flex-wrap items-center justify-between gap-2" aria-label="Section Navigation">
        <div class="flex flex-wrap items-center gap-1.5">
          <button
            data-nav-target="overviewSection"
            onclick="scrollToSection('overviewSection')"
            class="nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition bg-emerald-600 text-white shadow-sm"
          >
            Overview &amp; Pace
          </button>
          <button
            data-nav-target="countrySection"
            onclick="scrollToSection('countrySection')"
            class="nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--background)]"
          >
            Country Joiners
          </button>
          <button
            data-nav-target="winnersSection"
            onclick="scrollToSection('winnersSection')"
            class="nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--background)]"
          >
            Category Winners &amp; Podiums
          </button>
          <button
            data-nav-target="runnerTableSection"
            onclick="scrollToSection('runnerTableSection')"
            class="nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--background)]"
          >
            All Runners Results
          </button>
          <button
            data-nav-target="doubleRunnersSection"
            onclick="scrollToSection('doubleRunnersSection')"
            class="nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--background)]"
          >
            Double Category Runners
          </button>
        </div>
        <div class="flex items-center gap-1.5 ml-auto">
          <button
            onclick="scrollToSection('topHeaderSection')"
            class="px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition"
            title="Scroll back to top"
          >
            ↑ Top
          </button>
          <button
            onclick="toggleNavMenu(true)"
            class="px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition"
            title="Hide navigation menu"
          >
            Hide Menu
          </button>
        </div>
      </nav>
      <div id="stickyNavCollapsed" class="hidden inline-flex items-center gap-1.5 bg-[var(--card)]/95 backdrop-blur-md border border-[var(--border)] rounded-xl px-2.5 py-1.5 shadow-sm">
        <button
          onclick="toggleNavMenu(false)"
          class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white text-xs font-semibold shadow-sm transition hover:bg-emerald-500"
        >
          Menu
        </button>
        <button
          onclick="scrollToSection('topHeaderSection')"
          class="px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition"
          title="Scroll back to top"
        >
          ↑ Top
        </button>
      </div>
    </div>

    <!-- Top KPI Cards -->
    <div id="overviewSection" class="scroll-mt-20 space-y-6">
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
    </div>

    <!-- Country Joiners Pie Chart & Nationality Breakdown Section -->
    <div id="countrySection" class="scroll-mt-20 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-5">
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
    <div id="winnersSection" class="scroll-mt-20 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-5">
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
    <div id="runnerTableSection" class="scroll-mt-20 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-[var(--border)]">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-[var(--foreground)]">All-Events Race Results — All Runners (With Podium)</h2>
            <span id="runnerResultCountBadge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500">36,306 runners</span>
            <span id="activeBucketFilterBadge" class="hidden inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-500 border border-sky-500/30"></span>
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
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
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
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Remark</label>
          <select
            id="runnerRemarkSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Remarks</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Class</label>
          <select
            id="runnerClassSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Classes</option>
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
              <th onclick="setRunnerSort('pos')" class="py-3 px-3 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Overall Position">
                <span class="inline-flex items-center gap-1">Overall Pos / Status <span id="sortIcon_pos" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('catRank')" class="py-3 px-2 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Category Rank">
                <span class="inline-flex items-center gap-1">Cat Rank <span id="sortIcon_catRank" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('bib')" class="py-3 px-2.5 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Bib Number">
                <span class="inline-flex items-center gap-1">Bib No <span id="sortIcon_bib" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('name')" class="py-3 px-3 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Runner Name">
                <span class="inline-flex items-center gap-1">Runner Name <span id="sortIcon_name" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('event')" class="py-3 px-2.5 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Event">
                <span class="inline-flex items-center gap-1">Event <span id="sortIcon_event" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('category')" class="py-3 px-2.5 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Category">
                <span class="inline-flex items-center gap-1">Category <span id="sortIcon_category" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('gender')" class="py-3 px-2 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Gender">
                <span class="inline-flex items-center gap-1">Gender <span id="sortIcon_gender" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('country')" class="py-3 px-2.5 font-semibold cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Country">
                <span class="inline-flex items-center gap-1">Country <span id="sortIcon_country" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('bruto')" class="py-3 px-2.5 font-semibold text-right cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Bruto Finish Time">
                <span class="inline-flex items-center justify-end gap-1 w-full">Bruto Time <span id="sortIcon_bruto" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('netto')" class="py-3 px-2.5 font-semibold text-right cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Netto Finish Time">
                <span class="inline-flex items-center justify-end gap-1 w-full">Netto Time <span id="sortIcon_netto" class="text-xs">↕</span></span>
              </th>
              <th onclick="setRunnerSort('pace')" class="py-3 px-2.5 font-semibold text-right cursor-pointer select-none hover:text-[var(--foreground)] transition whitespace-nowrap group" title="Click to sort by Average Pace">
                <span class="inline-flex items-center justify-end gap-1 w-full">Avg Pace <span id="sortIcon_pace" class="text-xs">↕</span></span>
              </th>
              <th class="py-3 px-3 font-semibold whitespace-nowrap">Checkpoint Splits</th>
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

    <!-- Double Category Runners (Day 1 + Day 2 Multi-Event Tracker) -->
    <div id="doubleRunnersSection" class="scroll-mt-20 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-[var(--border)]">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-bold text-[var(--foreground)]">Double Category Runners — Day 1 &amp; Day 2 Multi-Event Tracker</h2>
            <span id="doubleResultCountBadge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500"></span>
            <span id="doubleGenderSummaryBadge" class="inline-flex flex-wrap items-center gap-1.5 text-xs"></span>
          </div>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">
            Runners registered in both Day 1 (Half Marathon / 5K) and Day 2 (Marathon / 10K)
          </p>
        </div>
        <button
          id="resetDoubleFiltersBtn"
          class="self-start lg:self-auto px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition"
        >
          Reset Double Filters
        </button>
      </div>

      <!-- Double Combo Summary Cards -->
      <div id="doubleComboCards" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3"></div>

      <!-- Double Runner Search & Filter Controls -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div class="sm:col-span-2">
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Search Double Runner (Name, Bib No, Country)</label>
          <input
            id="doubleSearchInput"
            type="text"
            placeholder="Search by runner name, bib number, or country..."
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Race Combination</label>
          <select
            id="doubleComboSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Combinations</option>
            <option value="HM_FM">Day 1 HM + Day 2 Marathon (63.3K)</option>
            <option value="HM_10K">Day 1 HM + Day 2 10K (31.1K)</option>
            <option value="5K_FM">Day 1 5K + Day 2 Marathon (47.2K)</option>
            <option value="5K_10K">Day 1 5K + Day 2 10K (15.0K)</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Completion Status</label>
          <select
            id="doubleStatusSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Registered Double Runners</option>
            <option value="BOTH_FINISHED">Finished Both (Day 1 &amp; Day 2)</option>
            <option value="INCOMPLETE">Partial / DNS / DNF</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Gender</label>
          <select
            id="doubleGenderSelect"
            class="w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs focus:outline-none"
          >
            <option value="ALL">All Genders</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
      </div>

      <!-- Double Category Runners Comparison Table -->
      <div class="overflow-x-auto border border-[var(--border)] rounded-xl">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-[var(--background)] border-b border-[var(--border)] text-[var(--muted-foreground)]">
              <th class="py-3 px-2.5 font-semibold">#</th>
              <th class="py-3 px-3 font-semibold">Runner Name</th>
              <th class="py-3 px-2 font-semibold">Gender / Country</th>
              <th class="py-3 px-2.5 font-semibold">Combo</th>
              <th class="py-3 px-3 font-semibold border-l border-[var(--border)]">Day 1 Race (HM / 5K)</th>
              <th class="py-3 px-2.5 font-semibold text-right">Day 1 Bruto / Netto</th>
              <th class="py-3 px-3 font-semibold border-l border-[var(--border)]">Day 2 Race (FM / 10K)</th>
              <th class="py-3 px-2.5 font-semibold text-right">Day 2 Bruto / Netto</th>
              <th class="py-3 px-3 font-semibold text-right border-l border-[var(--border)]">Total Netto / Avg Pace</th>
            </tr>
          </thead>
          <tbody id="doubleTableBody" class="divide-y divide-[var(--border)]"></tbody>
        </table>
      </div>

      <!-- Double Table Pagination -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-1">
        <div id="doublePaginationInfo" class="text-xs text-[var(--muted-foreground)]"></div>
        <div class="flex items-center gap-2">
          <label class="text-xs text-[var(--muted-foreground)]">Rows:</label>
          <select
            id="doublePageSizeSelect"
            class="px-2 py-1 rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] text-xs"
          >
            <option value="10" selected>10</option>
            <option value="25">25</option>
            <option value="50">50</option>
          </select>
          <button
            id="doublePrevPageBtn"
            class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium disabled:opacity-40"
          >
            ← Prev
          </button>
          <span id="doublePageIndicator" class="text-xs font-semibold px-2"></span>
          <button
            id="doubleNextPageBtn"
            class="px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--background)] text-xs font-medium disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Footer Copyright -->
    <footer class="bg-[var(--card)] border border-[var(--border)] rounded-2xl px-6 py-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-[var(--muted-foreground)]">
      <div>
        Data from <a href="https://results.scorenow.co.id" target="_blank" rel="noopener noreferrer" class="font-semibold text-emerald-500 hover:underline">https://results.scorenow.co.id</a>
      </div>
      <div class="font-medium text-[var(--foreground)]">
        &copy; 2026 <a href="https://www.instagram.com/gbudidarma/" target="_blank" rel="noopener noreferrer" class="font-bold text-emerald-500 hover:underline">@gbudidarma</a> All rights reserved.
      </div>
    </footer>

  </div>

  <script>
    const THEME_PALETTES = {
      dark: {
        '--background': '#0b0f19',
        '--card': '#111827',
        '--foreground': '#f9fafb',
        '--muted-foreground': '#9ca3af',
        '--border': '#1f2937',
        '--primary': '#10b981',
        '--secondary': '#1e293b'
      },
      light: {
        '--background': '#f8fafc',
        '--card': '#ffffff',
        '--foreground': '#0f172a',
        '--muted-foreground': '#64748b',
        '--border': '#e2e8f0',
        '--primary': '#059669',
        '--secondary': '#f1f5f9'
      }
    };

    let currentTheme = 'dark';

    function setTheme(mode) {
      currentTheme = mode === 'light' ? 'light' : 'dark';
      const root = document.documentElement;
      const palette = THEME_PALETTES[currentTheme];
      Object.entries(palette).forEach(([k, v]) => {
        root.style.setProperty(k, v);
        document.body.style.setProperty(k, v);
      });
      root.style.colorScheme = currentTheme;
      try {
        localStorage.setItem('jrf2026_theme', currentTheme);
      } catch (e) {}
      updateThemeButtons();
    }

    function updateThemeButtons() {
      const lightBtn = document.getElementById('themeLightBtn');
      const darkBtn = document.getElementById('themeDarkBtn');
      if (!lightBtn || !darkBtn) return;
      if (currentTheme === 'light') {
        lightBtn.className = 'px-3 py-1 rounded-md text-xs font-semibold transition bg-emerald-600 text-white shadow-sm';
        darkBtn.className = 'px-3 py-1 rounded-md text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)]';
      } else {
        darkBtn.className = 'px-3 py-1 rounded-md text-xs font-semibold transition bg-emerald-600 text-white shadow-sm';
        lightBtn.className = 'px-3 py-1 rounded-md text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)]';
      }
    }

    (function initTheme() {
      let saved = null;
      try {
        saved = localStorage.getItem('jrf2026_theme');
      } catch (e) {}
      if (saved === 'light' || saved === 'dark') {
        setTheme(saved);
        return;
      }
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
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
    let runnerRemarkFilter = 'ALL';
    let runnerClassFilter = 'ALL';
    let runnerPage = 1;
    let runnerPageSize = 10;
    let filteredRunners = [];
    let activeBucketFilter = null;
    let runnerSortCol = 'pos';
    let runnerSortDir = 'asc';
    const RUNNER_SORT_COLS = ['pos', 'catRank', 'bib', 'name', 'event', 'category', 'gender', 'country', 'bruto', 'netto', 'pace'];

    // ===== Global Remark & Class Filter (KelasBersamaSIlaban.csv joined by BIB No) =====
    let globalRemark = 'ALL';
    let globalClass = 'ALL';
    let filteredAnalyticsCache = null;
    let filteredAnalyticsKey = '';

    function isGlobalFilterActive() {
      return globalRemark !== 'ALL' || globalClass !== 'ALL';
    }

    function runnerPassesGlobal(r) {
      if (globalRemark !== 'ALL' && r[16] !== globalRemark) return false;
      if (globalClass !== 'ALL' && r[17] !== globalClass) return false;
      return true;
    }

    function secToHms(s) {
      if (s === null || s === undefined || isNaN(s)) return '-';
      const t = Math.round(s);
      const p2 = n => String(n).padStart(2, '0');
      return `${p2(Math.floor(t / 3600))}:${p2(Math.floor((t % 3600) / 60))}:${p2(t % 60)}`;
    }

    function secToPaceStr(s) {
      if (s === null || s === undefined || isNaN(s)) return '-';
      const t = Math.round(s);
      return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')} /km`;
    }

    function meanOf(arr) {
      return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
    }

    function medianOf(arr) {
      if (!arr.length) return null;
      const s = arr.slice().sort((a, b) => a - b);
      const m = Math.floor(s.length / 2);
      return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    }

    function pctOf(n, total, digits) {
      return total ? Number((n * 100 / total).toFixed(digits)) : 0;
    }

    function computeFilteredAnalytics() {
      const origEvents = DASHBOARD_DATA.events;
      const allPaces = [];
      const counts = { total: 0, finished: 0, dnf: 0, cut: 0, dns: 0, other: 0 };

      const events = origEvents.map((evo, evIdx) => {
        const dist = evo.distance_km;
        const rows = DASHBOARD_DATA.runners.filter(r => r[0] === evIdx && runnerPassesGlobal(r));
        const total = rows.length;
        const st = { FINISHED: 0, DNF: 0, CUT: 0, DNS: 0, OTHER: 0 };
        rows.forEach(r => {
          if (st[r[2]] !== undefined) st[r[2]]++;
          else st.OTHER++;
        });
        const finRows = rows.filter(r => r[2] === 'FINISHED' && parseTimeSec(r[5]));
        const finSecs = finRows.map(r => parseTimeSec(r[5]));
        const nettoSecs = finRows.map(r => parseTimeSec(r[13])).filter(v => v !== null && v > 0);
        const maleSecs = finRows.filter(r => r[8] === 'Male').map(r => parseTimeSec(r[5]));
        const femaleSecs = finRows.filter(r => r[8] === 'Female').map(r => parseTimeSec(r[5]));
        finSecs.forEach(s => allPaces.push(s / dist));

        const avgSec = meanOf(finSecs);
        const medSec = medianOf(finSecs);
        const minSec = finSecs.length ? Math.min(...finSecs) : null;
        const avgN = meanOf(nettoSecs);
        const medN = medianOf(nettoSecs);
        const minN = nettoSecs.length ? Math.min(...nettoSecs) : null;

        const buckets = (evo.buckets || []).map(b => {
          const cnt = finSecs.filter(s => s >= b.min_sec && s <= b.max_sec).length;
          return Object.assign({}, b, { count: cnt, pct: pctOf(cnt, finSecs.length, 1) });
        });

        const groups = {};
        rows.forEach(r => {
          const cat = r[7], gen = r[8];
          if (!cat || cat === 'Unknown' || cat === 'PACER' || !gen || gen === 'Unknown') return;
          const key = cat + '||' + gen;
          if (!groups[key]) groups[key] = { all: [], fin: [] };
          groups[key].all.push(r);
          if (r[2] === 'FINISHED' && parseTimeSec(r[5])) groups[key].fin.push(r);
        });

        const categories = [];
        evo.categories.forEach(oc => {
          const g = groups[oc.category + '||' + oc.gender];
          if (!g || !g.fin.length) return;
          const sorted = g.fin.slice().sort((a, b) => parseTimeSec(a[5]) - parseTimeSec(b[5]));
          const gAvg = meanOf(sorted.map(r => parseTimeSec(r[5])));
          const podium = sorted.slice(0, 3).map((r, i) => {
            const rs = parseTimeSec(r[5]);
            return {
              category_rank: i + 1,
              overall_pos: r[1],
              bib_no: r[3],
              name: r[4],
              country: r[9] || '-',
              time: r[5],
              netto_time: r[13] || r[5],
              pace: secToPaceStr(rs / dist),
              netto_pace: r[14] ? `${r[14]} /km` : secToPaceStr(rs / dist)
            };
          });
          categories.push({
            category: oc.category,
            gender: oc.gender,
            total_entered: g.all.length,
            finishers_count: sorted.length,
            finish_pct: pctOf(sorted.length, g.all.length, 1),
            avg_time: secToHms(gAvg),
            avg_pace: secToPaceStr(gAvg / dist),
            winner: podium[0] || null,
            podium: podium
          });
        });

        counts.total += total;
        counts.finished += st.FINISHED;
        counts.dnf += st.DNF;
        counts.cut += st.CUT;
        counts.dns += st.DNS;
        counts.other += st.OTHER;

        return {
          event_slug: evo.event_slug,
          event_name: evo.event_name,
          race_day: evo.race_day,
          distance_km: dist,
          total: total,
          finished: st.FINISHED,
          finished_pct: pctOf(st.FINISHED, total, 2),
          dnf: st.DNF,
          dnf_pct: pctOf(st.DNF, total, 2),
          cut: st.CUT,
          cut_pct: pctOf(st.CUT, total, 2),
          dnf_plus_cut: st.DNF + st.CUT,
          dnf_plus_cut_pct: pctOf(st.DNF + st.CUT, total, 2),
          dns: st.DNS,
          dns_pct: pctOf(st.DNS, total, 2),
          other: st.OTHER,
          other_pct: pctOf(st.OTHER, total, 2),
          avg_time: secToHms(avgSec),
          median_time: secToHms(medSec),
          best_time: secToHms(minSec),
          avg_netto_time: secToHms(avgN),
          median_netto_time: secToHms(medN),
          best_netto_time: secToHms(minN),
          avg_pace: secToPaceStr(avgSec === null ? null : avgSec / dist),
          median_pace: secToPaceStr(medSec === null ? null : medSec / dist),
          best_pace: secToPaceStr(minSec === null ? null : minSec / dist),
          male_avg_pace: secToPaceStr(maleSecs.length ? meanOf(maleSecs) / dist : null),
          female_avg_pace: secToPaceStr(femaleSecs.length ? meanOf(femaleSecs) / dist : null),
          male_finishers: maleSecs.length,
          female_finishers: femaleSecs.length,
          cot_label: evo.cot_label,
          step_label: evo.step_label,
          buckets: buckets,
          categories: categories
        };
      });

      const overall = {
        total: counts.total,
        finished: counts.finished,
        finished_pct: pctOf(counts.finished, counts.total, 2),
        dnf: counts.dnf,
        dnf_pct: pctOf(counts.dnf, counts.total, 2),
        cut: counts.cut,
        cut_pct: pctOf(counts.cut, counts.total, 2),
        dnf_plus_cut: counts.dnf + counts.cut,
        dnf_plus_cut_pct: pctOf(counts.dnf + counts.cut, counts.total, 2),
        dns: counts.dns,
        dns_pct: pctOf(counts.dns, counts.total, 2),
        other: counts.other,
        other_pct: pctOf(counts.other, counts.total, 2),
        avg_pace: secToPaceStr(meanOf(allPaces)),
        median_pace: secToPaceStr(medianOf(allPaces))
      };
      return { overall, events };
    }

    function getAnalytics() {
      if (!isGlobalFilterActive()) {
        return { overall: DASHBOARD_DATA.overall, events: DASHBOARD_DATA.events };
      }
      const key = globalRemark + '|' + globalClass;
      if (!filteredAnalyticsCache || filteredAnalyticsKey !== key) {
        filteredAnalyticsCache = computeFilteredAnalytics();
        filteredAnalyticsKey = key;
      }
      return filteredAnalyticsCache;
    }

    function getDoubleSummary() {
      if (!isGlobalFilterActive()) return DASHBOARD_DATA.double_summary;
      const blank = () => ({ reg: 0, reg_m: 0, reg_f: 0, fin_both: 0, fin_m: 0, fin_f: 0 });
      const sum = { ALL: blank(), HM_FM: blank(), HM_10K: blank(), '5K_FM': blank(), '5K_10K': blank() };
      (DASHBOARD_DATA.double_pairs || []).forEach(p => {
        const r1 = DASHBOARD_DATA.runners[p[0]];
        const r2 = DASHBOARD_DATA.runners[p[1]];
        if (!runnerPassesGlobal(r1) && !runnerPassesGlobal(r2)) return;
        const combo = p[2];
        [sum.ALL, sum[combo]].forEach(s => {
          if (!s) return;
          s.reg++;
          if (r1[8] === 'Male') s.reg_m++;
          else if (r1[8] === 'Female') s.reg_f++;
          if (p[3] === 1) {
            s.fin_both++;
            if (r1[8] === 'Male') s.fin_m++;
            else if (r1[8] === 'Female') s.fin_f++;
          }
        });
      });
      return sum;
    }

    function classBadgeHtml(r) {
      if (!r || !r[17]) return '';
      return `<span class="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/30 text-xs font-semibold" title="${escapeHtml(r[16] || '')}">${escapeHtml(r[17])}</span>`;
    }

    function renderGlobalFilterBar() {
      const meta = DASHBOARD_DATA.silaban_meta || { total: 0, remarks: [], classes: [] };
      const tabs = document.getElementById('globalRemarkTabs');
      const select = document.getElementById('globalClassSelect');
      const badge = document.getElementById('globalFilterActiveBadge');
      const resetBtn = document.getElementById('resetGlobalFilterBtn');
      if (!tabs || !select) return;

      const baseCls = 'px-3 py-1.5 rounded-xl text-xs font-semibold transition border ';
      const activeCls = 'bg-emerald-600 text-white border-emerald-600 shadow-sm';
      const idleCls = 'bg-[var(--background)] text-[var(--foreground)] border-[var(--border)] hover:border-emerald-500/50';
      tabs.innerHTML =
        `<button onclick="selectGlobalRemark('ALL')" class="${baseCls}${globalRemark === 'ALL' ? activeCls : idleCls}">All Runners</button>` +
        meta.remarks.map((rm, i) =>
          `<button onclick="selectGlobalRemarkByIdx(${i})" class="${baseCls}${globalRemark === rm.name ? activeCls : idleCls}">${escapeHtml(rm.name)} (${fmtNum(rm.count)})</button>`
        ).join('');

      select.innerHTML = `<option value="ALL">All Classes</option>` +
        meta.classes.map(c => `<option value="${escapeHtml(c.code)}">${escapeHtml(c.code)} (${fmtNum(c.count)})</option>`).join('');
      select.value = globalClass;

      const active = isGlobalFilterActive();
      resetBtn.classList.toggle('hidden', !active);
      if (active) {
        const a = getAnalytics();
        const parts = [];
        if (globalRemark !== 'ALL') parts.push(globalRemark);
        if (globalClass !== 'ALL') parts.push(`Class ${globalClass}`);
        badge.classList.remove('hidden');
        badge.textContent = `Filter active: ${parts.join(' • ')} — ${fmtNum(a.overall.total)} runners (${fmtNum(a.overall.finished)} finished) applied to the whole dashboard`;
      } else {
        badge.classList.add('hidden');
        badge.textContent = '';
      }
    }

    function refreshRunnerEventOptions() {
      const sel = document.getElementById('runnerEventSelect');
      if (!sel) return;
      const prev = sel.value;
      const a = getAnalytics();
      sel.innerHTML = `<option value="ALL">All 4 Events (${fmtNum(a.overall.total)})</option>` +
        DASHBOARD_DATA.event_lookup.map((ev, idx) =>
          `<option value="${idx}">${ev.name} (${ev.dist}K) — ${fmtNum(a.events[idx].total)}</option>`
        ).join('');
      sel.value = prev;
    }

    function applyGlobalFilter() {
      filteredAnalyticsCache = null;
      activeBucketFilter = null;
      updateBucketFilterBadge();
      renderGlobalFilterBar();
      refreshRunnerEventOptions();
      document.getElementById('runnerDetailDrawer').classList.add('hidden');
      renderAll();
      filterRunnersList();
      filterDoubleRunnersList();
    }

    function selectGlobalRemark(name) {
      globalRemark = name;
      if (name === 'ALL') globalClass = 'ALL';
      applyGlobalFilter();
    }

    function selectGlobalRemarkByIdx(i) {
      const rm = (DASHBOARD_DATA.silaban_meta.remarks || [])[i];
      if (!rm) return;
      globalRemark = globalRemark === rm.name ? 'ALL' : rm.name;
      if (globalRemark === 'ALL') globalClass = 'ALL';
      applyGlobalFilter();
    }

    function selectGlobalClass(code) {
      globalClass = globalClass === code ? 'ALL' : code;
      applyGlobalFilter();
    }

    function resetGlobalFilter() {
      globalRemark = 'ALL';
      globalClass = 'ALL';
      applyGlobalFilter();
    }

    function parseTimeSec(t) {
      if (!t) return null;
      const p = String(t).trim().split(':').map(Number);
      if (p.length === 3 && p.every(n => !isNaN(n))) return p[0] * 3600 + p[1] * 60 + p[2];
      if (p.length === 2 && p.every(n => !isNaN(n))) return p[0] * 60 + p[1];
      return null;
    }

    function updateBucketFilterBadge() {
      const badge = document.getElementById('activeBucketFilterBadge');
      if (!badge) return;
      if (!activeBucketFilter) {
        badge.classList.add('hidden');
        badge.innerHTML = '';
        return;
      }
      badge.classList.remove('hidden');
      badge.innerHTML = `
        <span>Finish Range: ${escapeHtml(activeBucketFilter.label)}</span>
        <button onclick="clearBucketFilter()" class="hover:opacity-75 font-bold" title="Clear Finish Time Range Filter">✕</button>
      `;
    }

    function selectBucketFilter(bucketIdx) {
      const { isAll, stats } = getActiveContext();
      if (isAll || !stats || !stats.buckets || !stats.buckets[bucketIdx]) return;
      const b = stats.buckets[bucketIdx];

      if (
        activeBucketFilter &&
        activeBucketFilter.eventSlug === stats.event_slug &&
        activeBucketFilter.bucketIdx === bucketIdx
      ) {
        clearBucketFilter();
        return;
      }

      const evIdx = DASHBOARD_DATA.event_lookup.findIndex(e => e.slug === stats.event_slug);
      activeBucketFilter = {
        eventSlug: stats.event_slug,
        eventIdx: evIdx,
        bucketIdx: bucketIdx,
        label: b.label,
        minSec: b.min_sec,
        maxSec: b.max_sec
      };
      if (evIdx >= 0) {
        runnerEventFilter = String(evIdx);
        document.getElementById('runnerEventSelect').value = runnerEventFilter;
      }
      runnerStatusFilter = 'FINISHED';
      document.getElementById('runnerStatusSelect').value = 'FINISHED';
      updateBucketFilterBadge();
      renderStatusAndRightPanel();
      filterRunnersList();
      document.getElementById('runnerTableSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function clearBucketFilter() {
      activeBucketFilter = null;
      updateBucketFilterBadge();
      renderStatusAndRightPanel();
      filterRunnersList();
    }

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
      const a = getAnalytics();
      if (selectedEventSlug === 'ALL') {
        return { isAll: true, stats: a.overall, events: a.events };
      }
      const ev = a.events.find(e => e.event_slug === selectedEventSlug);
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

      const sMeta = DASHBOARD_DATA.silaban_meta || { remarks: [], classes: [] };
      document.getElementById('runnerRemarkSelect').innerHTML = `<option value="ALL">All Remarks</option>` +
        sMeta.remarks.map(rm => `<option value="${escapeHtml(rm.name)}">${escapeHtml(rm.name)} (${fmtNum(rm.count)})</option>`).join('');
      document.getElementById('runnerClassSelect').innerHTML = `<option value="ALL">All Classes</option>` +
        sMeta.classes.map(c => `<option value="${escapeHtml(c.code)}">${escapeHtml(c.code)} (${fmtNum(c.count)})</option>`).join('');
    }

    function catRankBadgeHtml(catRank) {
      if (!catRank) return '<span class="text-[var(--muted-foreground)]">—</span>';
      if (catRank <= 3) {
        const medal = catRank === 1 ? '🥇 ' : catRank === 2 ? '🥈 ' : '🥉 ';
        return `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 font-bold">${medal}#${fmtNum(catRank)}</span>`;
      }
      return `<span class="font-mono text-xs text-sky-500 font-semibold">#${fmtNum(catRank)}</span>`;
    }

    function updateRunnerSortIcons() {
      RUNNER_SORT_COLS.forEach(col => {
        const icon = document.getElementById('sortIcon_' + col);
        if (!icon) return;
        if (runnerSortCol === col) {
          icon.textContent = runnerSortDir === 'asc' ? '▲' : '▼';
          icon.className = 'text-xs text-emerald-500 font-bold';
        } else {
          icon.textContent = '↕';
          icon.className = 'text-xs opacity-30 group-hover:opacity-75';
        }
      });
    }

    function sortRunnersList() {
      if (!runnerSortCol) return;
      const dir = runnerSortDir === 'desc' ? -1 : 1;

      filteredRunners.sort((a, b) => {
        switch (runnerSortCol) {
          case 'pos': {
            const isFinA = a[2] === 'FINISHED' && a[1] !== null;
            const isFinB = b[2] === 'FINISHED' && b[1] !== null;
            if (isFinA && isFinB) return (a[1] - b[1]) * dir;
            if (isFinA && !isFinB) return -1;
            if (!isFinA && isFinB) return 1;
            const sComp = (a[2] || '').localeCompare(b[2] || '');
            if (sComp !== 0) return sComp * dir;
            return (a[3] || '').localeCompare(b[3] || '', undefined, { numeric: true }) * dir;
          }
          case 'catRank': {
            const hasRkA = a[12] !== null && a[12] !== undefined && a[12] > 0;
            const hasRkB = b[12] !== null && b[12] !== undefined && b[12] > 0;
            if (hasRkA && hasRkB) return (a[12] - b[12]) * dir;
            if (hasRkA && !hasRkB) return -1;
            if (!hasRkA && hasRkB) return 1;
            return ((a[1] || 9999999) - (b[1] || 9999999)) * dir;
          }
          case 'bib':
            return (a[3] || '').localeCompare(b[3] || '', undefined, { numeric: true, sensitivity: 'base' }) * dir;
          case 'name': {
            const hasA = Boolean(a[4] && a[4].trim());
            const hasB = Boolean(b[4] && b[4].trim());
            if (hasA && hasB) return a[4].trim().localeCompare(b[4].trim()) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return 0;
          }
          case 'event': {
            const evA = DASHBOARD_DATA.event_lookup[a[0]] ? DASHBOARD_DATA.event_lookup[a[0]].name : '';
            const evB = DASHBOARD_DATA.event_lookup[b[0]] ? DASHBOARD_DATA.event_lookup[b[0]].name : '';
            const c = evA.localeCompare(evB);
            if (c !== 0) return c * dir;
            return ((a[1] || 9999999) - (b[1] || 9999999)) * dir;
          }
          case 'category': {
            const hasA = Boolean(a[7] && a[7] !== 'Unknown');
            const hasB = Boolean(b[7] && b[7] !== 'Unknown');
            if (hasA && hasB) return a[7].localeCompare(b[7]) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return 0;
          }
          case 'gender':
            return (a[8] || '').localeCompare(b[8] || '') * dir;
          case 'country': {
            const hasA = Boolean(a[9] && a[9] !== '-' && a[9] !== 'Unknown');
            const hasB = Boolean(b[9] && b[9] !== '-' && b[9] !== 'Unknown');
            if (hasA && hasB) return a[9].localeCompare(b[9]) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return 0;
          }
          case 'bruto': {
            const secA = parseTimeSec(a[5]);
            const secB = parseTimeSec(b[5]);
            const hasA = secA !== null && a[2] === 'FINISHED';
            const hasB = secB !== null && b[2] === 'FINISHED';
            if (hasA && hasB) return (secA - secB) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return (a[3] || '').localeCompare(b[3] || '', undefined, { numeric: true }) * dir;
          }
          case 'netto': {
            const secA = parseTimeSec(a[13]) || parseTimeSec(a[5]);
            const secB = parseTimeSec(b[13]) || parseTimeSec(b[5]);
            const hasA = secA !== null && a[2] === 'FINISHED';
            const hasB = secB !== null && b[2] === 'FINISHED';
            if (hasA && hasB) return (secA - secB) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return (a[3] || '').localeCompare(b[3] || '', undefined, { numeric: true }) * dir;
          }
          case 'pace': {
            const pStrA = a[14] || a[6] || '';
            const pStrB = b[14] || b[6] || '';
            const secA = parseTimeSec(pStrA);
            const secB = parseTimeSec(pStrB);
            const hasA = secA !== null && a[2] === 'FINISHED';
            const hasB = secB !== null && b[2] === 'FINISHED';
            if (hasA && hasB) return (secA - secB) * dir;
            if (hasA && !hasB) return -1;
            if (!hasA && hasB) return 1;
            return (a[3] || '').localeCompare(b[3] || '', undefined, { numeric: true }) * dir;
          }
          default:
            return 0;
        }
      });
    }

    function setRunnerSort(col) {
      if (runnerSortCol === col) {
        runnerSortDir = runnerSortDir === 'asc' ? 'desc' : 'asc';
      } else {
        runnerSortCol = col;
        runnerSortDir = 'asc';
      }
      sortRunnersList();
      runnerPage = 1;
      updateRunnerSortIcons();
      renderRunnerTable();
    }

    function filterRunnersList() {
      const q = runnerQuery.trim().toLowerCase();
      const evIdx = runnerEventFilter === 'ALL' ? null : Number(runnerEventFilter);

      filteredRunners = DASHBOARD_DATA.runners.filter(r => {
        if (!runnerPassesGlobal(r)) return false;
        if (evIdx !== null && r[0] !== evIdx) return false;
        if (runnerCategoryFilter !== 'ALL' && r[7] !== runnerCategoryFilter) return false;
        if (runnerGenderFilter !== 'ALL' && r[8] !== runnerGenderFilter) return false;
        if (runnerStatusFilter !== 'ALL' && r[2] !== runnerStatusFilter) return false;
        if (runnerRemarkFilter !== 'ALL' && r[16] !== runnerRemarkFilter) return false;
        if (runnerClassFilter !== 'ALL' && r[17] !== runnerClassFilter) return false;
        if (activeBucketFilter) {
          if (r[2] !== 'FINISHED') return false;
          if (activeBucketFilter.eventIdx >= 0 && r[0] !== activeBucketFilter.eventIdx) return false;
          const bSec = parseTimeSec(r[5]);
          if (bSec === null || bSec < activeBucketFilter.minSec || bSec > activeBucketFilter.maxSec) return false;
        }
        if (q) {
          const bib = (r[3] || '').toLowerCase();
          const name = (r[4] || '').toLowerCase();
          const country = (r[9] || '').toLowerCase();
          if (!bib.includes(q) && !name.includes(q) && !country.includes(q)) return false;
        }
        return true;
      });

      sortRunnersList();
      runnerPage = 1;
      updateRunnerSortIcons();
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

      let partnerBannerHtml = '';
      if (r[15] !== undefined && r[15] >= 0) {
        const pr = DASHBOARD_DATA.runners[r[15]];
        if (pr) {
          const pev = DASHBOARD_DATA.event_lookup[pr[0]];
          partnerBannerHtml = `
            <div class="p-3 rounded-xl bg-[var(--card)] border border-emerald-500/30 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div class="flex flex-wrap items-center gap-2">
                <span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-500 font-bold">Double Category Runner (${escapeHtml(pev.day)})</span>
                <span class="font-semibold text-[var(--foreground)]">${escapeHtml(pev.name)} (${pev.dist} KM)</span>
                <span class="text-[var(--muted-foreground)]">• Bib: <strong class="font-mono text-[var(--foreground)]">${escapeHtml(pr[3])}</strong> • Name: <strong>${escapeHtml(pr[4])}</strong></span>
              </div>
              <div class="flex items-center gap-3">
                ${statusBadgeHtml(pr[1], pr[2])}
                <span class="font-mono text-[var(--muted-foreground)]">Bruto: <strong class="text-[var(--foreground)]">${escapeHtml(pr[5] || '—')}</strong></span>
                <span class="font-mono text-emerald-500">Netto: <strong>${escapeHtml(pr[13] || '—')}</strong></span>
              </div>
            </div>
          `;
        }
      }

      drawer.innerHTML = `
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              ${statusBadgeHtml(r[1], r[2])}
              ${r[12] ? `<span class="px-2 py-0.5 rounded bg-sky-500/10 text-sky-500 border border-sky-500/30 font-mono text-xs font-semibold">Cat Rank #${fmtNum(r[12])}</span>` : ''}
              <span class="text-base font-bold text-[var(--foreground)]">${escapeHtml(r[4] || '(No Name)')}</span>
              ${r[16] ? `<span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/30 text-xs font-semibold">${escapeHtml(r[16])}${r[17] ? ' • ' + escapeHtml(r[17]) : ''}</span>` : ''}
              ${r[15] >= 0 ? `<span class="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 text-xs font-semibold">Double (Day 1+2)</span>` : ''}
              <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-xs text-[var(--muted-foreground)]">Bib: ${escapeHtml(r[3])}</span>
            </div>
            <div class="text-xs text-[var(--muted-foreground)] mt-1">
              <strong>${escapeHtml(ev.name)}</strong> (${ev.dist} KM • ${escapeHtml(ev.day)}) • Category: <strong>${escapeHtml(r[7])}</strong> • Gender: <strong>${escapeHtml(r[8])}</strong> • Country: <strong>${escapeHtml(r[9])}</strong>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-4">
            <div class="text-right px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)]">
              <div class="text-xs text-[var(--muted-foreground)]">Bruto Finish Time</div>
              <div class="text-sm font-mono font-bold text-[var(--foreground)]">${escapeHtml(r[5] || '—')} ${r[6] ? `<span class="text-xs font-normal text-[var(--muted-foreground)]">(${escapeHtml(r[6])} /km)</span>` : ''}</div>
            </div>
            <div class="text-right px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
              <div class="text-xs text-emerald-500 font-medium">Netto Finish Time (Splits)</div>
              <div class="text-sm font-mono font-bold text-emerald-500">${escapeHtml(r[13] || '—')} ${r[14] ? `<span class="text-xs font-normal text-sky-500">(${escapeHtml(r[14])} /km)</span>` : ''}</div>
            </div>
            <button
              onclick="document.getElementById('runnerDetailDrawer').classList.add('hidden')"
              class="px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--card)] text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              ✕ Close
            </button>
          </div>
        </div>
        ${partnerBannerHtml}
        <div>
          <div class="text-xs font-semibold text-[var(--muted-foreground)] mb-2">Checkpoint Split Times (Segment Intervals • Sum = Netto Finish Time: <span class="font-mono text-emerald-500">${escapeHtml(r[13] || '—')}</span>)</div>
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
            <td colspan="12" class="py-8 text-center text-sm text-[var(--muted-foreground)]">
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
            <td class="py-2.5 px-3 font-semibold text-[var(--foreground)]">
              <div class="flex flex-wrap items-center gap-1.5">
                <span>${escapeHtml(r[4] || '—')}</span>
                ${classBadgeHtml(r)}
                ${r[15] >= 0 ? `<span class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 text-xs font-medium">Double</span>` : ''}
              </div>
            </td>
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
            <td class="py-2.5 px-2.5 text-right font-mono font-semibold text-[var(--foreground)] whitespace-nowrap">${escapeHtml(r[5] || '—')}</td>
            <td class="py-2.5 px-2.5 text-right font-mono font-bold text-emerald-500 whitespace-nowrap">${escapeHtml(r[13] || '—')}</td>
            <td class="py-2.5 px-2.5 text-right font-mono text-sky-500 whitespace-nowrap">${r[14] ? `${escapeHtml(r[14])} /km` : '—'}</td>
            <td class="py-2.5 px-3"><div class="flex flex-wrap gap-1">${splitsPreview}</div></td>
          </tr>
        `;
      }).join('');
    }

    function renderTabs() {
      const container = document.getElementById('eventTabs');
      const a = getAnalytics();
      const filtered = isGlobalFilterActive();
      const tabs = [
        { slug: 'ALL', label: `All Events (${fmtNum(a.overall.total)})` },
        ...a.events.map(e => ({
          slug: e.event_slug,
          label: `${e.event_name} (${e.distance_km}K)${filtered ? ' · ' + fmtNum(e.total) : ''}`
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
          badge: isAll ? `Across all ${fmtNum(stats.finished)} finishers` : `${stats.distance_km} KM Distance`,
          color: 'text-sky-500',
          barColor: 'bg-sky-500',
          pct: 100
        },
        {
          title: isAll ? 'Total Finishers' : 'Avg Finish Time (Bruto / Netto)',
          value: isAll ? fmtNum(stats.finished) : stats.avg_time,
          sub: isAll ? `Across 4 Race Events (Day 1 & Day 2)` : `Netto Avg: ${stats.avg_netto_time} • Best: ${stats.best_netto_time}`,
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
                  <th class="py-2.5 px-2 font-semibold text-right">Avg Bruto</th>
                  <th class="py-2.5 px-2 font-semibold text-right text-emerald-500">Avg Netto</th>
                  <th class="py-2.5 pl-2 font-semibold text-right text-sky-500">Avg Pace</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border)] text-xs">
                ${getAnalytics().events.map(ev => `
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
                    <td class="py-3 px-2 text-right font-mono font-medium text-[var(--foreground)]">${ev.avg_time}</td>
                    <td class="py-3 px-2 text-right font-mono font-bold text-emerald-500">${ev.avg_netto_time}</td>
                    <td class="py-3 pl-2 text-right font-mono font-semibold text-sky-500">${ev.avg_pace}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else {
        rightTitle.textContent = `${stats.event_name} — Finish Time & Pace Distribution`;
        rightSubtitle.textContent = `COT: ${stats.cot_label} (${stats.step_label}) • Click any bar to filter runners in that finish time range`;
        const maxBucket = Math.max(...stats.buckets.map(b => b.count), 1);
        const hasActiveBar = activeBucketFilter && activeBucketFilter.eventSlug === stats.event_slug;
        rightContent.innerHTML = `
          ${hasActiveBar ? `
            <div class="flex items-center justify-between px-3 py-1.5 mb-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs">
              <span class="font-medium text-emerald-500">Active Filter: <strong>${escapeHtml(activeBucketFilter.label)}</strong></span>
              <button onclick="clearBucketFilter()" class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] font-medium hover:opacity-80">Clear Filter ✕</button>
            </div>
          ` : ''}
          <div class="space-y-1.5">
            ${stats.buckets.map((b, bIdx) => {
              const isSelected = hasActiveBar && activeBucketFilter.bucketIdx === bIdx;
              const rowCls = isSelected
                ? 'bg-emerald-500/15 ring-1 ring-emerald-500 rounded-lg px-2 py-1'
                : 'hover:bg-[var(--background)] rounded-lg px-2 py-1';
              const barColor = b.is_over_cot
                ? (isSelected ? 'bg-amber-500' : 'bg-amber-500/80')
                : (isSelected ? 'bg-emerald-500' : 'bg-emerald-500/80');
              const labelColor = b.is_over_cot ? 'text-amber-500 font-semibold' : 'text-[var(--foreground)] font-medium';
              return `
                <div
                  onclick="selectBucketFilter(${bIdx})"
                  class="grid grid-cols-12 items-center gap-2 text-xs cursor-pointer transition select-none ${rowCls}"
                  title="Click to filter runners in ${b.label} (${b.pace_label}): ${fmtNum(b.count)} runners (${b.pct}%)"
                >
                  <div class="col-span-3 font-mono ${labelColor}">${escapeHtml(b.label)}</div>
                  <div class="col-span-6">
                    <div class="w-full h-4 bg-[var(--background)] rounded-lg overflow-hidden border border-[var(--border)]">
                      <div class="h-full ${barColor} rounded-lg transition-all" style="width: ${b.count > 0 ? Math.max(2, (b.count / maxBucket) * 100) : 0}%"></div>
                    </div>
                  </div>
                  <div class="col-span-3 text-right">
                    <span class="font-semibold text-[var(--foreground)]">${fmtNum(b.count)}</span>
                    <span class="text-[var(--muted-foreground)] ml-1">(${b.pct}%)</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }
    }

    let collapsedWinnerEvents = new Set(DASHBOARD_DATA.events.map(e => e.event_slug));

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
                      <th class="py-2.5 px-2 font-semibold text-right">Bruto Time</th>
                      <th class="py-2.5 px-2 font-semibold text-right">Netto Time</th>
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
                          <td class="py-2.5 px-2 text-right font-mono font-semibold text-[var(--foreground)]">${w ? w.time : '-'}</td>
                          <td class="py-2.5 px-2 text-right font-mono font-bold text-emerald-500">${w ? w.netto_time : '-'}</td>
                          <td class="py-2.5 px-2 text-right font-mono text-sky-500">${w ? w.netto_pace : '-'}</td>
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
                          <div class="text-right shrink-0 space-y-0.5">
                            <div class="font-mono text-xs text-[var(--muted-foreground)]">Bruto: <span class="font-semibold text-[var(--foreground)]">${p.time}</span></div>
                            <div class="font-mono text-xs text-emerald-500">Netto: <span class="font-bold">${p.netto_time}</span></div>
                            <div class="font-mono text-xs text-sky-500">${p.netto_pace}</div>
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
      activeBucketFilter = null;
      updateBucketFilterBadge();
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
      const rows = (evIdx === null
        ? DASHBOARD_DATA.runners
        : DASHBOARD_DATA.runners.filter(r => r[0] === evIdx)
      ).filter(runnerPassesGlobal);

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

    // Double Category Runners State
    let doubleQuery = '';
    let doubleComboFilter = 'ALL';
    let doubleStatusFilter = 'ALL';
    let doubleGenderFilter = 'ALL';
    let doublePage = 1;
    let doublePageSize = 10;
    let filteredDoublePairs = [];

    const DOUBLE_COMBO_META = {
      ALL: { title: 'All Double Runners', sub: 'Day 1 + Day 2 Registered', badge: 'All Combos', dist: '' },
      HM_FM: { title: 'HM + Marathon', sub: '21.1K (Day 1) + 42.2K (Day 2)', badge: '63.3 KM', dist: '63.3 KM' },
      HM_10K: { title: 'HM + 10K', sub: '21.1K (Day 1) + 10K (Day 2)', badge: '31.1 KM', dist: '31.1 KM' },
      '5K_FM': { title: '5K + Marathon', sub: '5K (Day 1) + 42.2K (Day 2)', badge: '47.2 KM', dist: '47.2 KM' },
      '5K_10K': { title: '5K + 10K', sub: '5K (Day 1) + 10K (Day 2)', badge: '15.0 KM', dist: '15.0 KM' }
    };

    function selectDoubleCombo(comboCode) {
      doubleComboFilter = comboCode;
      document.getElementById('doubleComboSelect').value = comboCode;
      renderDoubleComboCards();
      filterDoubleRunnersList();
    }

    function renderDoubleComboCards() {
      const container = document.getElementById('doubleComboCards');
      if (!container || !DASHBOARD_DATA.double_summary) return;
      const keys = ['ALL', 'HM_FM', 'HM_10K', '5K_FM', '5K_10K'];
      container.innerHTML = keys.map(k => {
        const st = getDoubleSummary()[k] || { reg: 0, reg_m: 0, reg_f: 0, fin_both: 0, fin_m: 0, fin_f: 0 };
        const meta = DOUBLE_COMBO_META[k];
        const active = doubleComboFilter === k;
        const pct = st.reg ? ((st.fin_both * 100) / st.reg).toFixed(1) : '0.0';
        const finM = st.fin_m || 0;
        const finF = st.fin_f || 0;
        const regM = st.reg_m || 0;
        const regF = st.reg_f || 0;
        const mPct = regM ? ((finM * 100) / regM).toFixed(1) : '0.0';
        const fPct = regF ? ((finF * 100) / regF).toFixed(1) : '0.0';
        return `
          <div
            onclick="selectDoubleCombo('${k}')"
            class="p-3.5 rounded-xl border cursor-pointer transition select-none flex flex-col justify-between ${
              active
                ? 'bg-emerald-500/10 border-emerald-500 ring-1 ring-emerald-500'
                : 'bg-[var(--background)] border-[var(--border)] hover:border-emerald-500/50'
            }"
          >
            <div>
              <div class="flex items-center justify-between gap-1.5">
                <span class="text-xs font-bold text-[var(--foreground)]">${meta.title}</span>
                <span class="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-[var(--card)] border border-[var(--border)] text-emerald-500">${meta.badge}</span>
              </div>
              <div class="text-xs text-[var(--muted-foreground)] mt-0.5">${meta.sub}</div>
            </div>
            <div class="mt-3 pt-2 border-t border-[var(--border)] space-y-2">
              <div class="flex items-baseline justify-between gap-2">
                <div>
                  <span class="text-lg font-bold text-[var(--foreground)]">${fmtNum(st.reg)}</span>
                  <span class="text-xs text-[var(--muted-foreground)] ml-1">runners</span>
                </div>
                <div class="text-xs text-emerald-500 font-semibold text-right">
                  ${fmtNum(st.fin_both)} finished both (${pct}%)
                </div>
              </div>
              <div class="grid grid-cols-2 gap-1.5 pt-2 border-t border-[var(--border)] text-xs">
                <div class="px-2 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20">
                  <div class="text-[var(--muted-foreground)] font-medium">Male Finished</div>
                  <div class="font-mono font-bold text-sky-500 mt-0.5">${fmtNum(finM)} <span class="font-normal text-[var(--muted-foreground)]">/ ${fmtNum(regM)} (${mPct}%)</span></div>
                </div>
                <div class="px-2 py-1.5 rounded-lg bg-pink-500/10 border border-pink-500/20">
                  <div class="text-[var(--muted-foreground)] font-medium">Female Finished</div>
                  <div class="font-mono font-bold text-pink-500 mt-0.5">${fmtNum(finF)} <span class="font-normal text-[var(--muted-foreground)]">/ ${fmtNum(regF)} (${fPct}%)</span></div>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function filterDoubleRunnersList() {
      const q = doubleQuery.trim().toLowerCase();
      const pairs = DASHBOARD_DATA.double_pairs || [];

      filteredDoublePairs = pairs.filter(p => {
        const r1 = DASHBOARD_DATA.runners[p[0]];
        const r2 = DASHBOARD_DATA.runners[p[1]];
        const combo = p[2];
        const bothFin = p[3] === 1;

        if (!runnerPassesGlobal(r1) && !runnerPassesGlobal(r2)) return false;
        if (doubleComboFilter !== 'ALL' && combo !== doubleComboFilter) return false;
        if (doubleStatusFilter === 'BOTH_FINISHED' && !bothFin) return false;
        if (doubleStatusFilter === 'INCOMPLETE' && bothFin) return false;
        if (doubleGenderFilter !== 'ALL' && r1[8] !== doubleGenderFilter) return false;

        if (q) {
          const n1 = (r1[4] || '').toLowerCase();
          const n2 = (r2[4] || '').toLowerCase();
          const b1 = (r1[3] || '').toLowerCase();
          const b2 = (r2[3] || '').toLowerCase();
          const ctry = (r1[9] || '').toLowerCase();
          if (!n1.includes(q) && !n2.includes(q) && !b1.includes(q) && !b2.includes(q) && !ctry.includes(q)) {
            return false;
          }
        }
        return true;
      });

      doublePage = 1;
      renderDoubleTable();
    }

    function inspectDoubleRunnerInMainTable(bibNo) {
      runnerQuery = bibNo;
      runnerEventFilter = 'ALL';
      runnerCategoryFilter = 'ALL';
      runnerGenderFilter = 'ALL';
      runnerStatusFilter = 'ALL';
      runnerRemarkFilter = 'ALL';
      runnerClassFilter = 'ALL';
      runnerSortCol = 'pos';
      runnerSortDir = 'asc';
      activeBucketFilter = null;
      updateBucketFilterBadge();
      document.getElementById('runnerSearchInput').value = bibNo;
      document.getElementById('runnerEventSelect').value = 'ALL';
      document.getElementById('runnerCategorySelect').value = 'ALL';
      document.getElementById('runnerGenderSelect').value = 'ALL';
      document.getElementById('runnerStatusSelect').value = 'ALL';
      document.getElementById('runnerRemarkSelect').value = 'ALL';
      document.getElementById('runnerClassSelect').value = 'ALL';
      filterRunnersList();
      if (filteredRunners.length > 0) {
        showRunnerDetail(0);
      }
      document.getElementById('runnerTableSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderDoubleTable() {
      const total = filteredDoublePairs.length;
      const totalPages = Math.max(1, Math.ceil(total / doublePageSize));
      if (doublePage > totalPages) doublePage = totalPages;

      const startIdx = (doublePage - 1) * doublePageSize;
      const endIdx = Math.min(startIdx + doublePageSize, total);
      const pageSlice = filteredDoublePairs.slice(startIdx, endIdx);

      let finBothCount = 0, finMaleCount = 0, finFemaleCount = 0;
      filteredDoublePairs.forEach(p => {
        if (p[3] === 1) {
          finBothCount++;
          const g = DASHBOARD_DATA.runners[p[0]][8];
          if (g === 'Male') finMaleCount++;
          else if (g === 'Female') finFemaleCount++;
        }
      });

      document.getElementById('doubleResultCountBadge').textContent = `${fmtNum(total)} double runners (${fmtNum(finBothCount)} finished both)`;
      const genBadgeEl = document.getElementById('doubleGenderSummaryBadge');
      if (genBadgeEl) {
        genBadgeEl.innerHTML = `
          <span class="px-2.5 py-0.5 rounded-full font-semibold bg-sky-500/10 text-sky-500 border border-sky-500/20">Male Finished: ${fmtNum(finMaleCount)}</span>
          <span class="px-2.5 py-0.5 rounded-full font-semibold bg-pink-500/10 text-pink-500 border border-pink-500/20">Female Finished: ${fmtNum(finFemaleCount)}</span>
        `;
      }
      document.getElementById('doublePaginationInfo').textContent =
        total > 0
          ? `Showing ${fmtNum(startIdx + 1)}–${fmtNum(endIdx)} of ${fmtNum(total)} double-category runners`
          : 'No matching double-category runners found';
      document.getElementById('doublePageIndicator').textContent = `Page ${fmtNum(doublePage)} of ${fmtNum(totalPages)}`;
      document.getElementById('doublePrevPageBtn').disabled = doublePage <= 1;
      document.getElementById('doubleNextPageBtn').disabled = doublePage >= totalPages;

      const tbody = document.getElementById('doubleTableBody');
      if (!pageSlice.length) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" class="py-8 text-center text-sm text-[var(--muted-foreground)]">
              No double-category runners match your search filters.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = pageSlice.map((p, idx) => {
        const rankNum = startIdx + idx + 1;
        const r1 = DASHBOARD_DATA.runners[p[0]];
        const r2 = DASHBOARD_DATA.runners[p[1]];
        const ev1 = DASHBOARD_DATA.event_lookup[r1[0]];
        const ev2 = DASHBOARD_DATA.event_lookup[r2[0]];
        const combo = p[2];
        const bothFin = p[3] === 1;
        const combBruto = p[4];
        const combNetto = p[5];
        const combPace = p[6];
        const meta = DOUBLE_COMBO_META[combo] || { title: combo, dist: '' };

        const nameDisplay = r1[4] === r2[4]
          ? `<div class="font-bold text-[var(--foreground)]">${escapeHtml(r1[4])}</div>`
          : `<div class="font-bold text-[var(--foreground)]">${escapeHtml(r2[4].length >= r1[4].length ? r2[4] : r1[4])}</div>
             <div class="text-xs text-[var(--muted-foreground)]">Day 1: ${escapeHtml(r1[4])} • Day 2: ${escapeHtml(r2[4])}</div>`;

        return `
          <tr class="hover:bg-[var(--background)] transition">
            <td class="py-2.5 px-2.5 font-mono text-[var(--muted-foreground)]">#${fmtNum(rankNum)}</td>
            <td class="py-2.5 px-3">
              ${nameDisplay}
            </td>
            <td class="py-2.5 px-2 whitespace-nowrap">
              <span class="px-2 py-0.5 rounded text-xs font-medium ${
                r1[8] === 'Male' ? 'bg-sky-500/10 text-sky-500' : 'bg-pink-500/10 text-pink-500'
              }">${escapeHtml(r1[8])}</span>
              <div class="text-xs text-[var(--muted-foreground)] mt-0.5">${escapeHtml(r1[9])}</div>
            </td>
            <td class="py-2.5 px-2.5 whitespace-nowrap">
              <span class="px-2 py-0.5 rounded-md text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">${escapeHtml(meta.title)}</span>
              <div class="text-xs font-mono text-[var(--muted-foreground)] mt-0.5">${escapeHtml(meta.dist)}</div>
            </td>
            <td onclick="inspectDoubleRunnerInMainTable('${escapeHtml(r1[3])}')" class="py-2.5 px-3 border-l border-[var(--border)] cursor-pointer hover:opacity-80" title="Click to inspect Day 1 splits">
              <div class="flex items-center gap-1.5">
                ${statusBadgeHtml(r1[1], r1[2])}
                <span class="font-semibold text-[var(--foreground)]">${escapeHtml(ev1.name)}</span>
              </div>
              <div class="text-xs text-[var(--muted-foreground)] mt-0.5">Bib: <span class="font-mono font-semibold text-[var(--foreground)]">${escapeHtml(r1[3])}</span> • ${escapeHtml(r1[7])}</div>
            </td>
            <td class="py-2.5 px-2.5 text-right font-mono whitespace-nowrap">
              <div class="text-xs text-[var(--muted-foreground)]">Bruto: <span class="font-semibold text-[var(--foreground)]">${escapeHtml(r1[5] || '—')}</span></div>
              <div class="text-xs text-emerald-500">Netto: <span class="font-bold">${escapeHtml(r1[13] || '—')}</span></div>
            </td>
            <td onclick="inspectDoubleRunnerInMainTable('${escapeHtml(r2[3])}')" class="py-2.5 px-3 border-l border-[var(--border)] cursor-pointer hover:opacity-80" title="Click to inspect Day 2 splits">
              <div class="flex items-center gap-1.5">
                ${statusBadgeHtml(r2[1], r2[2])}
                <span class="font-semibold text-[var(--foreground)]">${escapeHtml(ev2.name)}</span>
              </div>
              <div class="text-xs text-[var(--muted-foreground)] mt-0.5">Bib: <span class="font-mono font-semibold text-[var(--foreground)]">${escapeHtml(r2[3])}</span> • ${escapeHtml(r2[7])}</div>
            </td>
            <td class="py-2.5 px-2.5 text-right font-mono whitespace-nowrap">
              <div class="text-xs text-[var(--muted-foreground)]">Bruto: <span class="font-semibold text-[var(--foreground)]">${escapeHtml(r2[5] || '—')}</span></div>
              <div class="text-xs text-emerald-500">Netto: <span class="font-bold">${escapeHtml(r2[13] || '—')}</span></div>
            </td>
            <td class="py-2.5 px-3 text-right font-mono whitespace-nowrap border-l border-[var(--border)]">
              ${bothFin ? `
                <div class="font-bold text-emerald-500">${escapeHtml(combNetto)}</div>
                <div class="text-xs text-sky-500">${escapeHtml(combPace)}</div>
                <div class="text-xs text-[var(--muted-foreground)]">Bruto: ${escapeHtml(combBruto)}</div>
              ` : '<span class="text-xs text-[var(--muted-foreground)]">Incomplete</span>'}
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderAll() {
      renderTabs();
      renderKPIs();
      renderStatusAndRightPanel();
      renderCountryJoiners();
      renderWinners();
      renderDoubleComboCards();
    }

    // Event listeners for Runner Table
    document.getElementById('runnerSearchInput').addEventListener('input', e => {
      runnerQuery = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerEventSelect').addEventListener('change', e => {
      runnerEventFilter = e.target.value;
      activeBucketFilter = null;
      updateBucketFilterBadge();
      renderStatusAndRightPanel();
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
    document.getElementById('runnerRemarkSelect').addEventListener('change', e => {
      runnerRemarkFilter = e.target.value;
      filterRunnersList();
    });
    document.getElementById('runnerClassSelect').addEventListener('change', e => {
      runnerClassFilter = e.target.value;
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
      runnerRemarkFilter = 'ALL';
      runnerClassFilter = 'ALL';
      runnerSortCol = 'pos';
      runnerSortDir = 'asc';
      activeBucketFilter = null;
      updateBucketFilterBadge();
      renderStatusAndRightPanel();
      document.getElementById('runnerSearchInput').value = '';
      document.getElementById('runnerEventSelect').value = 'ALL';
      document.getElementById('runnerCategorySelect').value = 'ALL';
      document.getElementById('runnerGenderSelect').value = 'ALL';
      document.getElementById('runnerStatusSelect').value = 'ALL';
      document.getElementById('runnerRemarkSelect').value = 'ALL';
      document.getElementById('runnerClassSelect').value = 'ALL';
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

    // Event listeners for Double Category Runners Table
    document.getElementById('doubleSearchInput').addEventListener('input', e => {
      doubleQuery = e.target.value;
      filterDoubleRunnersList();
    });
    document.getElementById('doubleComboSelect').addEventListener('change', e => {
      doubleComboFilter = e.target.value;
      renderDoubleComboCards();
      filterDoubleRunnersList();
    });
    document.getElementById('doubleStatusSelect').addEventListener('change', e => {
      doubleStatusFilter = e.target.value;
      filterDoubleRunnersList();
    });
    document.getElementById('doubleGenderSelect').addEventListener('change', e => {
      doubleGenderFilter = e.target.value;
      filterDoubleRunnersList();
    });
    document.getElementById('doublePageSizeSelect').addEventListener('change', e => {
      doublePageSize = Number(e.target.value);
      doublePage = 1;
      renderDoubleTable();
    });
    document.getElementById('doublePrevPageBtn').addEventListener('click', () => {
      if (doublePage > 1) {
        doublePage--;
        renderDoubleTable();
      }
    });
    document.getElementById('doubleNextPageBtn').addEventListener('click', () => {
      const totalPages = Math.max(1, Math.ceil(filteredDoublePairs.length / doublePageSize));
      if (doublePage < totalPages) {
        doublePage++;
        renderDoubleTable();
      }
    });
    document.getElementById('resetDoubleFiltersBtn').addEventListener('click', () => {
      doubleQuery = '';
      doubleComboFilter = 'ALL';
      doubleStatusFilter = 'ALL';
      doubleGenderFilter = 'ALL';
      document.getElementById('doubleSearchInput').value = '';
      document.getElementById('doubleComboSelect').value = 'ALL';
      document.getElementById('doubleStatusSelect').value = 'ALL';
      document.getElementById('doubleGenderSelect').value = 'ALL';
      renderDoubleComboCards();
      filterDoubleRunnersList();
    });

    const NAV_SECTION_IDS = [
      'overviewSection',
      'countrySection',
      'winnersSection',
      'runnerTableSection',
      'doubleRunnersSection'
    ];

    function setActiveNavBtn(targetId) {
      document.querySelectorAll('.nav-jump-btn').forEach(btn => {
        const active = btn.dataset.navTarget === targetId;
        btn.className = active
          ? 'nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-semibold transition bg-emerald-600 text-white shadow-sm'
          : 'nav-jump-btn px-3 py-1.5 rounded-lg text-xs font-medium transition text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--background)]';
      });
    }

    let navMenuHidden = false;

    function toggleNavMenu(hide) {
      navMenuHidden = Boolean(hide);
      const expanded = document.getElementById('stickyNavExpanded');
      const collapsed = document.getElementById('stickyNavCollapsed');
      if (!expanded || !collapsed) return;
      if (navMenuHidden) {
        expanded.classList.add('hidden');
        collapsed.classList.remove('hidden');
      } else {
        expanded.classList.remove('hidden');
        collapsed.classList.add('hidden');
      }
    }

    function scrollToSection(sectionId) {
      const el = document.getElementById(sectionId);
      if (!el) return;
      if (NAV_SECTION_IDS.includes(sectionId)) {
        setActiveNavBtn(sectionId);
      } else {
        setActiveNavBtn('overviewSection');
      }
      if (window.innerWidth < 640 && sectionId !== 'topHeaderSection') {
        toggleNavMenu(true);
      }
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    window.addEventListener('scroll', () => {
      let current = NAV_SECTION_IDS[0];
      for (const id of NAV_SECTION_IDS) {
        const el = document.getElementById(id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 140) {
            current = id;
          }
        }
      }
      setActiveNavBtn(current);
    }, { passive: true });

    initRunnerFilterOptions();
    renderGlobalFilterBar();
    renderAll();
    filterRunnersList();
    filterDoubleRunnersList();
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
