#!/usr/bin/env python3
"""Experimento G.3 — medição runtime + smoke (instrumentação in-memory)."""
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8013/"
MAIN_JS = Path(__file__).resolve().parents[1] / "static/institutional/js/main.js"

TITLE_KEYS = {1: "A", 4: "B", 7: "C"}

TELEMETRY_HEAD = r"""
window.__tel = window.__tel || {
  t0: performance.now(),
  logical: [],
  effective: [],
  duringFlush: [],
  refreshes: [],
  flushes: [],
  _flushSeq: 0,
  _currentFlush: null,
  now: function() { return Math.round((performance.now() - this.t0) * 10) / 10; },
  classifySite: function(stack) {
    var s = stack || '';
    if (s.indexOf('initReturnReveal') !== -1) return 'return';
    if (s.indexOf('initTitleLine') !== -1) return 'rr_title_anim';
    if (s.indexOf('initHeroSplit') !== -1) return 'hero';
    if (s.indexOf('initFadeItem') !== -1) return 'fade-top';
    if (s.indexOf('flushPendingViewportInits') !== -1) return 'flush_batch_end';
    return 'other';
  }
};
window.__titleGeom = window.__titleGeom || {};
"""

INIT_HOOK = r"""
(() => {
  const tel = window.__tel;
  const wrapRefresh = () => {
    if (typeof ScrollTrigger === 'undefined' || !ScrollTrigger.refresh || ScrollTrigger.refresh.__w) return;
    const orig = ScrollTrigger.refresh.bind(ScrollTrigger);
    ScrollTrigger.refresh = function() {
      const stack = (new Error()).stack || '';
      let phase = 'internal';
      if (/ScrollSmoother/.test(stack)) phase = 'smoother';
      else if (/main\.js/.test(stack) && /:12[0-9]:|:13[0-9]:/.test(stack)) phase = 'main';
      tel.refreshes.push({ t: tel.now(), phase, stack: stack.split('\n').slice(1, 8) });
      return orig();
    };
    ScrollTrigger.refresh.__w = 1;
  };
  setInterval(wrapRefresh, 5);
})();
"""

GEOM_SNAP = r"""
function __geomSnap(st, moment) {
  return {
    moment: moment,
    start: st ? st.start : null,
    end: st ? st.end : null,
    isActive: st ? !!st.isActive : null,
    progress: st ? st.progress : null
  };
}
"""

GEOM_INJECT_MARKER = "const tl = gsap.timeline({"
GEOM_INJECT_AFTER = r"""
           var __allTitles = gsap.utils.toArray(".rr_title_anim");
           var __idx = __allTitles.indexOf(splitTextLine);
           var __key = __idx === 1 ? 'A' : __idx === 4 ? 'B' : __idx === 7 ? 'C' : null;
           if (__key) {
             var __st = tl.scrollTrigger;
             window.__titleGeom[__key] = window.__titleGeom[__key] || [];
             window.__titleGeom[__key].push(__geomSnap(__st, 'T1'));
             requestAnimationFrame(function() {
               window.__titleGeom[__key].push(__geomSnap(__st, 'T2'));
             });
           }
"""

SCHEDULE_PATCH_OLD = "function scheduleScrollTriggerRefresh() {"
SCHEDULE_PATCH = r"""function scheduleScrollTriggerRefresh() {
    window.__tel = window.__tel || { t0: performance.now(), logical: [], effective: [], duringFlush: [], now: function(){ return performance.now()-this.t0; }, classifySite: function(s){ s=s||''; if(s.indexOf('initReturnReveal')!==-1)return'return'; if(s.indexOf('initTitleLine')!==-1)return'rr_title_anim'; if(s.indexOf('initHeroSplit')!==-1)return'hero'; if(s.indexOf('initFadeItem')!==-1)return'fade-top'; if(s.indexOf('flushPendingViewportInits')!==-1)return'flush_batch_end'; return'other'; } };
    var __stack = (new Error()).stack || '';
    var __site = window.__tel.classifySite(__stack);
    var __during = !!window.viewportInitFlushInProgress;
    window.__tel.logical.push({ t: window.__tel.now(), site: __site, duringFlush: __during, stack: __stack.split('\n').slice(1,6) });
    if (__during) window.__tel.duringFlush.push({ t: window.__tel.now(), site: __site });
"""

