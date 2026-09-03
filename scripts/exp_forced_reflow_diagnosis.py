#!/usr/bin/env python3
"""Production forced-reflow / LCP diagnosis for Smart360 home (read-only)."""
import asyncio
import json
import statistics
import time
from pathlib import Path

from playwright.async_api import async_playwright

PROD = "https://www.smartcontrolbrasil.com.br/"
OUT = Path("/tmp/smart360-reflow-diagnosis.json")

INSTRUMENT = """
(() => {
  const diag = {
    t0: performance.timeOrigin,
    layoutReads: [],
    styleWrites: [],
    h1Timeline: [],
    preloaderTimeline: [],
    lcp: null,
    fcp: null,
    nav: null,
  };
  window.__smart360Diag = diag;

  function ts() { return Math.round(performance.now()); }
  function stack() {
    try {
      const s = new Error().stack || '';
      return s.split('\\n').slice(2, 8).map(l => l.trim()).join(' | ');
    } catch (e) { return ''; }
  }

  const readProps = ['offsetWidth','offsetHeight','clientWidth','clientHeight','scrollWidth','scrollHeight','offsetTop','offsetLeft'];
  readProps.forEach((prop) => {
    const desc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop);
    if (!desc || !desc.get) return;
    Object.defineProperty(HTMLElement.prototype, prop, {
      configurable: true,
      get: function() {
        diag.layoutReads.push({t: ts(), prop, tag: this.tagName, id: this.id||'', cls: (this.className||'').toString().slice(0,60), stack: stack()});
        return desc.get.call(this);
      }
    });
  });

  const gbcr = Element.prototype.getBoundingClientRect;
  Element.prototype.getBoundingClientRect = function() {
    diag.layoutReads.push({t: ts(), prop: 'getBoundingClientRect', tag: this.tagName, id: this.id||'', cls: (this.className||'').toString().slice(0,60), stack: stack()});
    return gbcr.call(this);
  };

  const gcs = window.getComputedStyle;
  window.getComputedStyle = function(el, pseudo) {
    diag.layoutReads.push({t: ts(), prop: 'getComputedStyle', tag: el && el.tagName, id: el && el.id || '', cls: el && (el.className||'').toString().slice(0,60), stack: stack()});
    return gcs.call(window, el, pseudo);
  };

  const origSet = CSSStyleDeclaration.prototype.setProperty;
  CSSStyleDeclaration.prototype.setProperty = function(name, value, priority) {
    diag.styleWrites.push({t: ts(), prop: name, stack: stack()});
    return origSet.call(this, name, value, priority);
  };

  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.name === 'first-contentful-paint') diag.fcp = Math.round(e.startTime);
      }
    }).observe({type: 'paint', buffered: true});
  } catch (e) {}

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      if (entries.length) {
        const last = entries[entries.length - 1];
        diag.lcp = Math.round(last.startTime);
        diag.lcpElement = last.element ? last.element.tagName + '.' + String(last.element.className||'').trim().split(/\\s+/)[0] : null;
      }
    }).observe({type: 'largest-contentful-paint', buffered: true});
  } catch (e) {}

  function sampleH1() {
    const h1 = document.querySelector('h1.banner-heading__wrapper-title');
    const pre = document.getElementById('preloader');
    if (h1) {
      const r = h1.getBoundingClientRect();
      const s = getComputedStyle(h1);
      diag.h1Timeline.push({t: ts(), w: Math.round(r.width), h: Math.round(r.height), op: s.opacity, vis: s.visibility, fs: s.fontSize});
    }
    if (pre) {
      const s = getComputedStyle(pre);
      diag.preloaderTimeline.push({t: ts(), op: s.opacity, vis: s.visibility, display: s.display, inDom: !!pre.parentNode});
    }
  }

  const iv = setInterval(sampleH1, 100);
  window.addEventListener('load', () => {
    const nav = performance.getEntriesByType('navigation')[0];
    if (nav) diag.nav = {ttfb: Math.round(nav.responseStart), dcl: Math.round(nav.domContentLoadedEventEnd), load: Math.round(nav.loadEventEnd)};
    setTimeout(() => clearInterval(iv), 8000);
  });
})();
"""


