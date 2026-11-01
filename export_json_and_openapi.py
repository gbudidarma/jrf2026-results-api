import csv
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent

EVENTS_CONFIG = [
    {
        "event_slug": "mybca_jakarta_half_marathon",
        "event_name": "myBCA Jakarta Half Marathon",
        "race_day": "Day 1",
        "cid": 19723,
        "rid": 337,
        "eid": 1,
        "distance_km": 21.1,
        "csv_file": "mybca_jakarta_half_marathon_results.csv",
        "json_file": "mybca_jakarta_half_marathon_results.json",
        "split_columns": ["KM 5", "KM 10", "KM 15", "KM 20", "FINISH"],
    },
    {
        "event_slug": "samsung_galaxy_5k",
        "event_name": "Samsung Galaxy 5K",
        "race_day": "Day 1",
        "cid": 19723,
        "rid": 337,
        "eid": 2,
        "distance_km": 5.0,
        "csv_file": "samsung_galaxy_5k_results.csv",
        "json_file": "samsung_galaxy_5k_results.json",
        "split_columns": ["KM 3.4", "FINISH"],
    },
    {
        "event_slug": "hydroplus_marathon",
        "event_name": "Hydroplus Marathon",
        "race_day": "Day 2",
        "cid": 19723,
        "rid": 338,
        "eid": 1,
        "distance_km": 42.195,
        "csv_file": "hydroplus_marathon_results.csv",
        "json_file": "hydroplus_marathon_results.json",
        "split_columns": [
            "KM 5",
            "KM 10",
            "KM 15",
            "KM 20",
            "KM 21.1",
            "KM 25",
            "KM 30",
            "KM 35",
            "KM 40",
            "FINISH",
        ],
    },
    {
        "event_slug": "le_minerale_10k",
        "event_name": "Le Minerale 10K",
        "race_day": "Day 2",
        "cid": 19723,
        "rid": 338,
        "eid": 3,
        "distance_km": 10.0,
        "csv_file": "le_minerale_10k_results.csv",
        "json_file": "le_minerale_10k_results.json",
        "split_columns": ["KM 3.9", "KM 8.8", "FINISH"],
    },
]


def time_to_sec(t: str | None) -> int | None:
    if not t:
        return None
    parts = [int(x) for x in t.strip().split(":") if x.strip().isdigit()]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None


def sec_to_hms(s: int | None) -> str | None:
    if s is None or s <= 0:
        return None
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def compute_netto_time(splits: dict, split_cols: list[str]) -> str | None:
    clean_cols = [c for c in split_cols if c != "RTW"]
    vals = [time_to_sec(splits.get(c)) for c in clean_cols]
    if not vals or vals[-1] is None:
        return None
    if any(v is None for v in vals):
        last_none = max(i for i, v in enumerate(vals) if v is None)
        tail = vals[last_none + 1 :]
        return sec_to_hms(sum(tail)) if tail else None
    return sec_to_hms(sum(vals))


def parse_position_and_status(raw_pos: str, finish_time: str) -> tuple[int | None, str]:
    """Convert raw Pos value ('1', '1,000', 'DNS', 'DNF', 'CUT', 'DQ', 'QRY') into (position_int, status_str)."""
    cleaned = raw_pos.replace(",", "").strip()
    if cleaned.isdigit():
        return int(cleaned), "FINISHED"
    if cleaned in {"DNS", "DNF", "CUT", "DQ", "DSQ", "QRY"}:
        return None, cleaned
    return (None, "FINISHED" if finish_time else "UNKNOWN")


