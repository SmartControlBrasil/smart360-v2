/* global chrome */
(function smart360GoogleMapsCollector() {
  const DEBUG = false;
  const COLLECTOR_VERSION = "0.1.0";
  const CONFIG = Object.freeze({
    mutationDebounceMs: 800,
    scrollIntervalMs: 1800,
    scrollStepRatio: 0.85,
    maxIdleCycles: 6,
    maxRuntimeMs: 12 * 60 * 1000,
    maxCardsPerScan: 80,
    endListTexts: [
      "you've reached the end of the list",
      "fim da lista",
      "você chegou ao final da lista"
    ]
  });

  let collector = null;

  function log(...args) {
    if (DEBUG) {
      console.log("[Smart360 Prospect]", ...args);
    }
  }

  function debounce(fn, waitMs) {
    let timer = null;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), waitMs);
    };
  }

  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function normalizeName(value) {
    return normalizeText(value).toLocaleLowerCase("pt-BR");
  }

  function normalizePhone(value) {
    let digits = String(value || "").replace(/\D/g, "");
    if (digits.startsWith("55") && (digits.length === 12 || digits.length === 13)) {
      digits = digits.slice(2);
    }
    return digits;
  }

  function parseAddressLocation(address) {
    const result = { city: "", state: "" };
    const text = normalizeText(address);
    const stateMatch = text.match(/(?:^|[\s,-])([A-Z]{2})(?:,|\s|$)/);
    if (stateMatch) {
      result.state = stateMatch[1];
    }
    const cityStateMatch = text.match(/,\s*([^,\-]+)\s*-\s*([A-Z]{2})(?:,|\s|$)/);
    if (cityStateMatch) {
      result.city = normalizeText(cityStateMatch[1]);
      result.state = cityStateMatch[2];
    }
    return result;
  }

  function absoluteUrl(href) {
    if (!href) {
      return "";
    }
    try {
      return new URL(href, window.location.href).href;
    } catch (_error) {
      return "";
    }
  }

  function getResultsFeed() {
    return document.querySelector('[role="feed"]')
      || document.querySelector('[aria-label*="Results for" i]')
      || document.querySelector('[aria-label*="Resultados para" i]');
  }

  function getScrollTarget() {
    const feed = getResultsFeed();
    if (feed && feed.scrollHeight > feed.clientHeight) {
      return feed;
    }
    const candidates = Array.from(document.querySelectorAll("div"));
    return candidates.find((node) => {
      const style = window.getComputedStyle(node);
      return /(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight && node.clientHeight > 300;
    }) || document.scrollingElement || document.documentElement;
  }

  function getVisibleCards() {
    const feed = getResultsFeed();
    const root = feed || document;
    const cards = Array.from(root.querySelectorAll('a[href*="/maps/place/"], a[href*="?cid="]'))
      .map((link) => link.closest('[role="article"]') || link.closest("div"))
      .filter(Boolean);
    return Array.from(new Set(cards)).slice(0, CONFIG.maxCardsPerScan);
  }

  function findPlaceLink(card) {
    return card.querySelector('a[href*="/maps/place/"]') || card.querySelector('a[href*="?cid="]');
  }

  function extractName(card, placeLink) {
    const aria = normalizeText(placeLink ? placeLink.getAttribute("aria-label") : "");
    if (aria) {
      return aria;
    }
    const heading = card.querySelector('[role="heading"], h1, h2, h3');
    if (heading) {
      return normalizeText(heading.textContent);
    }
    const text = normalizeText(card.textContent).split("·")[0];
    return text.split("\n")[0].slice(0, 180);
  }

  function extractWebsite(card) {
    const link = card.querySelector('a[href^="http"]:not([href*="google."]):not([href*="gstatic."])');
    return link ? absoluteUrl(link.getAttribute("href")) : "";
  }

  function extractPhone(text) {
    const phoneMatch = text.match(/(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?(?:9\s*)?\d{4}[\s.-]?\d{4}/);
    return phoneMatch ? normalizeText(phoneMatch[0]) : "";
  }

  function extractRating(text) {
    const ratingMatch = text.match(/\b([0-5][,.][0-9])\b/);
    return ratingMatch ? ratingMatch[1] : "";
  }

  function extractReviews(text) {
    const reviewsMatch = text.match(/\(?([0-9.]+)\)?\s*(?:reviews|avaliações)/i);
    return reviewsMatch ? reviewsMatch[1] : "";
  }

  function extractCategory(text) {
    const chunks = text.split("·").map(normalizeText).filter(Boolean);
    return chunks.find((chunk) => !/^[0-5][,.][0-9]/.test(chunk) && !/reviews|avaliações/i.test(chunk)) || "";
  }

  function extractAddress(text) {
    const lines = text.split("\n").map(normalizeText).filter(Boolean);
    return lines.find((line) => /\d/.test(line) && /rua|avenida|av\.?|rodovia|estrada|praça|r\.?\s/i.test(line)) || "";
  }

  function extractExternalId(url) {
    const cid = url.match(/[?&]cid=([^&]+)/);
    if (cid) {
      return `cid:${decodeURIComponent(cid[1])}`;
    }
    return "";
  }

  function extractBusinessFromCard(card) {
    const placeLink = findPlaceLink(card);
    const sourceUrl = absoluteUrl(placeLink ? placeLink.getAttribute("href") : "");
    const text = normalizeText(card.innerText || card.textContent || "");
    const name = extractName(card, placeLink);
    if (!name) {
      return null;
    }
    const address = extractAddress(text);
    const location = parseAddressLocation(address || text);
    return {
      name,
      phone: extractPhone(text),
      website: extractWebsite(card),
      address,
      city: location.city,
      state: location.state,
      source_url: sourceUrl,
      external_id: extractExternalId(sourceUrl),
      raw_data: {
        category: extractCategory(text),
        rating: extractRating(text),
        reviews: extractReviews(text),
        maps_text: text.slice(0, 1000),
        collector_version: COLLECTOR_VERSION
      }
    };
  }

  function dedupeKey(result) {
    if (result.external_id) {
      return `external:${result.external_id}`;
    }
    if (result.source_url) {
      return `url:${result.source_url}`;
    }
    const name = normalizeName(result.name);
    const phone = normalizePhone(result.phone);
    if (name && phone) {
      return `name-phone:${name}|${phone}`;
    }
    return result.address ? `name-address:${name}|${normalizeName(result.address)}` : `name:${name}`;
  }

  function isEndOfList() {
    const pageText = normalizeText(document.body.innerText).toLocaleLowerCase("pt-BR");
    return CONFIG.endListTexts.some((needle) => pageText.includes(needle));
  }

  function ensureOverlay() {
    let overlay = document.getElementById("smart360-prospect-overlay");
    if (overlay) {
      return overlay;
    }
    overlay = document.createElement("div");
    overlay.id = "smart360-prospect-overlay";
    overlay.style.cssText = [
      "position:fixed",
      "right:14px",
      "bottom:14px",
      "z-index:2147483647",
      "background:#16202a",
      "color:#fff",
      "font:12px Arial,sans-serif",
      "padding:8px 10px",
      "border-radius:6px",
      "box-shadow:0 6px 20px rgba(0,0,0,.2)",
      "max-width:220px"
    ].join(";");
    overlay.textContent = "Smart360 Prospect pronto";
    document.body.appendChild(overlay);
    return overlay;
  }

  function updateOverlay(text) {
    ensureOverlay().textContent = `Smart360 Prospect: ${text}`;
  }

  class MapsCollector {
    constructor(options) {
      this.options = options || {};
      this.seen = new Set();
      this.running = false;
      this.startedAt = 0;
      this.idleCycles = 0;
      this.scrollTimer = null;
      this.observer = null;
      this.scanDebounced = debounce(() => this.scan(), CONFIG.mutationDebounceMs);
    }

    start() {
      if (this.running) {
        return;
      }
      this.running = true;
      this.startedAt = Date.now();
      this.idleCycles = 0;
      updateOverlay("executando");
      this.installObserver();
      this.scan();
      this.scheduleScroll();
      log("collector started");
    }

    stop() {
      this.running = false;
      if (this.scrollTimer) {
        clearTimeout(this.scrollTimer);
      }
      if (this.observer) {
        this.observer.disconnect();
      }
      updateOverlay("pausado");
    }

    installObserver() {
      if (this.observer) {
        this.observer.disconnect();
      }
      const target = getResultsFeed() || document.body;
      this.observer = new MutationObserver(() => this.scanDebounced());
      this.observer.observe(target, { childList: true, subtree: true });
      log("feed detected");
    }

    scan() {
      if (!this.running) {
        return;
      }
      const cards = getVisibleCards();
      const results = [];
      for (const card of cards) {
        const result = extractBusinessFromCard(card);
        if (!result || !result.name) {
          continue;
        }
        const key = dedupeKey(result);
        if (this.seen.has(key)) {
          continue;
        }
        this.seen.add(key);
        results.push(result);
      }
      if (results.length) {
        this.idleCycles = 0;
        updateOverlay(`${this.seen.size} encontrados`);
        chrome.runtime.sendMessage({ type: "SMART360_RESULTS_FOUND", results }).catch(() => {});
      } else {
        this.idleCycles += 1;
      }
      this.checkStopConditions();
    }

    scheduleScroll() {
      if (!this.running) {
        return;
      }
      this.scrollTimer = setTimeout(() => {
        this.scrollOnce();
        this.scan();
        this.scheduleScroll();
      }, CONFIG.scrollIntervalMs);
    }

    scrollOnce() {
      const target = getScrollTarget();
      const step = Math.max(260, Math.floor((target.clientHeight || window.innerHeight) * CONFIG.scrollStepRatio));
      target.scrollBy({ top: step, behavior: "smooth" });
    }

    checkStopConditions() {
      const requestedLimit = Number(this.options.requestedLimit || 0);
      if (requestedLimit > 0 && this.seen.size >= requestedLimit) {
        this.complete("limite solicitado atingido");
        return;
      }
      if (isEndOfList()) {
        this.complete("fim da lista detectado");
        return;
      }
      if (this.idleCycles >= CONFIG.maxIdleCycles) {
        this.complete("sem novos resultados");
        return;
      }
      if (Date.now() - this.startedAt > CONFIG.maxRuntimeMs) {
        this.fail("timeout máximo de segurança atingido");
        return;
      }
      if (!/\/maps\//.test(window.location.pathname)) {
        this.fail("URL deixou de ser Google Maps");
      }
    }

    complete(reason) {
      this.stop();
      updateOverlay(`concluído: ${reason}`);
      chrome.runtime.sendMessage({ type: "SMART360_COLLECTOR_DONE", reason }).catch(() => {});
    }

    fail(reason) {
      this.stop();
      updateOverlay(`falha: ${reason}`);
      chrome.runtime.sendMessage({ type: "SMART360_COLLECTOR_ERROR", reason }).catch(() => {});
    }
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "SMART360_START_COLLECTING") {
      if (collector) {
        collector.stop();
      }
      collector = new MapsCollector(message.config || {});
      collector.start();
      sendResponse({ ok: true });
      return true;
    }
    if (message.type === "SMART360_PAUSE_COLLECTING" || message.type === "SMART360_STOP_COLLECTING") {
      if (collector) {
        collector.stop();
      }
      sendResponse({ ok: true });
      return true;
    }
    if (message.type === "SMART360_STATE" && message.state) {
      updateOverlay(`${message.state.status} · ${message.state.foundCount || 0} encontrados`);
      sendResponse({ ok: true });
      return true;
    }
    return false;
  });

  if (/\/maps\//.test(window.location.pathname)) {
    ensureOverlay();
    log("content script initialized");
  }
})();
