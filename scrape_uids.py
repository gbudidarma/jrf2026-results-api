import asyncio
import json
import re
from pathlib import Path
from scrape_results import start_browser_reliably

WORKSPACE = Path(__file__).resolve().parent

EVENTS = [
    (19723, 337, 1, "mybca_jakarta_half_marathon"),
    (19723, 337, 2, "samsung_galaxy_5k"),
    (19723, 338, 1, "hydroplus_marathon"),
    (19723, 338, 3, "le_minerale_10k"),
]


async def fetch_uid_batch(page, urls: list[str]) -> list[dict]:
    js_code = f"""
    (async () => {{
        const urls = {json.dumps(urls)};
        const parseHtml = (html) => {{
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const table = doc.getElementById('ctl00_Content_Main_tblResults');
            if (!table) return {{ items: [], maxPage: 1 }};
            const trs = Array.from(table.querySelectorAll('tr'));
            if (!trs.length) return {{ items: [], maxPage: 1 }};

            const headerCells = Array.from(trs[0].querySelectorAll('th, td'));
            let bibIdx = -1;
            headerCells.forEach((cell, idx) => {{
                const text = cell.textContent.replace(/\\s+/g, ' ').trim().toLowerCase();
                if (text === 'bib no' || text === 'bib') bibIdx = idx;
            }});
            if (bibIdx === -1) bibIdx = 2;

            const items = [];
            for (let i = 1; i < trs.length; i++) {{
                const tr = trs[i];
                const cells = Array.from(tr.querySelectorAll('th, td'));
                if (cells.length <= bibIdx) continue;
                const bib = cells[bibIdx].textContent.replace(/\\s+/g, ' ').trim();
                const link = tr.querySelector('a[href*="uid="]');
                if (bib && link) {{
                    const href = link.getAttribute('href') || '';
                    const m = href.match(/uid=([0-9-]+)/i);
                    if (m) {{
                        items.push([bib, m[1]]);
                    }}
                }}
            }}

            let maxPage = 1;
            const pager = doc.getElementById('ctl00_Content_Main_grdBottomPager');
            if (pager) {{
                pager.querySelectorAll('a').forEach(a => {{
                    const href = a.getAttribute('href') || '';
                    const m = href.match(/PageNo=(\\d+)/i);
                    if (m) maxPage = Math.max(maxPage, parseInt(m[1], 10));
                }});
                pager.querySelectorAll('span').forEach(s => {{
                    const t = s.textContent.trim();
                    if (/^\\d+$/.test(t)) maxPage = Math.max(maxPage, parseInt(t, 10));
                }});
            }}
            return {{ items, maxPage }};
        }};

        const results = await Promise.all(
            urls.map(async (u) => {{
                for (let attempt = 0; attempt < 3; attempt++) {{
                    try {{
                        const resp = await fetch(u, {{ credentials: 'include' }});
                        if (resp.ok) {{
                            const html = await resp.text();
                            return parseHtml(html);
                        }}
                    }} catch (e) {{}}
                    await new Promise(r => setTimeout(r, 800));
                }}
                return {{ items: [], maxPage: 1 }};
            }})
        );
        return JSON.stringify(results);
    }})()
    """
    raw = await page.evaluate(js_code, await_promise=True, return_by_value=True)
    if not raw or not isinstance(raw, str):
        return [{"items": [], "maxPage": 1} for _ in urls]
    return json.loads(raw)


async def main():
    browser, proc = await start_browser_reliably()
    uid_map = {}
    try:
        start_url = "https://results.scorenow.co.id/Results.aspx?CId=19723&RId=337&EId=1&dt=0&PageNo=1"
        page = await browser.get(start_url)
        for i in range(25):
            await asyncio.sleep(1.5)
            content = await page.get_content()
            if "ctl00_Content_Main_tblResults" in content:
                print(f"Cloudflare passed at step {i}", flush=True)
                break
        else:
            raise RuntimeError("Timed out waiting for ScoreNow table")

        for cid, rid, eid, slug in EVENTS:
            first_url = f"https://results.scorenow.co.id/Results.aspx?CId={cid}&RId={rid}&EId={eid}&dt=0&PageNo=1"
            res_list = await fetch_uid_batch(page, [first_url])
            first_res = res_list[0]
            max_page = first_res["maxPage"]
            ev_map = {}
            for bib, uid in first_res["items"]:
                ev_map[bib] = uid

            print(f"[{slug}] Page 1 scraped ({len(ev_map)} items), maxPage={max_page}", flush=True)

            batch_size = 20
            curr = 2
            while curr <= max_page:
                end_p = min(curr + batch_size - 1, max_page)
                urls = [
                    f"https://results.scorenow.co.id/Results.aspx?CId={cid}&RId={rid}&EId={eid}&dt=0&PageNo={p}"
                    for p in range(curr, end_p + 1)
                ]
                b_res = await fetch_uid_batch(page, urls)
                for r in b_res:
                    for bib, uid in r["items"]:
                        ev_map[bib] = uid
                    if r["maxPage"] > max_page:
                        max_page = r["maxPage"]
                print(f"  [{slug}] Pages {curr}..{end_p}/{max_page} -> {len(ev_map)} UIDs", flush=True)
                curr = end_p + 1

            uid_map[slug] = ev_map
            print(f"Completed {slug}: {len(ev_map)} runner UIDs collected.", flush=True)

        out_path = WORKSPACE / "runner_uids.json"
        out_path.write_text(json.dumps(uid_map, separators=(",", ":")), encoding="utf-8")
        total_uids = sum(len(v) for v in uid_map.values())
        print(f"\nSaved {total_uids} total runner UIDs to {out_path}", flush=True)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
