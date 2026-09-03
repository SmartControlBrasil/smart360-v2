#!/usr/bin/env python3
"""Full HOME validation: Swiper lazy, GSAP groups, WOW, data-background."""
import json
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]

SCROLL_TO_ELEMENT_JS = """
(targetSelector) => {
  const el = document.querySelector(targetSelector);
  if (!el) return { ok: false, reason: 'missing element' };

  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  window.dispatchEvent(new Event('scroll'));

  const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get)
    ? ScrollSmoother.get()
    : null;

  if (smoother && typeof smoother.scrollTo === 'function') {
    smoother.scrollTo(el, true, 'center center');
  }

  if (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.refresh) {
    ScrollTrigger.refresh();
  }

  return {
    ok: true,
    method: smoother ? 'scrollIntoView+ScrollSmoother.scrollTo' : 'scrollIntoView'
  };
}
"""

GSAP_GROUP_AUDIT_JS = """
() => {
  const groups = {
    return: '.return',
    rr_title_anim: '.rr_title_anim',
    hero: '.hero',
    fade_top: '.fade-top'
  };

  const audit = {};
  for (const [key, sel] of Object.entries(groups)) {
    const nodes = Array.from(document.querySelectorAll(sel));
    let initialized = 0;
    let visibleAnimated = 0;
    const vh = window.innerHeight;

    for (const el of nodes) {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const inVp = rect.top < vh + 320 && rect.bottom > -320;

      const opacity = parseFloat(style.opacity);
      const visibility = style.visibility;
      const hasSplit = !!el.querySelector('[style*="translate"], .char, .word');
      const gsapStarted = opacity > 0.01 && visibility !== 'hidden';

      if (gsapStarted || hasSplit || style.transform !== 'none') {
        initialized += 1;
      }

      if (inVp && gsapStarted) {
        visibleAnimated += 1;
      }
    }

    audit[key] = {
      total: nodes.length,
      initializedHeuristic: initialized,
      visibleInExpandedViewportAnimated: visibleAnimated
    };
  }

  return audit;
}
"""

METRICS_JS = """
() => {
  const stLen = (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.getAll)
    ? ScrollTrigger.getAll().length : -1;
  const swipers = document.querySelectorAll('.swiper-initialized').length;
  const testimonial = document.querySelector('.testimonial__carousel');
  return {
    scrollTriggerCount: stLen,
    swipersInitialized: swipers,
    testimonialExists: !!testimonial,
    testimonialHasClass: testimonial ? testimonial.classList.contains('swiper-initialized') : false
  };
}
"""

DATA_BACKGROUND_JS = """
() => {
  const nodes = Array.from(document.querySelectorAll('[data-background]'));
  const vh = window.innerHeight;
  const out = { aboveFold: [], belowFold: [] };

  for (const el of nodes) {
    const rect = el.getBoundingClientRect();
    const bg = window.getComputedStyle(el).backgroundImage;
    const item = {
      selector: el.className.split(' ').slice(0, 2).join('.'),
      dataBackground: el.getAttribute('data-background'),
      hasBg: bg && bg !== 'none' && bg.includes('url')
    };

    if (rect.top < vh) {
      out.aboveFold.push(item);
    } else {
      out.belowFold.push(item);
    }
  }

  return out;
}
"""

WOW_AUDIT_JS = """
() => {
  const sections = ['.service', '.testimonial', '.faq', '.blog', 'footer'];
  const report = {};
  const vh = window.innerHeight;

  for (const sel of sections) {
    const root = document.querySelector(sel);
    if (!root) {
      report[sel] = { found: false };
      continue;
    }

    const wows = Array.from(root.querySelectorAll('.wow'));
    let stuckHidden = 0;
    let visibleOk = 0;

    for (const el of wows) {
      const r = el.getBoundingClientRect();
      const inVp = r.top < vh + 120 && r.bottom > -120;
      if (!inVp) continue;
      const style = window.getComputedStyle(el);
      if (style.visibility === 'hidden') stuckHidden += 1;
      else visibleOk += 1;
    }

    report[sel] = { found: true, visibleOk, stuckHidden };
  }

  return report;
}
"""