FLUSH_PATCH_OLD = "function flushPendingViewportInits() {"
FLUSH_PATCH = r"""function flushPendingViewportInits() {
    window.__tel = window.__tel || { t0: performance.now(), flushes: [], _flushSeq: 0, _currentFlush: null, now: function(){ return performance.now()-this.t0; } };
    window.__tel._flushSeq = (window.__tel._flushSeq || 0) + 1;
    window.__tel._currentFlush = window.__tel._flushSeq;
    window.__tel.flushes.push({ t: window.__tel.now(), seq: window.__tel._flushSeq });
"""

TIMEOUT_PATCH = "scrollTriggerRefreshTimeout = setTimeout(function () {"
TIMEOUT_PATCH_NEW = r"""scrollTriggerRefreshTimeout = setTimeout(function () {
      window.__tel = window.__tel || { effective: [], now: function(){ return performance.now()-(this.t0||performance.now()); } };
      window.__tel.effective.push({ t: window.__tel.now(), site: 'scheduled' });
"""

SCROLL_JS = """
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
}
"""

T3_JS = """
() => {
  const keys = { A: 1, B: 4, C: 7 };
  const all = Array.from(document.querySelectorAll('.rr_title_anim'));
  const out = {};
  for (const [k, idx] of Object.entries(keys)) {
    const el = all[idx];
    if (!el) { out[k] = { error: 'missing', moment: 'T3' }; continue; }
    let st = null;
    if (typeof ScrollTrigger !== 'undefined') {
      ScrollTrigger.getAll().forEach(t => { if (t.trigger === el) st = t; });
    }
    out[k] = {
      moment: 'T3',
      start: st ? st.start : null,
      end: st ? st.end : null,
      isActive: st ? !!st.isActive : null,
      progress: st ? st.progress : null,
      rectTop: el.getBoundingClientRect().top
    };
  }
  return out;
}
"""

SMOKE_JS = """
() => {
  const vh = window.innerHeight;
  const report = {
    rr_title_anim: { pass: true, issues: [], count: 0, stuck: 0, details: [] },
    return: { pass: true, issues: [], count: 0, stuck: 0 },
    hero: { pass: true, issues: [], count: 0, stuck: 0 },
    fade_top: { pass: true, issues: [], count: 0, stuck: 0 },
    scrollSmoother: { pass: true, issues: [] },
    backToTop: { pass: true, issues: [] },
    resize: { pass: true, issues: [] },
    gsapErrors: { pass: true, issues: [] },
    stuckTotal: 0
  };

  const titles = Array.from(document.querySelectorAll('.rr_title_anim')).filter(el => !el.closest('.banner-before'));
  report.rr_title_anim.count = titles.length;
  titles.forEach((el, i) => {
    const lines = el.querySelectorAll('.line, div[style*="display"]');
    const hasSplit = el.querySelector('.line') || el.innerHTML.indexOf('<div') !== -1;
    const st = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const opacity = parseFloat(st.opacity);
    const visible = opacity > 0.05 && st.visibility !== 'hidden';
    let stObj = null;
    if (typeof ScrollTrigger !== 'undefined') {
      ScrollTrigger.getAll().forEach(t => { if (t.trigger === el) stObj = t; });
    }
    const invalidST = stObj && (stObj.start === 0 || stObj.end == null);
    if (!hasSplit && r.top < document.body.scrollHeight) {
      report.rr_title_anim.issues.push('idx'+i+': no SplitText lines');
      report.rr_title_anim.pass = false;
    }
    if (invalidST && r.top < vh * 2) {
      report.rr_title_anim.issues.push('idx'+i+': invalid ST start/end near viewport');
    }
    if (r.top < vh && r.bottom > 0 && opacity < 0.05) {
      report.rr_title_anim.stuck += 1;
      report.rr_title_anim.pass = false;
      report.stuckTotal += 1;
    }
    report.rr_title_anim.details.push({
      i, text: (el.textContent||'').trim().slice(0,40),
      hasSplit, opacity, stStart: stObj?stObj.start:null, stEnd: stObj?stObj.end:null
    });
  });

  document.querySelectorAll('.return').forEach(el => {
    report.return.count += 1;
    const img = el.querySelector('img');
    const st = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.top < vh && r.bottom > 0 && parseFloat(st.opacity) < 0.05) {
      report.return.stuck += 1; report.return.pass = false; report.stuckTotal += 1;
    }
    if (img && r.top < vh && parseFloat(window.getComputedStyle(img).opacity) < 0.05) {
      report.return.issues.push('img hidden in viewport');
    }
  });

  document.querySelectorAll('.hero').forEach(el => {
    report.hero.count += 1;
    const split = el.querySelector('._split_text');
    const r = el.getBoundingClientRect();
    if (split && r.top < vh * 1.5 && !split.querySelector('[class*="char"], [class*="word"]') && split.children.length <= 1) {
      report.hero.issues.push('hero split missing chars');
      report.hero.pass = false;
    }
  });

  document.querySelectorAll('.fade-top').forEach(el => {
    report.fade_top.count += 1;
    const r = el.getBoundingClientRect();
    const st = window.getComputedStyle(el);
    if (r.top < vh && r.bottom > 0 && parseFloat(st.opacity) < 0.05) {
      report.fade_top.stuck += 1; report.fade_top.pass = false; report.stuckTotal += 1;
    }
  });

  const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get) ? ScrollSmoother.get() : null;
  const isMobile = window.innerWidth <= 767;
  if (!isMobile) {
    if (!smoother) { report.scrollSmoother.pass = false; report.scrollSmoother.issues.push('missing smoother'); }
    else if (typeof smoother.scrollTop !== 'function') {
      report.scrollSmoother.pass = false; report.scrollSmoother.issues.push('scrollTop missing');
    }
  } else if (smoother) {
    report.scrollSmoother.pass = false; report.scrollSmoother.issues.push('smoother active on mobile');
  }

  const scrollY = window.scrollY || window.pageYOffset || 0;
  if (scrollY > 50) report.backToTop.issues.push('not at top, y='+scrollY);

  return report;
}
"""

