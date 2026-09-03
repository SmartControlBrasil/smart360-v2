#!/usr/bin/env python3
"""Final validation: fixed UI critical CSS patch (CLS / document composite)."""
import asyncio
import json
import statistics
import time
from pathlib import Path

from playwright.async_api import async_playwright

PROD = "https://www.smartcontrolbrasil.com.br/"
LOCAL = "http://127.0.0.1:8013/"
PATCH_CSS = Path(__file__).resolve().parents[1] / "static/institutional/css/home-critical.css"
OUT = Path("/tmp/smart360-fixed-ui-critical-validation.json")

GEOM_KEYS = (
    "position", "top", "right", "bottom", "left", "width", "height",
    "z-index", "display", "visibility", "opacity", "transform", "overflow", "pointer-events",
)

INSTRUMENT = """
(() => {
  window.__v = {
    marks: [],
    shifts: [],
    paints: { fcp: null, lcp: null, lcpElement: null },
    css: { critical: null, main: null, bootstrap: null },
  };
  const v = window.__v;
  const ts = () => Math.round(performance.now());

  const mark = (label) => {
    const h = document.querySelector('.header-1');
    const h1 = document.querySelector('.banner-heading__wrapper-title');
    const back = document.querySelector('.backtotop-wrap');
    const wa = document.querySelector('.whatsapp-float');
    const pop = document.querySelector('#popup-search-box');
    const pick = (el) => {
      if (!el) return null;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const o = { rectTop: Math.round(r.top), rectH: Math.round(r.height), rectW: Math.round(r.width) };
      for (const k of %s) o[k] = cs[k];
      return o;
    };
    v.marks.push({
      label,
      t: ts(),
      bodyScrollH: document.body.scrollHeight,
      docScrollH: document.documentElement.scrollHeight,
      headerTop: h ? Math.round(h.getBoundingClientRect().top) : null,
      h1Top: h1 ? Math.round(h1.getBoundingClientRect().top) : null,
      h1H: h1 ? Math.round(h1.getBoundingClientRect().height) : null,
      h1W: h1 ? Math.round(h1.getBoundingClientRect().width) : null,
      backtotop: pick(back),
      whatsapp: pick(wa),
      popup: pick(pop),
    });
  };

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.name === 'first-contentful-paint') v.paints.fcp = Math.round(e.startTime);
      }
    }).observe({ type: 'paint', buffered: true });
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length) {
        const last = entries[entries.length - 1];
        v.paints.lcp = Math.round(last.startTime);
        v.paints.lcpElement = last.element
          ? last.element.tagName + '.' + (last.element.className || '').toString().slice(0, 80)
          : null;
      }
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.hadRecentInput) continue;
        v.shifts.push({
          t: Math.round(e.startTime),
          value: e.value,
          sources: (e.sources || []).map((s) => ({
            node: s.node ? (s.node.tagName + '.' + (s.node.className || '').toString().slice(0, 80)) : '',
            prev: s.previousRect ? {
              x: s.previousRect.x, y: s.previousRect.y,
              w: s.previousRect.width, h: s.previousRect.height,
            } : null,
            curr: s.currentRect ? {
              x: s.currentRect.x, y: s.currentRect.y,
              w: s.currentRect.width, h: s.currentRect.height,
            } : null,
          })),
        });
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}

  document.addEventListener('DOMContentLoaded', () => mark('T0_dom'));
  const links = [...document.querySelectorAll('link')];
  links.forEach((link) => {
    link.addEventListener('load', () => {
      const href = link.href || '';
      if (href.includes('home-critical.css')) {
        v.css.critical = ts();
        mark('T1_critical');
      } else if (href.includes('main.css')) {
        v.css.main = ts();
        mark('T2_main');
      } else if (href.includes('bootstrap.min.css')) {
        v.css.bootstrap = ts();
        mark('T3_bootstrap');
      }
    });
  });
  window.addEventListener('load', () => mark('T4_load'));
  mark('T_init');
})();
""" % json.dumps(list(GEOM_KEYS))

GLOBAL_SCAN = """
() => {
  const header = document.querySelector('.header-1');
  if (!header) return { beforeHeader: [] };
  const out = [];
  let node = document.body.firstElementChild;
  while (node && !node.contains(header)) {
    if (node.id === 'preloader' || node.matches('.header-1')) {
      node = node.nextElementSibling;
      continue;
    }
    const cs = getComputedStyle(node);
    const r = node.getBoundingClientRect();
    out.push({
      tag: node.tagName,
      id: node.id || '',
      cls: (node.className || '').toString().slice(0, 80),
      position: cs.position,
      display: cs.display,
      rectTop: Math.round(r.top),
      rectH: Math.round(r.height),
      offsetH: node.offsetHeight,
      inFlow: cs.position === 'static' || cs.position === 'relative',
    });
    node = node.nextElementSibling;
  }
  return { beforeHeader: out };
}
"""


