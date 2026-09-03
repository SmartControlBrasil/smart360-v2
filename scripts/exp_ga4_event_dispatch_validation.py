#!/usr/bin/env python3
"""Validação GA4 event dispatch — gtag('event') + lazy loader."""
import json
import re
import sys
import time
from collections import Counter

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
UTM_PATH = "/?utm_source=test&utm_medium=cpc&utm_campaign=perf_test&gclid=TEST123"
MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1440, "height": 900}

PREVENT_NAV = """
document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href*="wa.me"], a[href*="whatsapp"], a[target="_blank"]');
  if (link) event.preventDefault();
}, true);
document.addEventListener('submit', (event) => event.preventDefault(), true);
"""

GTAG_QUEUE_JS = """
(eventName) => window.dataLayer.filter((entry) => entry && entry[0] === 'event' && entry[1] === eventName)
"""

CUSTOM_DL_JS = """
(eventName) => window.dataLayer.filter((entry) => entry && entry.event === eventName)
"""

CLICK_PRIMARY_CTA_JS = """
() => {
  const btn = document.querySelector('[data-track-event="click_primary_cta"][data-track-location="home_hero"]')
    || document.querySelector('[data-track-event="click_primary_cta"][data-track-location="header"]')
    || document.querySelector('[data-track-event="click_primary_cta"]');
  if (!btn) return { ok: false };
  btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  return { ok: true };
}
"""

CLICK_WHATSAPP_JS = """
() => {
  const wa = document.querySelector('a.whatsapp-float');
  if (!wa) return { ok: false };
  wa.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  return { ok: true };
}
"""


class CollectMonitor:
    def __init__(self, page):
        self.urls = []
        page.on("request", self._track)
        page.on("response", self._track)

    def _track(self, req):
        url = req.url if hasattr(req, "url") else req.request.url
        if "/g/collect" in url or "/r/collect" in url:
            self.urls.append(url)

    def ens(self):
        found = []
        for url in self.urls:
            found.extend(re.findall(r"en=([^&]+)", url.split("?", 1)[-1]))
        return found


def wait_until(fn, timeout_ms=15000):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if fn():
            return True
        time.sleep(0.1)
    return False


def wait_gtag_ready(page):
    page.wait_for_function("() => typeof window.jQuery === 'function'", timeout=15000)
    page.wait_for_function(
        "() => window.dataLayer.some((entry) => entry && entry.event === 'gtm.load')",
        timeout=15000,
    )


def scenario_before_gtag_js():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=MOBILE)
        page.add_init_script(PREVENT_NAV)
        blocked = {"active": True}

        def route_handler(route):
            if blocked["active"] and "googletagmanager.com/gtag/js" in route.request.url:
                route.abort()
                return
            route.continue_()

        page.route("**/*", route_handler)
        monitor = CollectMonitor(page)
        page.goto(BASE + "/", wait_until="load")
        page.wait_for_function("() => typeof window.jQuery === 'function'", timeout=15000)

        page.evaluate(CLICK_PRIMARY_CTA_JS)

        dl_count = len(page.evaluate(CUSTOM_DL_JS, "click_primary_cta"))
        queue = page.evaluate(
            """(eventName) => {
              const entries = window.dataLayer.filter((entry) => entry && entry[0] === 'event' && entry[1] === eventName);
              const last = entries[entries.length - 1];
              return last ? { count: entries.length, params: last[2] || null } : { count: 0, params: null };
            }""",
            "click_primary_cta",
        )

        blocked["active"] = False
        page.evaluate("() => window.loadGoogleTagOnce && window.loadGoogleTagOnce()")
        wait_until(lambda: page.evaluate("() => window.smart360GoogleTagLoaded === true"), 12000)
        page.wait_for_function(
            "() => window.dataLayer.some((entry) => entry && entry.event === 'gtm.load')",
            timeout=15000,
        )
        time.sleep(4)
        browser.close()

    ens = monitor.ens()
    return {
        "dataLayer_count_before_gtag": dl_count,
        "gtag_queue_count_before_gtag": queue["count"],
        "gtag_queue_params": queue["params"],
        "click_primary_cta_collect": ens.count("click_primary_cta"),
        "page_view_collect": ens.count("page_view"),
    }


