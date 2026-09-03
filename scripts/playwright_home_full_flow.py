#!/usr/bin/env python3
"""Full HOME interaction flow: FAQ, menu, back-to-top, Swiper, WOW/GSAP."""
import json
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]

METRICS_JS = """
() => ({
  scrollTriggerCount: (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.getAll)
    ? ScrollTrigger.getAll().length : -1,
  swipersInitialized: document.querySelectorAll('.swiper-initialized').length,
  testimonialInitialized: !!document.querySelector('.testimonial__carousel.swiper-initialized')
})
"""

SCROLL_STEPS_JS = """
(args) => {
  const [pct, steps] = args;
  const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get)
    ? ScrollSmoother.get() : null;
  const max = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)
    - window.innerHeight;
  const target = max * pct;
  const step = target / steps;
  let y = 0;
  for (let i = 0; i < steps; i++) {
    y += step;
    if (smoother && typeof smoother.scrollTop === 'function') smoother.scrollTop(y);
    else window.scrollTo(0, y);
  }
  if (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.refresh) ScrollTrigger.refresh();
}
"""

WOW_GSAP_AUDIT_JS = """
() => {
  const vh = window.innerHeight;
  const stuckWow = [];
  document.querySelectorAll('.wow').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= vh) return;
    const st = window.getComputedStyle(el);
    if (st.visibility === 'hidden') stuckWow.push(el.className.slice(0, 60));
  });
  const sections = ['.banner1', '.service__area', '.testimonial__area', '.faq__area'];
  const hiddenSections = [];
  for (const sel of sections) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= vh) continue;
    const st = window.getComputedStyle(el);
    if (st.display === 'none' || (st.visibility === 'hidden' && parseFloat(st.opacity) < 0.01)) {
      hiddenSections.push(sel);
    }
  }
  return {
    stuckWowInViewport: stuckWow.length,
    stuckWowSamples: stuckWow.slice(0, 5),
    hiddenSectionsInViewport: hiddenSections
  };
}
"""


def scroll_steps(page, pct, steps, wait_ms=350):
    page.evaluate(SCROLL_STEPS_JS, [pct, steps])
    page.wait_for_timeout(wait_ms)


def filter_console_errors(errors):
    out = []
    for e in errors:
        low = e.lower()
        if "livia" in low or "cors" in low or "smartcontrolbrasil.com.br" in low:
            continue
        if "failed to load resource" in low and "net::err_failed" in low:
            continue
        out.append(e)
    return out


def test_swiper(page, initial_metrics):
    result = {"ok": False, "details": {"initial": initial_metrics}}
    scroll_steps(page, 0.4, 10, 400)
    page.locator(".testimonial__carousel").first.scroll_into_view_if_needed(timeout=30000)
    page.wait_for_timeout(1200)

    at_section = page.evaluate(
        """() => {
        const root = document.querySelector('.testimonial__carousel');
        const slides = root ? root.querySelectorAll('.swiper-slide') : [];
        let idx = -1;
        slides.forEach((s, i) => { if (s.classList.contains('swiper-slide-active')) idx = i; });
        return {
          swipersInitialized: document.querySelectorAll('.swiper-initialized').length,
          testimonialInitialized: root?.classList.contains('swiper-initialized') || false,
          activeIndexBefore: idx
        };
      }"""
    )
    result["details"]["atTestimonials"] = at_section
    page.wait_for_timeout(4000)
    after = page.evaluate(
        """() => {
        const root = document.querySelector('.testimonial__carousel.swiper-initialized');
        if (!root) return { initialized: false };
        const slides = root.querySelectorAll('.swiper-slide');
        let idx = -1;
        slides.forEach((s, i) => { if (s.classList.contains('swiper-slide-active')) idx = i; });
        return { initialized: true, activeIndexAfter: idx };
      }"""
    )
    result["details"]["autoplay"] = after
    init_ok = initial_metrics.get("swipersInitialized") == 0 and at_section.get("testimonialInitialized") is True
    autoplay_ok = after.get("initialized") and after.get("activeIndexAfter", -1) != at_section.get("activeIndexBefore", -1)
    result["ok"] = init_ok and autoplay_ok
    result["details"]["initOk"] = init_ok
    result["details"]["autoplayOk"] = autoplay_ok
    return result


