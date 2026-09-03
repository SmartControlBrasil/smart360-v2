#!/usr/bin/env python3
"""Local diagnosis after composite fix."""
import asyncio
import json
import sys
import time

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013/"
OUT = "/tmp/smart360-composite-fix-diagnosis.json"

# Reuse instrumentation from production script
from exp_document_composite_diagnosis import BASE_INSTRUMENT, run_scenario


async def main():
    scenarios = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def run(label, viewport, **kwargs):
            ctx = await browser.new_context(
                viewport=viewport,
                user_agent=(
                    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                )
                if viewport["width"] < 800
                else (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()

            async def goto_local(route):
                req = route.request
                if req.url.rstrip("/") == "https://www.smartcontrolbrasil.com.br/" or req.url == URL:
                    pass
                await route.continue_()

            # patch goto target inside run_scenario by monkeypatching page.goto
            orig = run_scenario

            async def run_local(page, label, **kwargs):
                await page.add_init_script(BASE_INSTRUMENT)
                inject_css = kwargs.get("inject_css")
                if inject_css:
                    await page.add_init_script(
                        f"(() => {{ const s=document.createElement('style'); s.textContent=`{inject_css}`; document.documentElement.appendChild(s); }})();"
                    )
                await page.goto(URL, wait_until="load", timeout=60000)
                await page.wait_for_timeout(5000)
                data = await page.evaluate("() => window.__docDiag")
                cls_total = sum(x["value"] for x in data.get("layoutShift", []))
                cls_shapes = sum(
                    x["value"]
                    for x in data.get("layoutShift", [])
                    if any("banner1__shapes" in (s.get("node") or "") for s in x.get("sources", []))
                )
                top_cls = sorted(
                    (
                        (s.get("node") or "?", x["value"])
                        for x in data.get("layoutShift", [])
                        for s in x.get("sources", [])
                    ),
                    key=lambda t: t[1],
                    reverse=True,
                )[:8]
                return {
                    "label": label,
                    "fcp": data.get("paints", {}).get("fcp"),
                    "lcp": data.get("paints", {}).get("lcp"),
                    "cls_total": round(cls_total, 4),
                    "cls_shapes": round(cls_shapes, 4),
                    "top_cls_sources": top_cls,
                    "longTaskTotalMs": sum(t["duration"] for t in data.get("longTasks", [])),
                    "cssEvents": data.get("css", []),
                    "h1Timeline": data.get("h1", [])[:12],
                }

            result = await run_local(page, label, **kwargs)
            await ctx.close()
            return result

        mobile = {"width": 390, "height": 844}
        desktop = {"width": 1440, "height": 900}
        scenarios.append(await run("mobile_fix_local", mobile))
        scenarios.append(await run("desktop_fix_local", desktop))
        await browser.close()

    report = {"url": URL, "scenarios": scenarios, "generatedAt": time.time()}
    with open(OUT, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
