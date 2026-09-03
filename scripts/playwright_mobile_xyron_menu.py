#!/usr/bin/env python3
"""Directed validation: mobile menu Xyron submenu visibility."""
import json
import re
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8012"

MEASURE_XYRON_SUBMENU = """
() => {
  const lis = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li'));
  const xyronLi = lis.find((li) => {
    const directA = li.querySelector(':scope > a:not(.mean-expand)');
    return directA && /xyron/i.test((directA.textContent || '').trim());
  });
  if (!xyronLi) return { found: false };

  const sub = xyronLi.querySelector(':scope > ul.submenu--robots')
    || xyronLi.querySelector(':scope > ul');
  if (!sub) return { found: true, subFound: false };

  const st = window.getComputedStyle(sub);
  const rect = sub.getBoundingClientRect();
  const links = Array.from(sub.querySelectorAll(':scope > li > a'));
  let visibleLinks = 0;
  const linkLabels = [];
  for (const a of links) {
    const ar = a.getBoundingClientRect();
    const ast = window.getComputedStyle(a);
    const vis = ar.width > 0 && ar.height > 0
      && ast.visibility !== 'hidden' && ast.display !== 'none';
    if (vis) visibleLinks += 1;
    linkLabels.push((a.textContent || '').trim());
  }
  return {
    found: true,
    subFound: true,
    directLinkText: (xyronLi.querySelector(':scope > a:not(.mean-expand)')?.textContent || '').trim(),
    expandClasses: xyronLi.querySelector('a.mean-expand')?.className || null,
    liClasses: xyronLi.className,
    display: st.display,
    visibility: st.visibility,
    height: st.height,
    scrollHeight: sub.scrollHeight,
    offsetHeight: sub.offsetHeight,
    rectHeight: rect.height,
    totalLinks: links.length,
    visibleLinks,
    linkLabels,
    visuallyOpen: rect.height > 0 && visibleLinks > 0
  };
}
"""


def menu_related_errors(errors):
    out = []
    for e in errors:
        low = e.lower()
        if "livia" in low or "lívia" in low or "cors" in low:
            continue
        if "failed to load resource" in low:
            continue
        if "unrecognized expression: #" in low:
            continue
        out.append(e)
    return out