def test_faq(page):
    result = {"ok": False, "details": {}}
    page.locator(".faq__area").first.scroll_into_view_if_needed(timeout=30000)
    page.wait_for_timeout(2500)

    toggles = []
    for header_id in ("headingOne", "headingTow"):
        btn = page.locator(f"#{header_id} .accordion-button").first
        if not btn.count():
            toggles.append({"id": header_id, "error": "missing"})
            continue

        target = btn.get_attribute("data-bs-target") or ""
        panel = page.locator(target).first if target else None
        if not panel or not panel.count():
            toggles.append({"id": header_id, "error": "missing panel"})
            continue

        before = {
            "ariaExpanded": btn.get_attribute("aria-expanded"),
            "show": "show" in (panel.get_attribute("class") or ""),
        }
        btn.click(force=True)
        page.wait_for_timeout(500)
        after_open = {
            "ariaExpanded": btn.get_attribute("aria-expanded"),
            "show": "show" in (panel.get_attribute("class") or ""),
        }
        btn.click(force=True)
        page.wait_for_timeout(500)
        after_close = {
            "ariaExpanded": btn.get_attribute("aria-expanded"),
            "show": "show" in (panel.get_attribute("class") or ""),
        }
        toggles.append({
            "id": header_id,
            "before": before,
            "afterOpen": after_open,
            "afterClose": after_close,
            "openWorked": after_open["show"] != before["show"] or after_open["ariaExpanded"] != before["ariaExpanded"],
            "closeWorked": after_close["show"] != after_open["show"] or after_close["ariaExpanded"] != after_open["ariaExpanded"],
        })

    result["details"]["toggles"] = toggles
    result["ok"] = len(toggles) >= 2 and all(
        t.get("openWorked") and t.get("closeWorked") for t in toggles if "error" not in t
    )
    return result


def test_mobile_menu(page):
    result = {"ok": False, "skipped": False, "details": {}}
    if page.viewport_size["width"] > 991:
        result["skipped"] = True
        result["ok"] = True
        result["details"]["reason"] = "desktop viewport"
        return result

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    page.locator(".sidebar__toggle .bar-icon").first.click()
    page.wait_for_timeout(700)

    state = page.evaluate(
        """() => {
        const open = {
          area: document.querySelector('.offcanvas__area')?.classList.contains('info-open'),
          overlay: document.querySelector('.offcanvas__overlay')?.classList.contains('overlay-open'),
          menuVisible: !!document.querySelector('.mobile-menu .mean-nav')
        };
        const lis = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li'));
        const xyronLi = lis.find((li) => (li.textContent || '').includes('Xyron'));
        let xyronItems = 0;
        let submenuOpen = false;
        if (xyronLi) {
          const expand = xyronLi.querySelector('a.mean-expand');
          if (expand) expand.click();
          else xyronLi.querySelector('a')?.click();
          const sub = xyronLi.querySelector('ul');
          xyronItems = xyronLi.querySelectorAll('ul li a').length;
          submenuOpen = xyronLi.classList.contains('mean-clicked')
            || xyronLi.classList.contains('dropdown-open')
            || (sub && sub.offsetHeight > 0);
        }
        const closeBtn = document.querySelector('.offcanvas-close-icon');
        if (closeBtn) closeBtn.click();
        else document.querySelector('.offcanvas__overlay')?.click();
        const closed = {
          area: !document.querySelector('.offcanvas__area')?.classList.contains('info-open'),
          overlay: !document.querySelector('.offcanvas__overlay')?.classList.contains('overlay-open')
        };
        return { open, xyronItems, submenuOpen, closed };
      }"""
    )
    result["details"] = state
    result["ok"] = (
        state["open"]["area"]
        and state["open"]["overlay"]
        and state["open"]["menuVisible"]
        and state["xyronItems"] >= 3
        and state["submenuOpen"]
        and state["closed"]["area"]
        and state["closed"]["overlay"]
    )
    return result