async def run_once(page, url, patch_css=None, viewport=None):
    css_body = patch_css.read_text() if patch_css else None

    if css_body:
        async def handler(route):
            if "home-critical.css" in route.request.url:
                await route.fulfill(status=200, content_type="text/css", body=css_body)
            else:
                await route.continue_()

        await page.route("**/*", handler)

    await page.goto(url, wait_until="load", timeout=90000)
    await page.wait_for_timeout(5000)
    data = await page.evaluate("() => window.__v")
    scan = await page.evaluate(GLOBAL_SCAN)
    cls_total = sum(x["value"] for x in data.get("shifts", []))
    top_sources = sorted(
        (
            (s.get("node") or "?", x["value"])
            for x in data.get("shifts", [])
            for s in x.get("sources", [])
        ),
        key=lambda t: t[1],
        reverse=True,
    )[:10]
    marks = data.get("marks", [])
    header_tops = [m["headerTop"] for m in marks if m.get("headerTop") is not None]
    h1_tops = [m["h1Top"] for m in marks if m.get("h1Top") is not None]
    return {
        "cls": round(cls_total, 4),
        "shifts": data.get("shifts", []),
        "top_sources": top_sources,
        "fcp": data.get("paints", {}).get("fcp"),
        "lcp": data.get("paints", {}).get("lcp"),
        "lcpElement": data.get("paints", {}).get("lcpElement"),
        "marks": marks,
        "cssTiming": data.get("css", {}),
        "headerTopRange": {
            "min": min(header_tops) if header_tops else None,
            "max": max(header_tops) if header_tops else None,
            "delta": (max(header_tops) - min(header_tops)) if header_tops else None,
        },
        "h1TopRange": {
            "min": min(h1_tops) if h1_tops else None,
            "max": max(h1_tops) if h1_tops else None,
            "delta": (max(h1_tops) - min(h1_tops)) if h1_tops else None,
        },
        "docHeightRange": {
            "bodyMin": min(m["bodyScrollH"] for m in marks),
            "bodyMax": max(m["bodyScrollH"] for m in marks),
            "docMin": min(m["docScrollH"] for m in marks),
            "docMax": max(m["docScrollH"] for m in marks),
        },
        "globalScan": scan,
    }


async def run_suite(label, url, viewport, runs=3, patch=False):
    rows = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for i in range(runs):
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
            await page.add_init_script(INSTRUMENT)
            row = await run_once(
                page,
                url,
                patch_css=PATCH_CSS if patch else None,
                viewport=viewport,
            )
            row["run"] = i + 1
            rows.append(row)
            await ctx.close()
        await browser.close()
    cls_vals = [r["cls"] for r in rows]
    return {
        "label": label,
        "runs": rows,
        "median": {
            "cls": statistics.median(cls_vals),
            "fcp": statistics.median([r["fcp"] or 0 for r in rows]),
            "lcp": statistics.median([r["lcp"] or 0 for r in rows]),
            "headerDelta": statistics.median([r["headerTopRange"]["delta"] or 0 for r in rows]),
            "h1Delta": statistics.median([r["h1TopRange"]["delta"] or 0 for r in rows]),
        },
    }


async def main():
    report = {"generatedAt": time.time(), "patchCssBytes": PATCH_CSS.stat().st_size}
    viewports = {
        "mobile_390": {"width": 390, "height": 844},
        "mobile_430": {"width": 430, "height": 932},
        "desktop_1366": {"width": 1366, "height": 768},
        "desktop_1440": {"width": 1440, "height": 900},
        "desktop_1920": {"width": 1920, "height": 1080},
    }

    # Production baseline vs patch (3 runs each, primary viewports)
    report["production_mobile_baseline_3"] = await run_suite(
        "prod_mobile_baseline", PROD, viewports["mobile_390"], runs=3, patch=False
    )
    report["production_mobile_patch_3"] = await run_suite(
        "prod_mobile_patch", PROD, viewports["mobile_390"], runs=3, patch=True
    )
    report["production_desktop_baseline_3"] = await run_suite(
        "prod_desktop_baseline", PROD, viewports["desktop_1440"], runs=3, patch=False
    )
    report["production_desktop_patch_3"] = await run_suite(
        "prod_desktop_patch", PROD, viewports["desktop_1440"], runs=3, patch=True
    )

    # Local clean with patch served natively
    local = {}
    for key, vp in viewports.items():
        local[key] = await run_suite(f"local_{key}", LOCAL, vp, runs=1, patch=False)
    report["local_patch"] = local

    OUT.write_text(json.dumps(report, indent=2, default=str))
    summary = {
        "prod_mobile_baseline_cls_median": report["production_mobile_baseline_3"]["median"]["cls"],
        "prod_mobile_patch_cls_median": report["production_mobile_patch_3"]["median"]["cls"],
        "prod_desktop_baseline_cls_median": report["production_desktop_baseline_3"]["median"]["cls"],
        "prod_desktop_patch_cls_median": report["production_desktop_patch_3"]["median"]["cls"],
        "prod_mobile_patch_header_delta_median": report["production_mobile_patch_3"]["median"]["headerDelta"],
        "prod_mobile_patch_h1_delta_median": report["production_mobile_patch_3"]["median"]["h1Delta"],
    }
    print(json.dumps(summary, indent=2))
    print(f"Full report: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
