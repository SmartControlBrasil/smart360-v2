#!/usr/bin/env python3
"""Timeline validation: GSAP init must happen after LCP on home mobile."""
import asyncio
import json
import statistics
from pathlib import Path

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8012"
OUT = Path("/tmp/smart360-gsap-lcp-gate.json")

INIT = """
(() => {
  window.__tl = {
    fcp: null,
    lcp: null,
    gsapInit: null,
    stCreate: null,
    stRefresh: null,
    getBoundsBeforeLcp: 0,
    getBoundsAfterLcp: 0,
    initCount: 0,
    refreshCount: 0,
  };
  const tl = window.__tl;
  const ts = () => Math.round(performance.now());

  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) {
      if (e.name === 'first-contentful-paint') tl.fcp = Math.round(e.startTime);
    }
  }).observe({ type: 'paint', buffered: true });

  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) {
      tl.lcp = Math.round(e.startTime);
    }
  }).observe({ type: 'largest-contentful-paint', buffered: true });

  const gbcr = Element.prototype.getBoundingClientRect;
  Element.prototype.getBoundingClientRect = function() {
    const stack = (new Error()).stack || '';
    if (!stack.includes('_getBounds')) return gbcr.call(this);
    const t = ts();
    if (tl.lcp == null || t <= tl.lcp + 50) tl.getBoundsBeforeLcp += 1;
    else tl.getBoundsAfterLcp += 1;
    return gbcr.call(this);
  };

  const poll = setInterval(() => {
    if (window.ScrollTrigger && window.ScrollTrigger.create && !window.ScrollTrigger.create.__patched) {
      const origCreate = window.ScrollTrigger.create;
      window.ScrollTrigger.create = function() {
        if (tl.stCreate == null) tl.stCreate = ts();
        return origCreate.apply(this, arguments);
      };
      window.ScrollTrigger.create.__patched = true;
    }
    if (window.ScrollTrigger && window.ScrollTrigger.refresh && !window.ScrollTrigger.refresh.__patched) {
      const origRefresh = window.ScrollTrigger.refresh;
      window.ScrollTrigger.refresh = function() {
        tl.refreshCount += 1;
        if (tl.stRefresh == null) tl.stRefresh = ts();
        return origRefresh.apply(this, arguments);
      };
      window.ScrollTrigger.refresh.__patched = true;
    }
    if (window.gsap && document.readyState === 'complete') {
      /* noop */
    }
  }, 5);

  window.addEventListener('load', () => {
    const mark = () => {
      if (window.ScrollTrigger && window.ScrollTrigger.getAll().length > 0 && tl.gsapInit == null) {
        tl.gsapInit = ts();
        tl.initCount = 1;
      }
    };
    const id = setInterval(() => {
      mark();
      if (tl.gsapInit != null) clearInterval(id);
    }, 10);
    setTimeout(() => clearInterval(id), 8000);
  });
})();
"""


async def snapshot(page, wait_ms=6000):
    await page.wait_for_timeout(wait_ms)
    return await page.evaluate("""
      () => {
        const tl = window.__tl || {};
        const st = window.ScrollTrigger ? window.ScrollTrigger.getAll().length : 0;
        return {
          fcp: tl.fcp,
          lcp: tl.lcp,
          gsapInit: tl.gsapInit,
          stCreate: tl.stCreate,
          stRefresh: tl.stRefresh,
          getBoundsBeforeLcp: tl.getBoundsBeforeLcp,
          getBoundsAfterLcp: tl.getBoundsAfterLcp,
          refreshCount: tl.refreshCount,
          scrollTriggers: st,
        };
      }
    """)


async def run_case(browser, name, url, viewport, extra_init=None, early_scroll=False):
    ctx = await browser.new_context(viewport=viewport)
    page = await ctx.new_page()
    await page.add_init_script(INIT)
    if extra_init:
        await page.add_init_script(extra_init)
    await page.goto(url, wait_until="load", timeout=60000)
    if early_scroll:
        await page.evaluate("window.scrollBy(0, 150)")
        await page.wait_for_timeout(200)
    data = await snapshot(page)
    data["name"] = name
    if data["lcp"] and data["gsapInit"]:
        data["orderOk"] = data["gsapInit"] >= data["lcp"]
    elif name.startswith("home_mobile"):
        data["orderOk"] = data["getBoundsBeforeLcp"] == 0
    else:
        data["orderOk"] = data["scrollTriggers"] > 0
    await ctx.close()
    return data


async def main():
    results = {"scenarios": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        cases = [
            ("home_mobile", f"{BASE}/", {"width": 390, "height": 844}),
            ("home_mobile_early_scroll", f"{BASE}/", {"width": 390, "height": 844}),
            ("home_mobile_no_po", f"{BASE}/", {"width": 390, "height": 844}),
            ("desktop_home", f"{BASE}/", {"width": 1440, "height": 900}),
            ("internal_empresa", f"{BASE}/empresa/", {"width": 390, "height": 844}),
            ("internal_servicos", f"{BASE}/servicos/", {"width": 390, "height": 844}),
            ("internal_xyron", f"{BASE}/xyron/", {"width": 390, "height": 844}),
            ("internal_littlebot", f"{BASE}/xyron/littlebot/", {"width": 390, "height": 844}),
            ("internal_mitsubishi", f"{BASE}/mitsubishi-automacao-industrial/", {"width": 390, "height": 844}),
        ]
        for name, url, vp in cases:
            extra = "window.PerformanceObserver = undefined;" if name == "home_mobile_no_po" else None
            scroll = name == "home_mobile_early_scroll"
            results["scenarios"].append(
                await run_case(browser, name, url, vp, extra, scroll)
            )

        # mobile menu before gsap
        ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()
        await page.goto(f"{BASE}/", wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        menu = await page.locator("a.meanmenu-reveal").is_visible()
        results["mobile_menu"] = {"meanmenuVisibleAt500ms": menu}
        await ctx.close()
        await browser.close()

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
