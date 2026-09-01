/* global chrome, Smart360Api, normalizeSmart360BaseUrl */
importScripts("lib/smart360_api.js");

const DEBUG = false;
const VERSION = "0.1.0";
const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const STATE_KEY = "smart360ProspectState";
const SETTINGS_KEY = "smart360ProspectSettings";
const BATCH_SIZE = 10;
const MAX_RETRIES = 3;
const RETRY_DELAYS_MS = [1000, 2000, 5000];
const MAX_PENDING_BEFORE_FLUSH = BATCH_SIZE;
const STATUS = Object.freeze({
  IDLE: "IDLE",
  RUNNING: "RUNNING",
  PAUSED: "PAUSED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED"
});

let state = defaultState();
let settings = { baseUrl: DEFAULT_BASE_URL };
let flushInFlight = false;

function log(...args) {
  if (DEBUG) {
    console.log("[Smart360 Prospect]", ...args);
  }
}

function defaultState() {
  return {
    status: STATUS.IDLE,
    searchRunId: "",
    query: "",
    mapsTabId: null,
    foundCount: 0,
    sentCount: 0,
    duplicateCount: 0,
    errorCount: 0,
    pending: [],
    seenKeys: [],
    requestedLimit: null,
    lastActivity: "",
    lastError: "",
    updatedAt: null,
    startedAt: null,
    completedAt: null
  };
}

function nowIso() {
  return new Date().toISOString();
}

async function storageGet(keys) {
  return chrome.storage.local.get(keys);
}

async function storageSet(values) {
  return chrome.storage.local.set(values);
}

async function loadState() {
  const stored = await storageGet([STATE_KEY, SETTINGS_KEY]);
  state = { ...defaultState(), ...(stored[STATE_KEY] || {}) };
  settings = { baseUrl: DEFAULT_BASE_URL, ...(stored[SETTINGS_KEY] || {}) };
}

async function persistState(partial = {}) {
  state = { ...state, ...partial, updatedAt: nowIso() };
  await storageSet({ [STATE_KEY]: state });
  broadcastState();
}

async function persistSettings(partial = {}) {
  settings = { ...settings, ...partial };
  settings.baseUrl = normalizeSmart360BaseUrl(settings.baseUrl || DEFAULT_BASE_URL);
  await storageSet({ [SETTINGS_KEY]: settings });
}

function broadcastState() {
  chrome.runtime.sendMessage({ type: "SMART360_STATE", state, settings }).catch(() => {});
  if (state.mapsTabId) {
    chrome.tabs.sendMessage(state.mapsTabId, { type: "SMART360_STATE", state }).catch(() => {});
  }
}

function api() {
  return new Smart360Api(settings.baseUrl || DEFAULT_BASE_URL);
}

function normalizeName(value) {
  return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase("pt-BR");
}

function normalizePhone(value) {
  let digits = String(value || "").replace(/\D/g, "");
  if (digits.startsWith("55") && (digits.length === 12 || digits.length === 13)) {
    digits = digits.slice(2);
  }
  return digits;
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
  if (name && result.address) {
    return `name-address:${name}|${normalizeName(result.address)}`;
  }
  return name ? `name:${name}` : "";
}

function isValidResult(result) {
  return result && normalizeName(result.name);
}

function rememberSeen(keys) {
  const compact = keys.slice(-1000);
  return compact;
}

async function addResults(results) {
  if (state.status !== STATUS.RUNNING) {
    return;
  }
  const seen = new Set(state.seenKeys || []);
  const pending = [...(state.pending || [])];
  let foundDelta = 0;
  let duplicateDelta = 0;
  let lastActivity = state.lastActivity;

  for (const result of results || []) {
    if (!isValidResult(result)) {
      continue;
    }
    const key = dedupeKey(result);
    if (!key || seen.has(key)) {
      duplicateDelta += 1;
      continue;
    }
    seen.add(key);
    pending.push(result);
    foundDelta += 1;
    lastActivity = result.name;
  }

  if (!foundDelta && !duplicateDelta) {
    return;
  }
  await persistState({
    pending,
    seenKeys: rememberSeen(Array.from(seen)),
    foundCount: state.foundCount + foundDelta,
    duplicateCount: state.duplicateCount + duplicateDelta,
    lastActivity
  });
  if (state.pending.length >= MAX_PENDING_BEFORE_FLUSH) {
    await flushPending();
  }
}

async function flushPending(options = {}) {
  const force = Boolean(options.force);
  if (flushInFlight || (!force && state.status !== STATUS.RUNNING) || !state.searchRunId || !state.pending.length) {
    return;
  }
  flushInFlight = true;
  try {
    while (state.pending.length && state.status === STATUS.RUNNING) {
      const batch = state.pending.slice(0, BATCH_SIZE);
      await sendBatchWithRetry(batch);
      await persistState({
        pending: state.pending.slice(batch.length),
        sentCount: state.sentCount + batch.length,
        lastError: ""
      });
    }
  } finally {
    flushInFlight = false;
  }
}

async function sendBatchWithRetry(batch) {
  let lastError = null;
  for (let attempt = 0; attempt < MAX_RETRIES; attempt += 1) {
    try {
      await api().sendResults(state.searchRunId, batch);
      log("batch sent", batch.length);
      return;
    } catch (error) {
      lastError = error;
      await persistState({ errorCount: state.errorCount + 1, lastError: error.message });
      await delay(RETRY_DELAYS_MS[attempt] || RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - 1]);
    }
  }
  await persistState({ status: STATUS.PAUSED, lastError: `Falha ao enviar lote: ${lastError ? lastError.message : "erro desconhecido"}` });
  throw lastError;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mapsSearchUrl(query) {
  const encoded = encodeURIComponent(query || "");
  return `https://www.google.com/maps/search/${encoded}`;
}

