#!/usr/bin/env python3
"""Production diagnosis: document composite, CSS timing, banner shapes CLS."""
import asyncio
import json
import statistics
import time
from collections import Counter, defaultdict

from playwright.async_api import async_playwright

PROD = "https://www.smartcontrolbrasil.com.br/"
OUT = "/tmp/smart360-document-composite-diagnosis.json"

BASE_INSTRUMENT = """
(() => {
  window.__docDiag = {
    css: [],
    h1: [],
    shapes: [],
    layoutShift: [],
    longTasks: [],
    paints: { fcp: null, lcp: null },
    dom: {},
  };
  const d = window.__docDiag;

  function ts() { return Math.round(performance.now()); }

  document.addEventListener('DOMContentLoaded', () => { d.domContentLoaded = ts(); });
  window.addEventListener('load', () => { d.load = ts(); });

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.name === 'first-contentful-paint') d.paints.fcp = Math.round(e.startTime);
      }
    }).observe({ type: 'paint', buffered: true });
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length) {
        const last = entries[entries.length - 1];
        d.paints.lcp = Math.round(last.startTime);
        d.paints.lcpElement = last.element ? (last.element.tagName + '.' + (last.element.className || '').toString().slice(0,80)) : null;
      }
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.duration < 50) continue;
        d.longTasks.push({ start: Math.round(e.startTime), duration: Math.round(e.duration), name: e.name || 'self' });
      }
    }).observe({ type: 'longtask', buffered: true });
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (!e.hadRecentInput) {
          d.layoutShift.push({
            t: Math.round(e.startTime),
            value: e.value,
            sources: (e.sources || []).map((s) => ({
              node: s.node ? (s.node.tagName + '.' + (s.node.className || '').toString().slice(0,80)) : '',
              prev: s.previousRect ? { x: s.previousRect.x, y: s.previousRect.y, w: s.previousRect.width, h: s.previousRect.height } : null,
              curr: s.currentRect ? { x: s.currentRect.x, y: s.currentRect.y, w: s.currentRect.width, h: s.currentRect.height } : null,
            })),
          });
        }
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}

  const snapH1 = () => {
    const h1 = document.querySelector('.banner-heading__wrapper-title');
    if (!h1) return;
    const cs = getComputedStyle(h1);
    const r = h1.getBoundingClientRect();
    d.h1.push({
      t: ts(),
      fontSize: cs.fontSize,
      lineHeight: cs.lineHeight,
      fontWeight: cs.fontWeight,
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top),
      left: Math.round(r.left),
    });
  };

  const snapShapes = () => {
    const root = document.querySelector('.banner1__shapes');
    if (!root) return;
    const rr = root.getBoundingClientRect();
    const entry = { t: ts(), root: { w: Math.round(rr.width), h: Math.round(rr.height), top: Math.round(rr.top), left: Math.round(rr.left) }, children: [] };
    root.querySelectorAll('[class*="banner1__shapes-shape"]').forEach((el) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      entry.children.push({
        cls: (el.className || '').toString(),
        w: Math.round(r.width),
        h: Math.round(r.height),
        top: Math.round(r.top),
        left: Math.round(r.left),
        pos: cs.position,
        transform: cs.transform,
        bg: cs.backgroundImage !== 'none' ? 'yes' : 'no',
      });
    });
    d.shapes.push(entry);
  };

  const cssLinks = [...document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"][as="style"]')];
  cssLinks.forEach((link) => {
    link.addEventListener('load', () => {
      d.css.push({ t: ts(), href: link.href, rel: link.rel, media: link.media || 'all' });
      snapH1();
      snapShapes();
    });
  });

  const obs = new MutationObserver(() => { snapH1(); snapShapes(); });
  const area = document.querySelector('.banner1__area');
  if (area) obs.observe(area, { attributes: true, subtree: true, attributeFilter: ['style', 'class'] });

  let n = 0;
  const poll = () => {
    snapH1();
    snapShapes();
    if (++n < 80) requestAnimationFrame(poll);
  };
  requestAnimationFrame(poll);

  window.addEventListener('load', () => {
    d.dom = {
      total: document.getElementsByTagName('*').length,
      inViewport: [...document.querySelectorAll('body *')].filter((el) => {
        const r = el.getBoundingClientRect();
        return r.bottom > 0 && r.top < innerHeight && r.width > 0 && r.height > 0;
      }).length,
    };
  });
})();
"""