def scroll_steps_to_percent(page, percent, steps):
    page.evaluate(
        """(args) => {
        const [pct, n] = args;
        const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get)
          ? ScrollSmoother.get() : null;
        const max = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)
          - window.innerHeight;
        const target = max * pct;
        const step = target / n;
        let y = 0;
        for (let i = 0; i < n; i++) {
            y += step;
            if (smoother && typeof smoother.scrollTop === 'function') {
              smoother.scrollTop(y);
            } else {
              window.scrollTo(0, y);
            }
        }
        if (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.refresh) {
          ScrollTrigger.refresh();
        }
    }""",
        [percent, steps],
    )
    page.wait_for_timeout(400)


def run_viewport(name, width, height):
    result = {"viewport": name, "size": [width, height], "steps": {}, "errors": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        console_errors = []

        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if "liviasupport" in text.lower() or "cors" in text.lower():
                    return
                console_errors.append(text)

        page.on("console", on_console)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        try:
            page.goto(BASE + "/", wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(500)

            result["steps"]["initial_metrics"] = page.evaluate(METRICS_JS)
            result["steps"]["data_background_load"] = page.evaluate(DATA_BACKGROUND_JS)

            # Before testimonials: swiper should be 0
            before_testimonial = page.evaluate(METRICS_JS)
            result["steps"]["before_testimonial_scroll"] = before_testimonial

            scroll_steps_to_percent(page, 0.4, 10)

            carousel = page.locator(".testimonial__carousel").first
            if carousel.count():
                carousel.scroll_into_view_if_needed(timeout=30000)
            page.wait_for_timeout(1200)

            scroll_info = {"ok": carousel.count() > 0, "method": "scroll_steps+scroll_into_view_if_needed"}
            result["steps"]["scroll_to_testimonial"] = scroll_info

            after_testimonial = page.evaluate(METRICS_JS)
            result["steps"]["after_testimonial_scroll"] = after_testimonial

            slide_before = page.evaluate(
                """() => {
                const root = document.querySelector('.testimonial__carousel.swiper-initialized');
                if (!root) return { initialized: false };
                const active = root.querySelector('.swiper-slide-active');
                let idx = -1;
                root.querySelectorAll('.swiper-slide').forEach((s, i) => {
                  if (s.classList.contains('swiper-slide-active')) idx = i;
                });
                return { initialized: true, activeIndex: idx, transform: active ? getComputedStyle(active).transform : '' };
            }"""
            )
            page.wait_for_timeout(2500)
            slide_after = page.evaluate(
                """() => {
                const root = document.querySelector('.testimonial__carousel.swiper-initialized');
                if (!root) return { initialized: false };
                const active = root.querySelector('.swiper-slide-active');
                let idx = -1;
                root.querySelectorAll('.swiper-slide').forEach((s, i) => {
                  if (s.classList.contains('swiper-slide-active')) idx = i;
                });
                return { initialized: true, activeIndex: idx, transform: active ? getComputedStyle(active).transform : '' };
            }"""
            )
            result["steps"]["swiper_autoplay"] = {
                "before": slide_before,
                "after": slide_after,
                "changed": slide_before != slide_after
            }

            # Slow full-page scroll
            page.evaluate(
                """() => {
                const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get)
                  ? ScrollSmoother.get() : null;
                const max = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)
                  - window.innerHeight;
                const steps = 24;
                for (let i = 1; i <= steps; i++) {
                  const y = (max / steps) * i;
                  if (smoother && typeof smoother.scrollTop === 'function') {
                    smoother.scrollTop(y);
                  } else {
                    window.scrollTo(0, y);
                  }
                }
                if (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.refresh) ScrollTrigger.refresh();
            }"""
            )
            page.wait_for_timeout(1500)

            result["steps"]["service_bg_after_scroll"] = page.evaluate(
                """() => {
                const shapes = Array.from(document.querySelectorAll('.service__bg-shape[data-background]'));
                return shapes.map((el) => ({
                  hasBg: (getComputedStyle(el).backgroundImage || '').includes('url'),
                  dataBackground: el.getAttribute('data-background')
                }));
            }"""
            )

            result["steps"]["gsap_groups_after_full_scroll"] = page.evaluate(GSAP_GROUP_AUDIT_JS)
            result["steps"]["final_metrics"] = page.evaluate(METRICS_JS)
            result["steps"]["wow_sections"] = page.evaluate(WOW_AUDIT_JS)
            result["console_errors"] = console_errors

        finally:
            browser.close()

    return result


def main():
    all_results = []
    for name, w, h in VIEWPORTS:
        print(f"Running {name} {w}x{h}...", file=sys.stderr)
        all_results.append(run_viewport(name, w, h))
    print(json.dumps(all_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
