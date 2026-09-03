#!/usr/bin/env python3
"""Comprehensive HOME page Playwright checks (desktop + mobile)."""
import json
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"
VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]


def eval_metrics(page):
    return page.evaluate(
        """() => {
        const stLen = (typeof ScrollTrigger !== 'undefined' && ScrollTrigger.getAll)
            ? ScrollTrigger.getAll().length : -1;
        const swipers = document.querySelectorAll('.swiper-initialized').length;
        const carousels = document.querySelectorAll('.testimonial__carousel').length;
        return { scrollTriggerCount: stLen, swipersInitialized: swipers, testimonialCarousels: carousels };
    }"""
    )


def hero_h1_visible(page):
    return page.evaluate(
        """() => {
        const h1 = document.querySelector('h1');
        if (!h1) return { found: false, visible: false };
        const r = h1.getBoundingClientRect();
        const style = window.getComputedStyle(h1);
        const visible = r.width > 0 && r.height > 0
            && style.visibility !== 'hidden' && style.display !== 'none'
            && r.bottom > 0 && r.top < window.innerHeight;
        return { found: true, visible, text: (h1.textContent || '').trim().slice(0, 80) };
    }"""
    )


def banner_shape8_bg(page):
    return page.evaluate(
        """() => {
        const el = document.querySelector('.banner1__shapes-shape-8');
        if (!el) return { found: false, hasBg: false };
        const bg = window.getComputedStyle(el).backgroundImage;
        const attr = el.getAttribute('data-background');
        return {
            found: true,
            dataBackground: attr,
            backgroundImage: bg,
            hasBg: bg && bg !== 'none' && bg.includes('url')
        };
    }"""
    )


def count_selectors(page, selectors):
    return page.evaluate(
        """(sels) => {
        const out = {};
        for (const s of sels) out[s] = document.querySelectorAll(s).length;
        return out;
    }""",
        selectors,
    )


def visible_wow_count(page):
    return page.evaluate(
        """() => {
        const wows = Array.from(document.querySelectorAll('.wow'));
        let stuckHidden = 0;
        let visibleOk = 0;
        const vh = window.innerHeight;
        for (const el of wows) {
            const r = el.getBoundingClientRect();
            const inVp = r.top < vh && r.bottom > 0;
            if (!inVp) continue;
            const style = window.getComputedStyle(el);
            const visHidden = style.visibility === 'hidden';
            if (visHidden) stuckHidden += 1;
            else visibleOk += 1;
        }
        return { inViewport: visibleOk + stuckHidden, visibleOk, stuckHidden };
    }"""
    )


def swiper_slide_state(page):
    return page.evaluate(
        """() => {
        const root = document.querySelector('.testimonial__carousel.swiper-initialized');
        if (!root) return { initialized: false };
        const active = root.querySelector('.swiper-slide-active');
        const slides = root.querySelectorAll('.swiper-slide');
        let activeIndex = -1;
        slides.forEach((s, i) => { if (s.classList.contains('swiper-slide-active')) activeIndex = i; });
        const transform = active ? window.getComputedStyle(active).transform : '';
        return {
            initialized: true,
            activeIndex,
            activeTransform: transform,
            slideCount: slides.length,
            hasActiveClass: !!active
        };
    }"""
    )


def scroll_steps_to_percent(page, percent, steps):
    page.evaluate(
        """(args) => {
        const [pct, n] = args;
        const max = Math.max(
            document.documentElement.scrollHeight,
            document.body.scrollHeight
        ) - window.innerHeight;
        const target = max * pct;
        const step = target / n;
        let y = 0;
        for (let i = 0; i < n; i++) {
            y += step;
            window.scrollTo(0, y);
        }
    }""",
        [percent, steps],
    )
    page.wait_for_timeout(300)


def run_viewport(name, width, height):
    result = {"viewport": name, "size": [width, height], "steps": {}, "errors": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        console_errors = []

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", on_console)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        try:
            page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(500)

            result["steps"]["1_initial"] = eval_metrics(page)
            result["steps"]["hero_h1"] = hero_h1_visible(page)
            result["steps"]["banner_shape8"] = banner_shape8_bg(page)

            scroll_steps_to_percent(page, 0.4, 10)
            result["steps"]["after_40pct_scroll"] = eval_metrics(page)

            carousel = page.locator(".testimonial__carousel").first
            if carousel.count():
                carousel.scroll_into_view_if_needed(timeout=30000)
            page.wait_for_timeout(1000)

            after_testimonial = eval_metrics(page)
            result["steps"]["after_testimonial_1s"] = after_testimonial
            result["steps"]["swiper_must_be_1"] = after_testimonial["swipersInitialized"] == 1

            init_check = page.evaluate(
                """() => {
                const el = document.querySelector('.testimonial__carousel');
                return el ? el.classList.contains('swiper-initialized') : false;
            }"""
            )
            result["steps"]["testimonial_has_swiper_initialized_class"] = init_check

            slide_before = swiper_slide_state(page)
            result["steps"]["slide_before_autoplay"] = slide_before
            page.wait_for_timeout(2000)
            slide_after = swiper_slide_state(page)
            result["steps"]["slide_after_autoplay_2s"] = slide_after
            result["steps"]["autoplay_changed"] = (
                slide_before.get("activeIndex") != slide_after.get("activeIndex")
                or slide_before.get("activeTransform") != slide_after.get("activeTransform")
            )

            for sel in [".faq", ".blog", "footer"]:
                loc = page.locator(sel).first
                if loc.count():
                    try:
                        loc.scroll_into_view_if_needed(timeout=15000)
                        page.wait_for_timeout(400)
                    except Exception as e:
                        result["errors"].append(f"scroll {sel}: {e}")

            result["steps"]["element_counts_mid"] = count_selectors(
                page, [".return", ".rr_title_anim", ".hero", ".fade-top"]
            )

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)

            result["steps"]["element_counts_full"] = count_selectors(
                page, [".return", ".rr_title_anim", ".hero", ".fade-top"]
            )
            result["steps"]["scrollTrigger_after_full_scroll"] = eval_metrics(page)["scrollTriggerCount"]
            result["steps"]["wow_visibility"] = visible_wow_count(page)
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
