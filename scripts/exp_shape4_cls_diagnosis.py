#!/usr/bin/env python3
"""Deep diagnosis: banner1__shapes-shape-4 CLS on production with fixed-UI patch."""
import asyncio
import json
import statistics
import time
from pathlib import Path

from playwright.async_api import async_playwright

PROD = "https://www.smartcontrolbrasil.com.br/"
PATCH_CSS = Path(__file__).resolve().parents[1] / "static/institutional/css/home-critical.css"
OUT = Path("/tmp/smart360-shape4-cls-diagnosis.json")

PROPS = [
    "position", "top", "right", "bottom", "left", "width", "height", "display",
    "visibility", "opacity", "transform", "transformOrigin", "filter",
    "animationName", "animationDuration", "animationDelay", "animationFillMode",
    "transition", "margin", "padding", "overflow", "zIndex", "contain",
    "backgroundSize", "backgroundPosition",
]

TRACE_JS = """
(() => {
  const PROPS = %s;
  window.__s4 = { samples: [], shifts: [], css: {} };
  const S = window.__s4;

  const rectObj = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      top: r.top, left: r.left, right: r.right, bottom: r.bottom,
      width: r.width, height: r.height, x: r.x, y: r.y,
      offsetTop: el.offsetTop, offsetLeft: el.offsetLeft,
      offsetWidth: el.offsetWidth, offsetHeight: el.offsetHeight,
    };
  };

  const styleObj = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const o = {};
    for (const p of PROPS) o[p] = cs[p];
    return o;
  };

  const snap = (label) => {
    const el = document.querySelector('.banner1__shapes-shape-4');
    const parents = {
      shapes: document.querySelector('.banner1__shapes'),
      area: document.querySelector('.banner1__area'),
      section: document.querySelector('.banner-before'),
      col9: document.querySelector('.banner1__area .col-lg-9'),
    };
    S.samples.push({
      label,
      t: Math.round(performance.now()),
      shape4: { rect: rectObj(el), style: styleObj(el) },
      parents: Object.fromEntries(Object.entries(parents).map(([k, n]) => [k, { rect: rectObj(n), style: n ? { position: getComputedStyle(n).position, width: getComputedStyle(n).width, height: getComputedStyle(n).height } : null }])),
      bodyH: document.body.scrollHeight,
    });
  };

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.hadRecentInput) continue;
        const sources = (e.sources || []).map((s) => ({
          node: s.node ? (s.node.tagName + '.' + (s.node.className || '').toString().slice(0, 80)) : '',
          prev: s.previousRect ? { x: s.previousRect.x, y: s.previousRect.y, w: s.previousRect.width, h: s.previousRect.height } : null,
          curr: s.currentRect ? { x: s.currentRect.x, y: s.currentRect.y, w: s.currentRect.width, h: s.currentRect.height } : null,
        }));
        S.shifts.push({ t: Math.round(e.startTime), value: e.value, sources });
        if (sources.some((x) => x.node.includes('shape-4'))) {
          snap('shift_shape4_' + Math.round(e.startTime));
        }
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}

  const links = [...document.querySelectorAll('link')];
  links.forEach((link) => {
    link.addEventListener('load', () => {
      const href = link.href || '';
      if (href.includes('home-critical.css')) { S.css.critical = Math.round(performance.now()); snap('T1_critical'); }
      else if (href.includes('main.css')) { S.css.main = Math.round(performance.now()); snap('T2_main'); }
      else if (href.includes('bootstrap.min.css')) { S.css.bootstrap = Math.round(performance.now()); snap('T3_bootstrap'); }
    });
  });

  document.addEventListener('DOMContentLoaded', () => snap('T0_dom'));
  window.addEventListener('load', () => snap('T4_load'));

  let n = 0;
  const poll = () => { snap('poll_' + n); if (++n < 100) requestAnimationFrame(poll); };
  requestAnimationFrame(poll);
})();
""" % json.dumps(PROPS)


async def run_trace(inject_css=None, extra_css=None, runs=1):
    css_body = PATCH_CSS.read_text()
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for run in range(runs):
            ctx = await browser.new_context(viewport={"width": 390, "height": 844})
            page = await ctx.new_page()
            await page.add_init_script(TRACE_JS)
            if extra_css:
                esc = json.dumps(extra_css)
                await page.add_init_script(
                    f"(()=>{{const s=document.createElement('style');s.textContent={esc};document.documentElement.appendChild(s);}})();"
                )

            async def handler(route):
                if inject_css and "home-critical.css" in route.request.url:
                    await route.fulfill(status=200, content_type="text/css", body=css_body)
                else:
                    await route.continue_()

            if inject_css:
                await page.route("**/*", handler)

            await page.goto(PROD, wait_until="load", timeout=90000)
            await page.wait_for_timeout(5000)
            data = await page.evaluate("() => window.__s4 || { samples: [], shifts: [], css: {} }")
            cls = sum(x["value"] for x in data.get("shifts", []))
            s4_cls = sum(
                x["value"] for x in data.get("shifts", [])
                if any("shape-4" in (s.get("node") or "") for s in x.get("sources", []))
            )
            shape_shifts = [
                x for x in data.get("shifts", [])
                if any("shape-4" in (s.get("node") or "") for s in x.get("sources", []))
            ]
            results.append({
                "run": run + 1,
                "cls": round(cls, 4),
                "shape4_cls": round(s4_cls, 4),
                "shape_shifts": shape_shifts,
                "cssTiming": data.get("css", {}),
                "samples_near_shift": [
                    s for s in data.get("samples", [])
                    if s["label"].startswith("shift_shape4") or s["label"] in ("T1_critical", "T2_main", "T3_bootstrap", "T4_load")
                ],
            })
            await ctx.close()
        await browser.close()
    return results


async def ab_variant(label, extra_css, runs=5):
    rows = await run_trace(inject_css=True, extra_css=extra_css, runs=runs)
    cls_vals = [r["cls"] for r in rows]
    s4_vals = [r["shape4_cls"] for r in rows]
    return {
        "label": label,
        "runs": rows,
        "median_cls": statistics.median(cls_vals),
        "median_shape4_cls": statistics.median(s4_vals),
    }


async def main():
    report = {"generatedAt": time.time()}

    # Deep trace 3 runs
    report["trace"] = await run_trace(inject_css=True, runs=3)

    # A/B variants
    variants = [
        ("baseline", None),
        ("animation_none", ".banner1__shapes-shape-4 { animation: none !important; }"),
        ("transition_none", ".banner1__shapes-shape-4 { transition: none !important; }"),
        ("filter_none", ".banner1__shapes-shape-4 { filter: none !important; }"),
        ("transform_none", ".banner1__shapes-shape-4 { transform: none !important; }"),
        ("visibility_hidden", ".banner1__shapes-shape-4 { visibility: hidden !important; }"),
        (
            "contain_strict",
            ".banner1__shapes-shape-4 { contain: strict !important; will-change: transform; transform: translateZ(0); }",
        ),
        (
            "layer_promote",
            ".banner1__shapes-shape-4 { transform: translateZ(0); will-change: transform; backface-visibility: hidden; }",
        ),
    ]
    report["ab"] = {}
    for label, css in variants:
        report["ab"][label] = await ab_variant(label, css, runs=5)

    OUT.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: {"median_cls": v["median_cls"], "median_shape4": v["median_shape4_cls"]} for k, v in report["ab"].items()}, indent=2))
    print(f"Full: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