def scenario_clicks(label, viewport, path="/", block_gtag_until_ready=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.add_init_script(PREVENT_NAV)
        blocked = {"active": block_gtag_until_ready}

        if block_gtag_until_ready:
            def route_handler(route):
                if blocked["active"] and "googletagmanager.com/gtag/js" in route.request.url:
                    route.abort()
                    return
                route.continue_()

            page.route("**/*", route_handler)

        monitor = CollectMonitor(page)
        page.goto(BASE + path, wait_until="load")

        if block_gtag_until_ready:
            page.wait_for_function("() => typeof window.jQuery === 'function'", timeout=15000)
            page.evaluate(CLICK_PRIMARY_CTA_JS)
            queue_before = len(page.evaluate(GTAG_QUEUE_JS, "click_primary_cta"))
            blocked["active"] = False
            page.evaluate("() => window.loadGoogleTagOnce && window.loadGoogleTagOnce()")
            wait_until(lambda: page.evaluate("() => window.smart360GoogleTagLoaded === true"), 12000)
        else:
            queue_before = None
            wait_gtag_ready(page)

        baseline = len(monitor.ens())
        page.evaluate(CLICK_PRIMARY_CTA_JS)
        time.sleep(2)
        page.evaluate(CLICK_WHATSAPP_JS)
        time.sleep(4)

        ens = monitor.ens()[baseline:]
        browser.close()

    return {
        "label": label,
        "gtag_queue_before_load": queue_before,
        "click_primary_cta_collect": ens.count("click_primary_cta"),
        "click_whatsapp_collect": ens.count("click_whatsapp"),
        "duplicate_cta": ens.count("click_primary_cta") > 1,
    }


def scenario_utm():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=MOBILE)
        page.add_init_script(PREVENT_NAV)
        monitor = CollectMonitor(page)
        page.goto(BASE + UTM_PATH, wait_until="load")
        wait_gtag_ready(page)
        time.sleep(3)
        page_view = [u for u in monitor.urls if "page_view" in u]
        browser.close()

    joined = " ".join(page_view)
    return {
        "page_view_count": len(page_view),
        "utm_in_dl": "utm_source%3Dtest" in joined or "utm_source=test" in joined,
        "gclid_in_dl": "gclid%3DTEST123" in joined or "gclid=TEST123" in joined,
    }


def main():
    report = {
        "before_gtag_js": scenario_before_gtag_js(),
        "after_gtag_mobile": scenario_clicks("mobile_home", MOBILE, "/", block_gtag_until_ready=False),
        "event_before_gtag_mobile": scenario_clicks(
            "mobile_before_gtag", MOBILE, "/", block_gtag_until_ready=True
        ),
        "after_gtag_desktop": scenario_clicks("desktop_home", DESKTOP, "/", block_gtag_until_ready=False),
        "after_gtag_internal": scenario_clicks("about", DESKTOP, "/empresa/", block_gtag_until_ready=False),
        "utm": scenario_utm(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    ok = (
        report["before_gtag_js"]["dataLayer_count_before_gtag"] >= 1
        and report["before_gtag_js"]["gtag_queue_count_before_gtag"] >= 1
        and report["before_gtag_js"]["click_primary_cta_collect"] == 1
        and report["before_gtag_js"]["page_view_collect"] == 1
        and report["after_gtag_mobile"]["click_primary_cta_collect"] == 1
        and report["after_gtag_mobile"]["click_whatsapp_collect"] == 1
        and report["after_gtag_mobile"]["duplicate_cta"] is False
        and report["event_before_gtag_mobile"]["click_primary_cta_collect"] >= 1
        and report["after_gtag_desktop"]["click_primary_cta_collect"] == 1
        and report["utm"]["page_view_count"] == 1
        and report["utm"]["utm_in_dl"]
        and report["utm"]["gclid_in_dl"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