def test_back_to_top(page, is_desktop):
    result = {"ok": False, "details": {}}
    scroll_steps(page, 0.92, 12, 400)
    page.wait_for_timeout(800)

    control = page.evaluate(
        """() => {
        const el = document.querySelector('#scroll-percentage');
        const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get) ? ScrollSmoother.get() : null;
        const scrollPos = smoother ? smoother.scrollTop() : (window.scrollY || document.documentElement.scrollTop);
        return {
          found: !!el,
          active: el?.classList.contains('active') || false,
          scrollPos,
          usesSmoother: !!smoother
        };
      }"""
    )
    result["details"]["beforeClick"] = control

    page.evaluate("document.querySelector('#scroll-percentage')?.click()")
    page.wait_for_timeout(4000)

    after = page.evaluate(
        """() => {
        const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get) ? ScrollSmoother.get() : null;
        const pos = smoother ? smoother.scrollTop() : (window.scrollY || document.documentElement.scrollTop);
        const h1Top = document.querySelector('h1')?.getBoundingClientRect().top ?? null;
        return { pos, h1Top, smootherAlive: !!smoother, scrollY: window.scrollY || document.documentElement.scrollTop };
      }"""
    )
    result["details"]["afterClick"] = after

    near_top = (after.get("pos") or after.get("scrollY") or 9999) < 150
    h1_ok = (after.get("h1Top") or 9999) < 400 and (after.get("h1Top") or -999) > -80
    if is_desktop:
        result["ok"] = near_top and h1_ok and after.get("smootherAlive")
        result["details"]["controlActiveLimitation"] = not control.get("active")
        result["details"]["note"] = (
            "No desktop, #scroll-percentage.active depende de documentElement.scrollTop; "
            "ScrollSmoother mantém scrollY=0. Clique no controle pode não subir — ver pos/h1Top."
        )
    else:
        result["ok"] = (control.get("active") or control.get("scrollPos", 0) > 100) and near_top and h1_ok
    return result


def run_viewport(name, width, height):
    out = {
        "viewport": name,
        "size": [width, height],
        "metrics": {},
        "faq": {},
        "mobileMenu": {},
        "backToTop": {},
        "swiper": {},
        "wowGsap": {},
        "consoleErrors": [],
        "pageErrors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": width, "height": height})
        page = ctx.new_page()
        console_errors = []

        page.on("console", lambda msg: msg.type == "error" and console_errors.append(msg.text))
        page.on("pageerror", lambda exc: out["pageErrors"].append(str(exc)))

        try:
            page.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(500)
            initial = page.evaluate(METRICS_JS)
            out["metrics"]["initial"] = initial

            out["swiper"] = test_swiper(page, initial)
            out["faq"] = test_faq(page)

            if name == "mobile":
                out["mobileMenu"] = test_mobile_menu(page)
            else:
                out["mobileMenu"] = {"ok": True, "skipped": True, "details": {"reason": "desktop"}}

            out["backToTop"] = test_back_to_top(page, name == "desktop")

            scroll_steps(page, 1.0, 16, 300)
            page.wait_for_timeout(800)
            out["metrics"]["final"] = page.evaluate(METRICS_JS)
            out["wowGsap"] = page.evaluate(WOW_GSAP_AUDIT_JS)
            out["consoleErrors"] = filter_console_errors(console_errors)
        except Exception as exc:
            out["fatalError"] = str(exc)
        finally:
            browser.close()

    return out


def main():
    results = []
    for name, w, h in VIEWPORTS:
        print(f"Running {name}...", file=sys.stderr)
        results.append(run_viewport(name, w, h))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