async function getActiveMapsTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (tab && /^https:\/\/www\.google\.(com|com\.br)\/maps\//.test(tab.url || "")) {
    return tab;
  }
  return null;
}

async function openMaps(query) {
  const activeMapsTab = await getActiveMapsTab();
  if (activeMapsTab) {
    if (query) {
      await chrome.tabs.update(activeMapsTab.id, { url: mapsSearchUrl(query), active: true });
    }
    return activeMapsTab.id;
  }
  const tab = await chrome.tabs.create({ url: mapsSearchUrl(query), active: true });
  return tab.id;
}

async function startCollection(input) {
  const baseUrl = normalizeSmart360BaseUrl(input.baseUrl || settings.baseUrl || DEFAULT_BASE_URL);
  const searchRunId = String(input.searchRunId || "").trim();
  const query = String(input.query || "").trim();
  if (!searchRunId) {
    throw new Error("Informe o SearchRun ID.");
  }
  if (!query) {
    throw new Error("Informe a busca do Google Maps.");
  }
  await persistSettings({ baseUrl });
  const run = await api().getSearchRun(searchRunId);
  if (run.status !== "RUNNING") {
    throw new Error(`SearchRun precisa estar RUNNING. Status atual: ${run.status}`);
  }
  const mapsTabId = await openMaps(query);
  await persistState({
    ...defaultState(),
    status: STATUS.RUNNING,
    searchRunId,
    query,
    mapsTabId,
    requestedLimit: run.requested_limit,
    startedAt: nowIso(),
    lastActivity: "Busca iniciada",
    lastError: ""
  });
  setTimeout(() => sendStartToContent(mapsTabId), 2000);
}

function sendStartToContent(tabId) {
  chrome.tabs.sendMessage(tabId, {
    type: "SMART360_START_COLLECTING",
    config: {
      query: state.query,
      requestedLimit: state.requestedLimit,
      collectorVersion: VERSION
    }
  }).catch(async (error) => {
    await persistState({ status: STATUS.FAILED, lastError: `Content script indisponível: ${error.message}` });
  });
}

async function pauseCollection() {
  await persistState({ status: STATUS.PAUSED, lastActivity: "Pausado pelo usuário" });
  if (state.mapsTabId) {
    chrome.tabs.sendMessage(state.mapsTabId, { type: "SMART360_PAUSE_COLLECTING" }).catch(() => {});
  }
}

async function resumeCollection() {
  if (!state.searchRunId || !state.query || !state.mapsTabId) {
    throw new Error("Não há coleta pausada para retomar.");
  }
  await persistState({ status: STATUS.RUNNING, lastActivity: "Retomado pelo usuário", lastError: "" });
  sendStartToContent(state.mapsTabId);
  await flushPending();
}

async function completeCollection() {
  await flushPending({ force: true });
  if (state.searchRunId) {
    await api().completeSearchRun(state.searchRunId);
  }
  await persistState({ status: STATUS.COMPLETED, completedAt: nowIso(), lastActivity: "SearchRun finalizada" });
  if (state.mapsTabId) {
    chrome.tabs.sendMessage(state.mapsTabId, { type: "SMART360_STOP_COLLECTING" }).catch(() => {});
  }
}

async function failCollection(reason) {
  if (state.searchRunId) {
    await api().failSearchRun(state.searchRunId, reason || state.lastError || "Falha na extensão Smart360 Prospect");
  }
  await persistState({ status: STATUS.FAILED, lastError: reason || state.lastError });
}

async function cancelCollection() {
  if (state.searchRunId) {
    await api().cancelSearchRun(state.searchRunId);
  }
  await persistState({ status: STATUS.IDLE, lastActivity: "SearchRun cancelada pelo usuário" });
  if (state.mapsTabId) {
    chrome.tabs.sendMessage(state.mapsTabId, { type: "SMART360_STOP_COLLECTING" }).catch(() => {});
  }
}

async function handleMessage(message) {
  switch (message.type) {
    case "SMART360_GET_STATE":
      return { state, settings };
    case "SMART360_START":
      await startCollection(message.payload || {});
      return { state, settings };
    case "SMART360_PAUSE":
      await pauseCollection();
      return { state, settings };
    case "SMART360_RESUME":
      await resumeCollection();
      return { state, settings };
    case "SMART360_COMPLETE":
      await completeCollection();
      return { state, settings };
    case "SMART360_CANCEL":
      await cancelCollection();
      return { state, settings };
    case "SMART360_RESULTS_FOUND":
      await addResults(message.results || []);
      return { state, settings };
    case "SMART360_COLLECTOR_DONE":
      await flushPending();
      await completeCollection();
      return { state, settings };
    case "SMART360_COLLECTOR_ERROR":
      await failCollection(message.reason || "Falha no coletor do Google Maps");
      return { state, settings };
    default:
      return { state, settings };
  }
}

chrome.runtime.onInstalled.addListener(() => {
  loadState().then(() => persistSettings(settings));
});

chrome.runtime.onStartup.addListener(() => {
  loadState();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message)
    .then((response) => sendResponse(response))
    .catch((error) => {
      persistState({ lastError: error.message, errorCount: state.errorCount + 1 }).finally(() => {
        sendResponse({ error: error.message, state, settings });
      });
    });
  return true;
});

loadState();