async def run_scenario(page, label, inject_css=None, hide_shapes=False, block_main=False, block_bootstrap=False):
    await page.add_init_script(BASE_INSTRUMENT)
    if inject_css:
        await page.add_init_script(f"""
        (() => {{
          const s = document.createElement('style');
          s.textContent = `{inject_css}`;
          document.documentElement.appendChild(s);
        }})();
        """)
    if hide_shapes:
        await page.add_init_script("""
        (() => {
          const s = document.createElement('style');
          s.textContent = '.banner1__shapes { visibility: hidden !important; }';
          document.documentElement.appendChild(s);
        })();
        """)

    async def route_handler(route):
        url = route.request.url
        if block_main and "main.css" in url:
            await route.abort()
            return
        if block_bootstrap and "bootstrap.min.css" in url:
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", route_handler)
    await page.goto(PROD, wait_until="load", timeout=60000)
    await page.wait_for_timeout(5000)

    data = await page.evaluate("() => window.__docDiag")
    cls_total = sum(x["value"] for x in data.get("layoutShift", []))
    cls_shapes = sum(
        x["value"]
        for x in data.get("layoutShift", [])
        if any("banner1__shapes" in (s.get("node") or "") for s in x.get("sources", []))
    )
    top_cls = sorted(
        ((s.get("node") or "?", x["value"]) for x in data.get("layoutShift", []) for s in x.get("sources", [])),
        key=lambda t: t[1],
        reverse=True,
    )[:8]

    return {
        "label": label,
        "fcp": data.get("paints", {}).get("fcp"),
        "lcp": data.get("paints", {}).get("lcp"),
        "lcpElement": data.get("paints", {}).get("lcpElement"),
        "cls_total": round(cls_total, 4),
        "cls_shapes": round(cls_shapes, 4),
        "top_cls_sources": top_cls,
        "longTasks": data.get("longTasks", [])[:15],
        "longTaskTotalMs": sum(t["duration"] for t in data.get("longTasks", [])),
        "cssEvents": data.get("css", []),
        "h1Timeline": data.get("h1", [])[:20],
        "shapesTimeline": data.get("shapes", [])[:8],
        "dom": data.get("dom", {}),
    }


async def main():
    scenarios = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def run(label, viewport, **kwargs):
            ctx = await browser.new_context(viewport=viewport, user_agent=(
                "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
            ) if viewport["width"] < 800 else (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ))
            page = await ctx.new_page()
            result = await run_scenario(page, label, **kwargs)
            await ctx.close()
            return result

        mobile = {"width": 390, "height": 844}
        desktop = {"width": 1440, "height": 900}

        scenarios.append(await run("mobile_baseline", mobile))
        scenarios.append(await run("desktop_baseline", desktop))
        scenarios.append(await run("desktop_hide_shapes", desktop, hide_shapes=True))
        scenarios.append(await run("mobile_block_main", mobile, block_main=True))
        scenarios.append(await run("mobile_block_bootstrap", mobile, block_bootstrap=True))
        scenarios.append(await run("mobile_block_both", mobile, block_main=True, block_bootstrap=True))
        scenarios.append(await run("desktop_block_main", desktop, block_main=True))
        scenarios.append(await run("desktop_block_bootstrap", desktop, block_bootstrap=True))

        shape_critical = """
.banner1__area { overflow: hidden; isolation: isolate; min-height: 720px; }
.banner1__shapes { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: hidden; contain: layout paint; }
.banner1__shapes-shape-8 { contain: strict; }
"""
        scenarios.append(await run("desktop_shape_contain", desktop, inject_css=shape_critical))
        scenarios.append(await run("mobile_shape_contain", mobile, inject_css=shape_critical))

        cv_css = """
main > section:not(.banner-before) { content-visibility: auto; contain-intrinsic-size: auto 500px; }
"""
        scenarios.append(await run("mobile_content_visibility", mobile, inject_css=cv_css))

        await browser.close()

    report = {"scenarios": scenarios, "generatedAt": time.time()}
    with open(OUT, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