def convert_csv_to_records(cfg: dict) -> list[dict]:
    csv_path = WORKSPACE / cfg["csv_file"]
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_pos = (row.get("Pos") or "").strip()
            finish_time = (row.get("Time") or "").strip() or None
            pos_int, status = parse_position_and_status(raw_pos, finish_time or "")

            splits = {}
            for col in cfg["split_columns"]:
                val = (row.get(col) or "").strip()
                splits[col] = val if val else None

            netto_time = compute_netto_time(splits, cfg["split_columns"]) if status == "FINISHED" else None

            record = {
                "event_slug": cfg["event_slug"],
                "event_name": cfg["event_name"],
                "race_day": cfg["race_day"],
                "position": pos_int,
                "status": status,
                "bib_no": (row.get("Bib No") or "").strip(),
                "name": (row.get("Name") or "").strip(),
                "time": finish_time,
                "bruto_time": finish_time,
                "netto_time": netto_time,
                "category": (row.get("Category") or "").strip() or None,
                "gender": (row.get("Gender") or "").strip() or None,
                "country": (row.get("Country") or "").strip() or None,
                "splits": splits,
            }
            records.append(record)
    return records


def build_openapi_spec(event_summaries: list[dict], sample_runner: dict) -> dict:
    event_slugs = [e["event_slug"] for e in event_summaries]
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Jakarta Running Festival (JRF) Race Results API",
            "description": (
                "Official race results and split timings dataset for the Jakarta Running Festival "
                "(Day 1 & Day 2), covering the Hydroplus Marathon (42.2K), myBCA Jakarta Half Marathon (21.1K), "
                "Le Minerale 10K, and Samsung Galaxy 5K."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "JRF Results API Support",
            },
        },
        "servers": [
            {
                "url": "https://raw.githubusercontent.com/gbudidarma/jrf2026-results-api/main",
                "description": "GitHub Raw Static JSON Server",
            }
        ],
        "tags": [
            {"name": "Events", "description": "Race events metadata and participant counts"},
            {"name": "Results", "description": "Event race results and split times"},
        ],
        "paths": {
            "/events.json": {
                "get": {
                    "operationId": "listEvents",
                    "tags": ["Events"],
                    "summary": "List all race events and participant counts",
                    "description": "Returns metadata and total participant counts for all 4 Jakarta Running Festival race events.",
                    "responses": {
                        "200": {
                            "description": "List of race events",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "competition": {"type": "string", "example": "Jakarta Running Festival"},
                                            "cid": {"type": "integer", "example": 19723},
                                            "total_events": {"type": "integer", "example": 4},
                                            "total_participants": {"type": "integer", "example": 36306},
                                            "events": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/EventSummary"},
                                            },
                                        },
                                    },
                                    "example": {
                                        "competition": "Jakarta Running Festival",
                                        "cid": 19723,
                                        "total_events": len(event_summaries),
                                        "total_participants": sum(e["total_participants"] for e in event_summaries),
                                        "events": event_summaries,
                                    },
                                }
                            },
                        }
                    },
                }
            },
            "/{event_slug}_results.json": {
                "get": {
                    "operationId": "getEventResultsBySlug",
                    "tags": ["Results"],
                    "summary": "Get results by event slug",
                    "description": "Fetches the complete results dataset for the selected event slug.",
                    "parameters": [
                        {
                            "name": "event_slug",
                            "in": "path",
                            "required": True,
                            "description": "Event slug identifier",
                            "schema": {
                                "type": "string",
                                "enum": event_slugs,
                                "default": "hydroplus_marathon",
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Event results dataset",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EventDatasetResponse"},
                                }
                            },
                        }
                    },
                }
            },
            "/hydroplus_marathon_results.json": {
                "get": {
                    "operationId": "getHydroplusMarathonResults",
                    "tags": ["Results"],
                    "summary": "Get Hydroplus Marathon (42.2K) results",
                    "description": "Returns all 4,420 participant results and split times for the Day 2 Hydroplus Marathon.",
                    "responses": {
                        "200": {
                            "description": "Hydroplus Marathon results",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EventDatasetResponse"},
                                }
                            },
                        }
                    },
                }
            },
            "/le_minerale_10k_results.json": {
                "get": {
                    "operationId": "getLeMinerale10KResults",
                    "tags": ["Results"],
                    "summary": "Get Le Minerale 10K results",
                    "description": "Returns all 12,441 participant results and split times for the Day 2 Le Minerale 10K.",
                    "responses": {
                        "200": {
                            "description": "Le Minerale 10K results",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EventDatasetResponse"},
                                }
                            },
                        }
                    },
                }
            },
            "/mybca_jakarta_half_marathon_results.json": {
                "get": {
                    "operationId": "getMyBcaHalfMarathonResults",
                    "tags": ["Results"],
                    "summary": "Get myBCA Jakarta Half Marathon (21.1K) results",
                    "description": "Returns all 14,684 participant results and split times for the Day 1 myBCA Jakarta Half Marathon.",
                    "responses": {
                        "200": {
                            "description": "myBCA Jakarta Half Marathon results",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EventDatasetResponse"},
                                }
                            },
                        }
                    },
                }
            },
            "/samsung_galaxy_5k_results.json": {
                "get": {
                    "operationId": "getSamsungGalaxy5KResults",
                    "tags": ["Results"],
                    "summary": "Get Samsung Galaxy 5K results",
                    "description": "Returns all 4,761 participant results and split times for the Day 1 Samsung Galaxy 5K.",
                    "responses": {
                        "200": {
                            "description": "Samsung Galaxy 5K results",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EventDatasetResponse"},
                                }
                            },
                        }
                    },
                }
            },
            "/jrf_all_results.json": {
                "get": {
                    "operationId": "getAllJrfResults",
                    "tags": ["Results"],
                    "summary": "Get all 36,306 results across all 4 events",
                    "description": "Returns the complete combined dataset for all 4 Jakarta Running Festival events.",
                    "responses": {
                        "200": {
                            "description": "Combined results dataset",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "competition": {"type": "string", "example": "Jakarta Running Festival"},
                                            "cid": {"type": "integer", "example": 19723},
                                            "total_events": {"type": "integer", "example": 4},
                                            "total_participants": {"type": "integer", "example": 36306},
                                            "events": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/EventSummary"},
                                            },
                                            "results": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/RunnerResult"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "EventSummary": {
                    "type": "object",
                    "required": [
                        "event_slug",
                        "event_name",
                        "race_day",
                        "distance_km",
                        "total_participants",
                        "finishers_count",
                        "split_checkpoints",
                    ],
                    "properties": {
                        "event_slug": {"type": "string", "example": "hydroplus_marathon"},
                        "event_name": {"type": "string", "example": "Hydroplus Marathon"},
                        "race_day": {"type": "string", "example": "Day 2"},
                        "distance_km": {"type": "number", "format": "float", "example": 42.195},
                        "total_participants": {"type": "integer", "example": 4420},
                        "finishers_count": {"type": "integer", "example": 2637},
                        "split_checkpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["KM 5", "KM 10", "KM 15", "KM 20", "KM 21.1", "KM 25", "KM 30", "KM 35", "KM 40", "FINISH"],
                        },
                    },
                },
                "RunnerResult": {
                    "type": "object",
                    "required": ["event_slug", "event_name", "race_day", "status", "bib_no", "name", "splits"],
                    "properties": {
                        "event_slug": {"type": "string", "example": "hydroplus_marathon"},
                        "event_name": {"type": "string", "example": "Hydroplus Marathon"},
                        "race_day": {"type": "string", "example": "Day 2"},
                        "position": {"type": "integer", "nullable": True, "example": 1},
                        "status": {
                            "type": "string",
                            "enum": ["FINISHED", "DNS", "DNF", "CUT", "DQ", "DSQ", "QRY", "UNKNOWN"],
                            "example": "FINISHED",
                        },
                        "bib_no": {"type": "string", "example": "A14328"},
                        "name": {"type": "string", "example": "KIPRONO KOECH"},
                        "time": {"type": "string", "nullable": True, "example": "02:15:41"},
                        "bruto_time": {"type": "string", "nullable": True, "example": "02:15:41"},
                        "netto_time": {"type": "string", "nullable": True, "example": "02:15:37"},
                        "category": {"type": "string", "nullable": True, "example": "TOP 3 OPEN"},
                        "gender": {"type": "string", "nullable": True, "example": "Male"},
                        "country": {"type": "string", "nullable": True, "example": "Kenya"},
                        "splits": {
                            "type": "object",
                            "properties": {
                                "KM 3.4": {"type": "string", "nullable": True},
                                "KM 3.9": {"type": "string", "nullable": True},
                                "KM 5": {"type": "string", "nullable": True},
                                "KM 8.8": {"type": "string", "nullable": True},
                                "KM 10": {"type": "string", "nullable": True},
                                "KM 15": {"type": "string", "nullable": True},
                                "KM 20": {"type": "string", "nullable": True},
                                "KM 21.1": {"type": "string", "nullable": True},
                                "KM 25": {"type": "string", "nullable": True},
                                "KM 30": {"type": "string", "nullable": True},
                                "KM 35": {"type": "string", "nullable": True},
                                "KM 40": {"type": "string", "nullable": True},
                                "FINISH": {"type": "string", "nullable": True},
                            },
                            "example": sample_runner["splits"],
                        },
                    },
                },
                "EventDatasetResponse": {
                    "type": "object",
                    "required": ["metadata", "results"],
                    "properties": {
                        "metadata": {"$ref": "#/components/schemas/EventSummary"},
                        "results": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/RunnerResult"},
                        },
                    },
                },
            }
        },
    }


