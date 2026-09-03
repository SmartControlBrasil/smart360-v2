#!/usr/bin/env python3
"""Validate HOME images load after asset optimization."""
import json
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
TARGETS = [
    "/static/institutional/imgs/shapes/home-1-bg-shape.png",
    "/static/institutional/imgs/images/header/logo-cores-03.webp",
    "/static/institutional/imgs/shapes/hero-1-shape-2.png",
    "/static/institutional/imgs/images/pricing-img-1.png",
    "/static/institutional/imgs/home/recepicionista-atendento.webp",
]

AUDIT_JS = """
() => {
  const checks = {};
  const heroBg = document.querySelector('.banner1__shapes-shape-8');
  if (heroBg) {
    const bg = getComputedStyle(heroBg).backgroundImage;
    checks.heroBackground = {
      hasUrl: bg.includes('home-1-bg-shape'),
      backgroundImage: bg.slice(0, 120)
    };
  }
  const logo = document.querySelector('header img[src*="logo-cores-03"]');
  if (logo) {
    const r = logo.getBoundingClientRect();
    checks.headerLogo = {
      naturalWidth: logo.naturalWidth,
      naturalHeight: logo.naturalHeight,
      displayWidth: r.width,
      displayHeight: r.height,
      complete: logo.complete
    };
  }
  const heroShape = document.querySelector('img[src*="hero-1-shape-2"]');
  if (heroShape) {
    const r = heroShape.getBoundingClientRect();
    checks.heroShape2 = {
      naturalWidth: heroShape.naturalWidth,
      naturalHeight: heroShape.naturalHeight,
      displayWidth: r.width,
      displayHeight: r.height,
      complete: heroShape.complete
    };
  }
  const robot = document.querySelector('img[src*="recepicionista-atendento"]');
  if (robot) {
    const r = robot.getBoundingClientRect();
    checks.robot = {
      naturalWidth: robot.naturalWidth,
      naturalHeight: robot.naturalHeight,
      displayWidth: r.width,
      displayHeight: r.height,
      complete: robot.complete
    };
  }
  return checks;
}
"""


def run_viewport(w, h):
    out = {"size": [w, h], "assets": {}, "audit": {}, "broken": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": w, "height": h}).new_page()
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(800)
        for path in TARGETS:
            url = BASE + path
            resp = page.request.get(url)
            out["assets"][path] = {
                "status": resp.status,
                "bytes": len(resp.body()) if resp.ok else 0,
            }
            if not resp.ok:
                out["broken"].append(path)
        out["audit"] = page.evaluate(AUDIT_JS)
        page.locator(".pricing-card, .pricing__area, img[src*='pricing-img-1']").first.scroll_into_view_if_needed(timeout=15000)
        page.wait_for_timeout(400)
        pricing = page.evaluate(
            """() => {
            const img = document.querySelector('img[src*="pricing-img-1"]');
            if (!img) return { found: false };
            const r = img.getBoundingClientRect();
            return { found: true, naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight,
              displayWidth: r.width, displayHeight: r.height, complete: img.complete };
          }"""
        )
        out["audit"]["pricingImg"] = pricing
        browser.close()
    return out


def main():
    results = [run_viewport(1440, 900), run_viewport(390, 844)]
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