def main():
    result = {
        "submenuOpened": False,
        "heightBefore": None,
        "heightAfter": None,
        "visibleLinksCount": 0,
        "totalLinksCount": 0,
        "linkSamples": [],
        "closedCorrectly": False,
        "reopenedCorrectly": False,
        "offcanvasClosedCorrectly": False,
        "jsErrorsRelated": False,
        "jsErrorsRelatedList": [],
        "codeChanged": True,
        "codeChangedNote": "Somente script scripts/playwright_mobile_xyron_menu.py (teste); main.js inalterado nesta validação.",
        "steps": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        console_errors = []
        page.on("console", lambda m: m.type == "error" and console_errors.append(m.text))
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        try:
            page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(600)

            page.locator(".sidebar__toggle .bar-icon").first.click()
            page.wait_for_timeout(700)

            result["steps"]["offcanvasOpen"] = page.evaluate(
                """() => ({
                  area: document.querySelector('.offcanvas__area')?.classList.contains('info-open'),
                  overlay: document.querySelector('.offcanvas__overlay')?.classList.contains('overlay-open'),
                  meanNavVisible: !!document.querySelector('.mobile-menu .mean-nav')
                })"""
            )

            before = page.evaluate(MEASURE_XYRON_SUBMENU)
            result["steps"]["beforeExpand"] = before
            result["heightBefore"] = before.get("rectHeight")

            # Expand Soluções first (parent of nested Xyron)
            solucoes = page.locator(".mobile-menu .mean-nav li").filter(
                has=page.locator(":scope > a:not(.mean-expand)", has_text=re.compile(r"Solu", re.I))
            ).first
            if solucoes.count():
                sol_expand = solucoes.locator(":scope > a.mean-expand").first
                if sol_expand.count():
                    sol_expand.click(force=True)
                    page.wait_for_timeout(400)

            result["steps"]["afterSolucoesExpand"] = page.evaluate(
                """() => {
                const solLi = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li')).find((li) => {
                  const a = li.querySelector(':scope > a:not(.mean-expand)');
                  return a && /solu/i.test((a.textContent || '').trim());
                });
                const ul = solLi?.querySelector(':scope > ul');
                return { solucoesUlHeight: ul ? ul.getBoundingClientRect().height : 0 };
              }"""
            )

            xyron_li = page.locator(".mobile-menu .mean-nav li").filter(
                has=page.locator(":scope > a:not(.mean-expand)", has_text=re.compile(r"Xyron", re.I))
            ).first
            expand = xyron_li.locator(":scope > a.mean-expand").first
            expand.click(force=True)
            page.wait_for_timeout(100)
            page.wait_for_function(
                """() => {
                const lis = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li'));
                const xyronLi = lis.find((li) => {
                  const a = li.querySelector(':scope > a:not(.mean-expand)');
                  return a && /xyron/i.test((a.textContent || '').trim());
                });
                const sub = xyronLi?.querySelector(':scope > ul.submenu--robots')
                  || xyronLi?.querySelector(':scope > ul');
                return sub && sub.getBoundingClientRect().height > 0;
              }""",
                timeout=5000,
            )

            after_open = page.evaluate(MEASURE_XYRON_SUBMENU)
            result["steps"]["afterFirstOpen"] = after_open
            result["heightAfter"] = after_open.get("rectHeight")
            result["visibleLinksCount"] = after_open.get("visibleLinks", 0)
            result["totalLinksCount"] = after_open.get("totalLinks", 0)
            result["linkSamples"] = after_open.get("linkLabels", [])
            result["submenuOpened"] = bool(after_open.get("visuallyOpen"))

            # Close Xyron submenu
            expand.click(force=True)
            page.wait_for_timeout(500)
            closed = page.evaluate(
                """() => {
                const xyronLi = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li')).find((li) => {
                  const a = li.querySelector(':scope > a:not(.mean-expand)');
                  return a && /xyron/i.test((a.textContent || '').trim());
                });
                const sub = xyronLi?.querySelector(':scope > ul.submenu--robots')
                  || xyronLi?.querySelector(':scope > ul');
                const h = sub ? sub.getBoundingClientRect().height : 0;
                return { rectHeight: h, closed: h === 0 };
              }"""
            )
            result["steps"]["afterClose"] = closed
            result["closedCorrectly"] = bool(closed.get("closed"))

            # Reopen
            expand.click(force=True)
            page.wait_for_function(
                """() => {
                const xyronLi = Array.from(document.querySelectorAll('.mobile-menu .mean-nav li')).find((li) => {
                  const a = li.querySelector(':scope > a:not(.mean-expand)');
                  return a && /xyron/i.test((a.textContent || '').trim());
                });
                const sub = xyronLi?.querySelector(':scope > ul.submenu--robots')
                  || xyronLi?.querySelector(':scope > ul');
                return sub && sub.getBoundingClientRect().height > 0;
              }""",
                timeout=5000,
            )
            reopen = page.evaluate(MEASURE_XYRON_SUBMENU)
            result["steps"]["afterReopen"] = reopen
            result["reopenedCorrectly"] = bool(reopen.get("visuallyOpen"))

            page.locator(".offcanvas-close-icon").first.click(force=True)
            page.wait_for_timeout(500)
            closed_off = page.evaluate(
                """() => ({
                  areaClosed: !document.querySelector('.offcanvas__area')?.classList.contains('info-open'),
                  overlayClosed: !document.querySelector('.offcanvas__overlay')?.classList.contains('overlay-open'),
                  bodyOverflow: getComputedStyle(document.body).overflow
                })"""
            )
            page.evaluate("window.scrollTo(0, 500)")
            page.wait_for_timeout(300)
            scroll_y = page.evaluate("() => window.scrollY || document.documentElement.scrollTop")
            result["steps"]["offcanvasClosed"] = {**closed_off, "scrollY": scroll_y}
            result["offcanvasClosedCorrectly"] = (
                closed_off.get("areaClosed")
                and closed_off.get("overlayClosed")
                and scroll_y > 50
            )

            related = menu_related_errors(console_errors)
            result["jsErrorsRelatedList"] = related
            result["jsErrorsRelated"] = len(related) > 0

        except Exception as exc:
            result["steps"]["error"] = str(exc)
            related = menu_related_errors(console_errors)
            result["jsErrorsRelatedList"] = related
            result["jsErrorsRelated"] = len(related) > 0

        finally:
            browser.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