def main():
    all_events_summary = []
    all_records = []
    events_payload = {}

    for cfg in EVENTS_CONFIG:
        records = convert_csv_to_records(cfg)
        finishers = sum(1 for r in records if r["status"] == "FINISHED")
        summary = {
            "event_slug": cfg["event_slug"],
            "event_name": cfg["event_name"],
            "race_day": cfg["race_day"],
            "distance_km": cfg["distance_km"],
            "total_participants": len(records),
            "finishers_count": finishers,
            "split_checkpoints": cfg["split_columns"],
        }
        all_events_summary.append(summary)
        all_records.extend(records)
        events_payload[cfg["event_slug"]] = {
            "metadata": summary,
            "results": records,
        }

        out_json = WORKSPACE / cfg["json_file"]
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(events_payload[cfg["event_slug"]], f, ensure_ascii=False, indent=2)
        print(f"Created {out_json.name} ({len(records)} records)")

    # Write events summary JSON
    events_summary_path = WORKSPACE / "events.json"
    events_summary_data = {
        "competition": "Jakarta Running Festival",
        "cid": 19723,
        "total_events": len(all_events_summary),
        "total_participants": len(all_records),
        "events": all_events_summary,
    }
    with open(events_summary_path, "w", encoding="utf-8") as f:
        json.dump(events_summary_data, f, ensure_ascii=False, indent=2)
    print(f"Created {events_summary_path.name} (summary of {len(all_events_summary)} events)")

    # Write combined JSON dataset
    combined_path = WORKSPACE / "jrf_all_results.json"
    combined_data = {
        **events_summary_data,
        "results": all_records,
    }
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    print(f"Created {combined_path.name} ({len(all_records)} total records)")

    # Pick first marathon finisher as example for OpenAPI spec
    sample_runner = events_payload["hydroplus_marathon"]["results"][0]
    openapi_spec = build_openapi_spec(all_events_summary, sample_runner)
    openapi_path = WORKSPACE / "openapi.json"
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, ensure_ascii=False, indent=2)
    print(f"Created {openapi_path.name} (OpenAPI 3.0.0 specification mapped to GitHub JSON paths)")


if __name__ == "__main__":
    main()