MOBILE_TITLE_JS = """
() => {
  const titles = Array.from(document.querySelectorAll('.rr_title_anim')).filter(el => !el.closest('.banner-before'));
  const out = { count: titles.length, stuck: 0, invalidAfterRaf: 0, samples: [] };
  titles.forEach((el, i) => {
    const st = window.getComputedStyle(el);
    const r = el.getBoundingClientRect();
    let stObj = null;
    if (typeof ScrollTrigger !== 'undefined') {
      ScrollTrigger.getAll().forEach(t => { if (t.trigger === el) stObj = t; });
    }
    const sample = {
      i,
      hasSplit: !!el.querySelector('.line') || el.innerHTML.indexOf('<div') !== -1,
      opacity: parseFloat(st.opacity),
      start: stObj ? stObj.start : null,
      end: stObj ? stObj.end : null,
      isActive: stObj ? stObj.isActive : null
    };
    if (sample.opacity < 0.05 && r.top < window.innerHeight) out.stuck += 1;
    if (stObj && (stObj.start === 0 || stObj.end == null)) out.invalidAfterRaf += 1;
    if (i <= 2 || i >= titles.length - 1) out.samples.push(sample);
  });
  return out;
}
"""


def patch_main_js(body: str) -> str:
    if GEOM_SNAP.strip() not in body:
        body = body.replace(
            "function initTitleLine(splitTextLine) {",
            GEOM_SNAP + "\n        function initTitleLine(splitTextLine) {",
            1,
        )
    if GEOM_INJECT_MARKER in body and "__key" not in body.split(GEOM_INJECT_MARKER)[1][:800]:
        body = body.replace(
            GEOM_INJECT_MARKER,
            GEOM_INJECT_MARKER,
            1,
        )
        # inject after closing `});` of timeline - find first occurrence inside initTitleLine
        needle = """           });

           tl.from(itemSplitted.lines,"""
        if needle in body:
            body = body.replace(
                needle,
                """           });

""" + GEOM_INJECT_AFTER + """
           tl.from(itemSplitted.lines,""",
                1,
            )
    if SCHEDULE_PATCH_OLD in body and "window.__tel.logical.push" not in body:
        body = body.replace(SCHEDULE_PATCH_OLD, SCHEDULE_PATCH, 1)
    if FLUSH_PATCH_OLD in body and "window.__tel.flushes.push" not in body:
        body = body.replace(FLUSH_PATCH_OLD, FLUSH_PATCH, 1)
    if TIMEOUT_PATCH in body and "effective.push" not in body.split(TIMEOUT_PATCH)[1][:200]:
        body = body.replace(TIMEOUT_PATCH, TIMEOUT_PATCH_NEW, 1)
    return body


