#!/usr/bin/env python3
"""Validação GA4 lazy seguro — Home mobile (Playwright + CDP)."""
import json
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
UTM_PATH = "/?utm_source=test&utm_medium=cpc&utm_campaign=perf_test&gclid=TEST123"
MOBILE = {"width": 390, "height": 844}


def collect_requests(page):
    reqs = []

    def on_request(request):
        url = request.url
        if "googletagmanager.com/gtag/js" in url or "/g/collect" in url or "google-analytics.com/g/collect" in url:
            reqs.append(
                {
                    "ts_ms": round(time.time() * 1000),
                    "url": url,
                    "method": request.method,
                }
            )

    page.on("request", on_request)
    return reqs


def wait_for(predicate, timeout_ms=15000, interval_ms=100):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval_ms / 1000)
    return False


def run_mobile_home(path="/"):
    result = {
        "path": path,
        "viewport": MOBILE,
        "dataLayer_early": False,
        "gtag_fn_early": False,
        "gtag_script_before_interaction": False,
        "load_count": None,
        "page_view_collect_count": 0,
        "events": {},
        "utm_gclid_in_collect": False,
        "timeline": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=MOBILE, user_agent=(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ))
        page = context.new_page()
        page.add_init_script(
            """
            document.addEventListener('click', (event) => {
              const link = event.target.closest('a[href*="wa.me"], a[href*="whatsapp"], a[target="_blank"]');
              if (link) event.preventDefault();
            }, true);
            document.addEventListener('submit', (event) => event.preventDefault(), true);
            """
        )
        reqs = collect_requests(page)

        nav_start = time.time()
        page.goto(BASE + path, wait_until="load")

        result["dataLayer_early"] = page.evaluate("() => Array.isArray(window.dataLayer)")
        result["gtag_fn_early"] = page.evaluate("() => typeof window.gtag === 'function'")

        # Garantir main.js/jQuery antes dos cliques de tracking
        page.wait_for_function("() => typeof window.jQuery === 'function'", timeout=15000)

        gtag_before_cta = any("googletagmanager.com/gtag/js" in r["url"] for r in reqs)

        # CTA hero via JS (evita navegação do form submit)
        cta_dl = page.evaluate(
            """() => {
              const btn = document.querySelector('[data-track-event="click_primary_cta"][data-track-location="home_hero"]');
              if (!btn) return { ok: false, count: 0 };
              btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
              const hits = window.dataLayer.filter(e => e && e.event === 'click_primary_cta');
              return { ok: true, count: hits.length, last: hits[hits.length - 1] || null };
            }"""
        )
        result["events"]["click_primary_cta_before_gtag"] = cta_dl.get("count", 0)
        result["events"]["click_primary_cta_payload"] = cta_dl.get("last")

        gtag_before_wa = any("googletagmanager.com/gtag/js" in r["url"] for r in reqs)
        result["gtag_script_before_interaction"] = gtag_before_cta and gtag_before_wa

        if not gtag_before_wa:
            wa_dl = page.evaluate(
                """() => {
                  const wa = document.querySelector('a.whatsapp-float');
                  if (!wa) return { count: 0 };
                  wa.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                  const hits = window.dataLayer.filter(e => e && e.event === 'click_whatsapp');
                  return { count: hits.length, last: hits[hits.length - 1] || null };
                }"""
            )
            result["events"]["click_whatsapp_before_gtag"] = wa_dl.get("count", 0)
            result["events"]["click_whatsapp_payload"] = wa_dl.get("last")

        # Esperar failsafe + stagger (~3s)
        wait_for(lambda: page.evaluate("() => window.smart360GoogleTagLoadCount >= 1"), 6000)
        wait_for(
            lambda: page.evaluate("() => window.smart360GoogleTagLoaded === true"),
            12000,
        )

        result["load_count"] = page.evaluate("() => window.smart360GoogleTagLoadCount")
        result["gtag_script_tags"] = page.evaluate(
            """() => [...document.querySelectorAll('script[src*="googletagmanager.com/gtag/js"]')].length"""
        )

        # page load complete + flush collect
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1.5)

        collect_urls = [
            r["url"]
            for r in reqs
            if "/g/collect" in r["url"] or "google-analytics.com/g/collect" in r["url"]
        ]
        page_view_hits = [u for u in collect_urls if "en=page_view" in u or "en%3Dpage_view" in u]
        result["page_view_collect_count"] = len(page_view_hits)

        def event_in_collect(name):
            return [
                u
                for u in collect_urls
                if f"en={name}" in u
                or f"en%3D{name}" in u
                or name in u
            ]

        result["events"]["click_primary_cta_collect"] = len(event_in_collect("click_primary_cta"))
        result["events"]["click_whatsapp_collect"] = len(event_in_collect("click_whatsapp"))
        result["collect_samples"] = collect_urls[:8]

        if path.startswith("/?"):
            utm_checks = all(
                token in " ".join(collect_urls)
                for token in ("utm_source=test", "utm_medium=cpc", "utm_campaign=perf_test", "gclid=TEST123")
            )
            result["utm_gclid_in_collect"] = utm_checks

        perf = page.evaluate(
            """() => {
              const nav = performance.getEntriesByType('navigation')[0];
              const paints = performance.getEntriesByType('paint');
              const fcp = paints.find(p => p.name === 'first-contentful-paint');
              const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
              const lcp = lcpEntries.length ? lcpEntries[lcpEntries.length - 1] : null;
              const gtagReq = performance.getEntriesByType('resource')
                .filter(r => r.name.includes('googletagmanager.com/gtag/js'))
                .sort((a,b) => a.startTime - b.startTime)[0];
              return {
                navigationStart: nav ? nav.startTime : null,
                fcp: fcp ? fcp.startTime : null,
                lcp: lcp ? lcp.startTime : null,
                gtagStart: gtagReq ? gtagReq.startTime : null,
                gtagDuration: gtagReq ? gtagReq.duration : null,
              };
            }"""
        )
        result["timeline"] = perf
        result["gtag_request_count"] = len(
            [r for r in reqs if "googletagmanager.com/gtag/js" in r["url"]]
        )
        result["collect_request_count"] = len(collect_urls)
        result["elapsed_s"] = round(time.time() - nav_start, 2)

        browser.close()

    return result


def run_desktop_home():
    result = {"viewport": "desktop", "immediate_gtag": False}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        reqs = collect_requests(page)
        page.goto(BASE + "/", wait_until="domcontentloaded")
        time.sleep(0.5)
        result["immediate_gtag"] = any("googletagmanager.com/gtag/js" in r["url"] for r in reqs)
        result["is_home_mobile_gate"] = page.evaluate(
            """() => typeof scheduleHomeMobileGoogleTagAfterLcp === 'function'"""
        )
        browser.close()
    return result


def main():
    out = {
        "mobile_home": run_mobile_home("/"),
        "mobile_home_utm": run_mobile_home(UTM_PATH),
        "desktop_home": run_desktop_home(),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    ok = (
        out["mobile_home"]["dataLayer_early"]
        and out["mobile_home"]["gtag_fn_early"]
        and out["mobile_home"]["load_count"] == 1
        and out["mobile_home"]["gtag_script_tags"] == 1
        and out["mobile_home"]["events"].get("click_primary_cta_before_gtag", 0) >= 1
        and out["mobile_home"]["page_view_collect_count"] >= 1
        and out["mobile_home"]["page_view_collect_count"] <= 2
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
