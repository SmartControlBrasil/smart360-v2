#!/usr/bin/env python3
"""Validate shape-4 CLS fix (composite3) on production + local."""
import asyncio
import json
import statistics
from pathlib import Path

from playwright.async_api import async_playwright

PROD = "https://www.smartcontrolbrasil.com.br/"
LOCAL = "http://127.0.0.1:8013/"
PATCH = Path(__file__).resolve().parents[1] / "static/institutional/css/home-critical.css"
OUT = Path("/tmp/smart360-shape4-fix-validation.json")

INIT = """
(() => {
  window.__v = { shifts: [], header: [], h1: [], area: [] };
  const track = () => {
    const h = document.querySelector('.header-1');
    const h1 = document.querySelector('.banner-heading__wrapper-title');
    const a = document.querySelector('.banner1__area');
    if (h) window.__v.header.push(Math.round(h.getBoundingClientRect().top));
    if (h1) window.__v.h1.push(Math.round(h1.getBoundingClientRect().top));
    if (a) window.__v.area.push(Math.round(a.getBoundingClientRect().height));
    requestAnimationFrame(track);
  };
  requestAnimationFrame(track);
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) {
      if (e.hadRecentInput) continue;
      window.__v.shifts.push({
        t: Math.round(e.startTime),
        v: e.value,
        sources: (e.sources || []).map((s) => ({
          node: s.node ? (s.node.tagName + '.' + (s.node.className || '').toString().slice(0, 60)) : '',
          prev: s.previousRect ? { x: s.previousRect.x, y: s.previousRect.y, w: s.previousRect.width, h: s.previousRect.height } : null,
          curr: s.currentRect ? { x: s.currentRect.x, y: s.currentRect.y, w: s.currentRect.width, h: s.currentRect.height } : null,
        })),
      });
    }
  }).observe({ type: 'layout-shift', buffered: true });
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.name === 'first-contentful-paint') window.__v.fcp = Math.round(e.startTime);
      }
    }).observe({ type: 'paint', buffered: true });
  } catch (e) {}
  try {
    new PerformanceObserver((list) => {
      const es = list.getEntries();
      if (es.length) window.__v.lcp = Math.round(es[es.length - 1].startTime);
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}
})();
"""


async def run(url, viewport, patch_prod=False, runs=5):
    rows = []
    css = PATCH.read_text()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for i in range(runs):
            ctx = await browser.new_context(
                viewport={"width": viewport[0], "height": viewport[1]},
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                )
                if viewport[0] < 800
                else (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()
            await page.add_init_script(INIT)
            if patch_prod:

                async def route(r):
                    if "home-critical.css" in r.request.url:
                        await r.fulfill(status=200, content_type="text/css", body=css)
                    else:
                        await r.continue_()

                await page.route("**/*", route)
            await page.goto(url, wait_until="load", timeout=90000)
            await page.wait_for_timeout(5000)
            data = await page.evaluate("() => window.__v")
            cls = sum(x["v"] for x in data["shifts"])
            s4 = sum(
                x["v"] for x in data["shifts"]
                if any("shape-4" in (s.get("node") or "") for s in x.get("sources", []))
            )
            s3 = sum(
                x["v"] for x in data["shifts"]
                if any("shape-3" in (s.get("node") or "") for s in x.get("sources", []))
            )
            livia = sum(
                x["v"] for x in data["shifts"]
                if any("livia" in (s.get("node") or "").lower() for s in x.get("sources", []))
            )
            hs = data.get("area") or []
            rows.append({
                "cls": round(cls, 4),
                "shape4": round(s4, 4),
                "shape3": round(s3, 4),
                "livia": round(livia, 4),
                "fcp": data.get("fcp"),
                "lcp": data.get("lcp"),
                "header_delta": (max(data["header"]) - min(data["header"])) if data.get("header") else 0,
                "h1_delta": (max(data["h1"]) - min(data["h1"])) if data.get("h1") else 0,
                "area_delta": (max(hs) - min(hs)) if hs else 0,
                "top": sorted(
                    ((s.get("node") or "?", x["v"]) for x in data["shifts"] for s in x.get("sources", [])),
                    key=lambda t: t[1], reverse=True,
                )[:5],
            })
            await ctx.close()
        await browser.close()
    med = lambda k: statistics.median([r[k] for r in rows])
    return {"runs": rows, "median": {k: med(k) for k in rows[0]}}


async def main():
    report = {
        "prod_mobile_patch": await run(PROD, (390, 844), patch_prod=True),
        "prod_desktop_patch": await run(PROD, (1440, 900), patch_prod=True),
        "local_mobile": await run(LOCAL, (390, 844), patch_prod=False, runs=3),
        "local_desktop": await run(LOCAL, (1440, 900), patch_prod=False, runs=3),
    }
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["median"] for k, v in report.items()}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