def classify_refresh_counts(tel, boot_ms=5000):
    main_boot = main_scroll = internal = 0
    for r in tel.get("refreshes", []):
        t = r.get("t", 0)
        phase = r.get("phase")
        if phase == "main":
            if t <= boot_ms:
                main_boot += 1
            else:
                main_scroll += 1
        elif phase in ("smoother", "internal"):
            internal += 1
    total = len(tel.get("refreshes", []))
    return {
        "main_boot": main_boot,
        "main_scroll": main_scroll,
        "internal": internal,
        "total": total,
    }


def origin_table(tel):
    logical = Counter()
    during_flush = Counter()
    for item in tel.get("logical", []):
        site = item.get("site", "other")
        logical[site] += 1
        if item.get("duringFlush"):
            during_flush[site] += 1

    eff_total = len(tel.get("effective", []))

    refresh_by_site = Counter()
    for r in tel.get("refreshes", []):
        if r.get("phase") != "main":
            continue
        stack = "\n".join(r.get("stack") or [])
        site = "scheduler"
        if "initFadeItem" in stack:
            site = "fade-top"
        elif "initTitleLine" in stack:
            site = "rr_title_anim"
        elif "initReturnReveal" in stack:
            site = "return"
        elif "initHeroSplit" in stack:
            site = "hero"
        refresh_by_site[site] += 1

    rows = {}
    for s in ("rr_title_anim", "fade-top", "return", "hero", "flush_batch_end"):
        rows[s] = {
            "logical": logical.get(s, 0),
            "during_flush": during_flush.get(s, 0),
            "effective": eff_total if s == "fade-top" and logical.get("fade-top", 0) else 0,
            "refreshes": refresh_by_site.get(s, 0),
        }
    rows["scheduler_total"] = {
        "logical": sum(logical.values()),
        "effective": eff_total,
        "refreshes": refresh_by_site.get("scheduler", 0),
    }
    return rows, eff_total, sum(logical.values())


def run_desktop_run(page, run_idx):
    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(5000)

    tel_boot = page.evaluate("() => JSON.parse(JSON.stringify(window.__tel || {}))")
    boot_counts = classify_refresh_counts(tel_boot)

    page.evaluate(SCROLL_JS, [0.45, 12])
    page.wait_for_timeout(3000)
    page.evaluate(SCROLL_JS, [0.75, 8])
    page.wait_for_timeout(2000)

    t3 = page.evaluate(T3_JS)
    geom = page.evaluate("() => window.__titleGeom || {}")
    for k, v in t3.items():
        geom.setdefault(k, []).append(v)

    smoke = page.evaluate(SMOKE_JS)

    page.evaluate(
        """() => {
        const smoother = (typeof ScrollSmoother !== 'undefined' && ScrollSmoother.get) ? ScrollSmoother.get() : null;
        if (smoother && typeof smoother.scrollTop === 'function') smoother.scrollTop(0);
        else window.scrollTo(0, 0);
    }"""
    )
    page.wait_for_timeout(1500)

    page.set_viewport_size({"width": 1200, "height": 800})
    page.wait_for_timeout(2000)
    resize_smoke = page.evaluate(SMOKE_JS)

    tel_final = page.evaluate("() => JSON.parse(JSON.stringify(window.__tel || {}))")
    final_counts = classify_refresh_counts(tel_final)

    return {
        "run": run_idx,
        "boot": boot_counts,
        "final": final_counts,
        "geom": geom,
        "t3": t3,
        "smoke": smoke,
        "resize_smoke": resize_smoke,
        "tel": tel_final,
    }


def run_mobile(page):
    page.goto(URL, wait_until="load", timeout=60000)
    page.wait_for_timeout(3000)
    page.evaluate(
        """() => {
        const max = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) - window.innerHeight;
        let y = 0;
        const step = max / 15;
        for (let i = 0; i < 15; i++) { y += step; window.scrollTo(0, y); }
    }"""
    )
    page.wait_for_timeout(2000)
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    mobile_titles = page.evaluate(MOBILE_TITLE_JS)
    tel = page.evaluate("() => JSON.parse(JSON.stringify(window.__tel || {}))")
    smoke = page.evaluate(SMOKE_JS)
    refreshes = len(tel.get("refreshes", []))
    return {"mobile_titles": mobile_titles, "refreshes": refreshes, "smoke": smoke}