async def run_scenario(page, label, block_patterns=None, inject_css=None, block_gtag=False):
    block_patterns = block_patterns or []
    metrics = {"label": label}

    async def route_handler(route):
        url = route.request.url
        if block_gtag and ("googletagmanager" in url or "google-analytics" in url):
            await route.abort()
            return
        for pat in block_patterns:
            if pat in url:
                await route.abort()
                return
        await route.continue_()

    await page.route("**/*", route_handler)
    if inject_css:
        await page.add_init_script(
            f"window.addEventListener('DOMContentLoaded',()=>{{const s=document.createElement('style');s.textContent={json.dumps(inject_css)};document.head.appendChild(s);}});"
        )
    await page.add_init_script(INSTRUMENT)

    t0 = time.time()
    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(PROD, wait_until="load", timeout=120000)
    await page.wait_for_timeout(6000)
    metrics["wall_ms"] = round((time.time() - t0) * 1000)

    diag = await page.evaluate("() => window.__smart360Diag || {}")
    metrics.update({
        "fcp": diag.get("fcp"),
        "lcp": diag.get("lcp"),
        "lcpElement": diag.get("lcpElement"),
        "nav": diag.get("nav"),
        "layoutReads": len(diag.get("layoutReads") or []),
        "styleWrites": len(diag.get("styleWrites") or []),
        "h1Timeline": diag.get("h1Timeline") or [],
        "preloaderTimeline": diag.get("preloaderTimeline") or [],
    })

    reads = diag.get("layoutReads") or []
    by_stack = {}
    for r in reads:
        key = (r.get("stack") or "unknown")[:120]
        by_stack[key] = by_stack.get(key, 0) + 1
    metrics["topLayoutReadStacks"] = sorted(
        [{"stack": k, "count": v} for k, v in by_stack.items()],
        key=lambda x: -x["count"],
    )[:12]

    early_reads = [r for r in reads if r.get("t", 99999) <= (metrics.get("lcp") or 5000)]
    metrics["layoutReadsBeforeLcp"] = len(early_reads)

    dom = await page.evaluate("""() => {
      const fold = window.innerHeight;
      let total=0, above=0, below=0;
      for (const el of document.querySelectorAll('body *')) {
        total++;
        const r = el.getBoundingClientRect();
        if (r.bottom <= 0 || r.top >= fold) below++; else if (r.width>0 && r.height>0) above++;
      }
      return {total, above, below, fold};
    }""")
    metrics["dom"] = dom

    cls = await page.evaluate("""() => {
      let cls=0;
      try {
        new PerformanceObserver(l=>{for(const e of l.getEntries()) if(!e.hadRecentInput) cls+=e.value}).observe({type:'layout-shift',buffered:true});
      } catch(e) {}
      return cls;
    }""")
    metrics["cls"] = cls

    await page.unroute("**/*")
    return metrics


async def cdp_trace_sample(page):
    cdp = await page.context.new_cdp_session(page)
    await cdp.send("Performance.enable")
    await page.add_init_script(INSTRUMENT)
    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(PROD, wait_until="load", timeout=120000)
    await page.wait_for_timeout(5500)
    perf = await cdp.send("Performance.getMetrics")
    diag = await page.evaluate("() => window.__smart360Diag || {}")
    await cdp.detach()
    metric_map = {m["name"]: m["value"] for m in perf.get("metrics", [])}
    return {"performanceMetrics": metric_map, "diag": {
        "fcp": diag.get("fcp"), "lcp": diag.get("lcp"), "lcpElement": diag.get("lcpElement"),
        "nav": diag.get("nav"), "layoutReads": len(diag.get("layoutReads") or []),
        "preloaderTimeline": diag.get("preloaderTimeline") or [],
        "h1Timeline": diag.get("h1Timeline") or [],
    }}


async def main():
    result = {"baseline_prod_pagespeed": {
        "mobile": {"perf": 83, "fcp": 1200, "lcp": 4300, "tbt": 40, "cls": 0.033, "si": 4300},
        "desktop": {"perf": 96, "fcp": 700, "lcp": 1000, "tbt": 10, "cls": 0.029, "si": 1600},
        "mainThread": {"other": 1580, "styleLayout": 555, "scriptEval": 370, "rendering": 208},
    }}

    scenarios = [
        ("A_baseline", [], None, False),
        ("B_no_scrolltrigger", ["ScrollTrigger.js"], None, False),
        ("C_no_gsap", ["gsap.js", "ScrollTrigger.js", "SplitText.js"], None, False),
        ("D_no_meanmenu", ["meanmenu.min.js"], None, False),
        ("E_no_wow_swiper", ["wow.js", "swiper.min.js"], None, False),
        ("F_no_hero_anim", [], "*{animation:none!important;transition:none!important}", False),
        ("G_content_visibility", [], "section:not(.banner-before){content-visibility:auto;contain-intrinsic-size:1px 800px}", False),
        ("H_no_gtag", [], None, True),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-cache"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 11; moto g power (2022)) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
        )

        result["ab"] = {}
        for label, blocks, css, no_gtag in scenarios:
            page = await ctx.new_page()
            result["ab"][label] = await run_scenario(page, label, blocks, css, no_gtag)
            await page.close()

        page = await ctx.new_page()
        result["cdp"] = await cdp_trace_sample(page)
        await page.close()
        await browser.close()

    # Summarize H1 timeline from baseline
    base = result["ab"]["A_baseline"]
    h1t = base.get("h1Timeline") or []
    visible = [x for x in h1t if float(x.get("op", 0)) > 0 and x.get("vis") != "hidden" and x.get("w", 0) > 0]
    result["h1_analysis"] = {
        "firstVisibleSampleMs": visible[0]["t"] if visible else None,
        "lcpMs": base.get("lcp"),
        "fcpMs": base.get("fcp"),
        "samples": len(h1t),
    }

    pre = base.get("preloaderTimeline") or []
    gone = next((x for x in pre if float(x.get("op", 1)) == 0 or x.get("vis") == "hidden"), None)
    result["preloader_analysis"] = {
        "firstHiddenMs": gone["t"] if gone else None,
        "samples": pre[:20],
    }

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "out": str(OUT),
        "ab_summary": {k: {"lcp": v.get("lcp"), "fcp": v.get("fcp"), "layoutReads": v.get("layoutReads"), "layoutReadsBeforeLcp": v.get("layoutReadsBeforeLcp"), "cls": v.get("cls")} for k, v in result["ab"].items()},
        "h1": result["h1_analysis"],
        "preloader": result["preloader_analysis"],
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