def flatten_geom(geom):
    rows = []
    for key in ("A", "B", "C"):
        entries = geom.get(key, [])
        by_moment = {}
        for e in entries:
            by_moment[e.get("moment")] = e
        for moment in ("T1", "T2", "T3"):
            e = by_moment.get(moment, {})
            rows.append({
                "title": key,
                "moment": moment,
                "start": e.get("start"),
                "end": e.get("end"),
                "isActive": e.get("isActive"),
            })
    return rows


def t2_valid(geom):
    for key in ("A", "B", "C"):
        entries = geom.get(key, [])
        t2 = next((e for e in entries if e.get("moment") == "T2"), None)
        if not t2:
            return False, key
        start, end = t2.get("start"), t2.get("end")
        if start in (0, None) or end in (0, None):
            return False, key
    return True, None


def main():
    raw_main = MAIN_JS.read_text(encoding="utf-8")
    patched = patch_main_js(raw_main)

    results = {"desktop_runs": [], "mobile": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        def route_main(route):
            url = route.request.url
            if "/static/institutional/js/main.js" in url.split("?")[0]:
                route.fulfill(status=200, content_type="application/javascript", body=patched)
            else:
                route.continue_()

        context.route("**/static/institutional/js/main.js*", route_main)
        page = context.new_page()
        page.add_init_script(TELEMETRY_HEAD + INIT_HOOK)

        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        for i in range(1, 4):
            if i > 1:
                page.close()
                page = context.new_page()
                page.add_init_script(TELEMETRY_HEAD + INIT_HOOK)
                page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: console_errors.append(str(e)))
            results["desktop_runs"].append(run_desktop_run(page, i))

        page.close()
        mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_ctx.route("**/static/institutional/js/main.js*", route_main)
        mpage = mobile_ctx.new_page()
        mpage.add_init_script(TELEMETRY_HEAD + INIT_HOOK)
        results["mobile"] = run_mobile(mpage)
        browser.close()

    # filter cors
    gsap_errors = [e for e in console_errors if "gsap" in e.lower() or "scrolltrigger" in e.lower()]
    livia_cors = [e for e in console_errors if "livia" in e.lower() or "cors" in e.lower()]

    geom_run1 = results["desktop_runs"][0]["geom"]
    geom_rows = flatten_geom(geom_run1)
    t2_ok, fail_key = t2_valid(geom_run1)

    boot_vals = [r["final"]["main_boot"] for r in results["desktop_runs"]]
    scroll_vals = [r["final"]["main_scroll"] for r in results["desktop_runs"]]
    total_vals = [r["final"]["total"] for r in results["desktop_runs"]]

    tel_avg = defaultdict(list)
    for r in results["desktop_runs"]:
        tel = r["tel"]
        for item in tel.get("logical", []):
            tel_avg["logical"].append(item)
        for item in tel.get("effective", []):
            tel_avg["effective"].append(item)
        for item in tel.get("refreshes", []):
            tel_avg["refreshes"].append(item)

    merged_tel = {
        "logical": tel_avg["logical"],
        "effective": tel_avg["effective"],
        "refreshes": tel_avg["refreshes"],
    }
    origins, eff_total, logical_total = origin_table(merged_tel)

    out = {
        "geom_rows": geom_rows,
        "t2_ok": t2_ok,
        "t2_fail_key": fail_key,
        "desktop_runs_table": [
            {
                "run": r["run"],
                "main_boot": r["final"]["main_boot"],
                "main_scroll": r["final"]["main_scroll"],
                "total": r["final"]["total"],
            }
            for r in results["desktop_runs"]
        ],
        "averages": {
            "main_boot": statistics.mean(boot_vals),
            "main_scroll": statistics.mean(scroll_vals),
            "total": statistics.mean(total_vals),
        },
        "origins": origins,
        "logical_total": logical_total,
        "effective_total": eff_total,
        "coalesced": max(0, logical_total - eff_total),
        "smoke_run1": results["desktop_runs"][0]["smoke"],
        "smoke_resize": results["desktop_runs"][0]["resize_smoke"],
        "mobile": results["mobile"],
        "gsap_errors": gsap_errors,
        "livia_cors_count": len(livia_cors),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
