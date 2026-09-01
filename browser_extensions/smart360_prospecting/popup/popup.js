/* global chrome */
const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

const fields = {
  baseUrl: document.getElementById("base-url"),
  searchRunId: document.getElementById("search-run-id"),
  query: document.getElementById("query")
};

const output = {
  dot: document.getElementById("status-dot"),
  status: document.getElementById("status"),
  foundCount: document.getElementById("found-count"),
  sentCount: document.getElementById("sent-count"),
  pendingCount: document.getElementById("pending-count"),
  duplicateCount: document.getElementById("duplicate-count"),
  errorCount: document.getElementById("error-count"),
  lastActivity: document.getElementById("last-activity"),
  lastError: document.getElementById("last-error")
};

const buttons = {
  start: document.getElementById("start"),
  pause: document.getElementById("pause"),
  resume: document.getElementById("resume"),
  complete: document.getElementById("complete"),
  cancel: document.getElementById("cancel")
};

function send(type, payload = {}) {
  return chrome.runtime.sendMessage({ type, payload });
}

function statePayload() {
  return {
    baseUrl: fields.baseUrl.value || DEFAULT_BASE_URL,
    searchRunId: fields.searchRunId.value,
    query: fields.query.value
  };
}

function render(response) {
  const state = response && response.state ? response.state : {};
  const settings = response && response.settings ? response.settings : {};
  fields.baseUrl.value = settings.baseUrl || fields.baseUrl.value || DEFAULT_BASE_URL;
  fields.searchRunId.value = state.searchRunId || fields.searchRunId.value || "";
  fields.query.value = state.query || fields.query.value || "";

  const status = state.status || "IDLE";
  output.status.textContent = status;
  output.foundCount.textContent = state.foundCount || 0;
  output.sentCount.textContent = state.sentCount || 0;
  output.pendingCount.textContent = state.pending ? state.pending.length : 0;
  output.duplicateCount.textContent = state.duplicateCount || 0;
  output.errorCount.textContent = state.errorCount || 0;
  output.lastActivity.textContent = state.lastActivity || "Pronto para iniciar.";
  output.lastError.hidden = !state.lastError;
  output.lastError.textContent = state.lastError || "";

  output.dot.className = `dot dot-${status.toLocaleLowerCase("pt-BR")}`;
  buttons.start.disabled = status === "RUNNING";
  buttons.pause.disabled = status !== "RUNNING";
  buttons.resume.disabled = status !== "PAUSED";
  buttons.complete.disabled = !["RUNNING", "PAUSED"].includes(status);
  buttons.cancel.disabled = !["RUNNING", "PAUSED", "FAILED"].includes(status);
}

async function command(type, payload = {}) {
  const response = await send(type, payload);
  render(response);
}

buttons.start.addEventListener("click", () => command("SMART360_START", statePayload()));
buttons.pause.addEventListener("click", () => command("SMART360_PAUSE"));
buttons.resume.addEventListener("click", () => command("SMART360_RESUME"));
buttons.complete.addEventListener("click", () => command("SMART360_COMPLETE"));
buttons.cancel.addEventListener("click", () => command("SMART360_CANCEL"));

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "SMART360_STATE") {
    render(message);
  }
});

command("SMART360_GET_STATE").catch((error) => {
  output.lastError.hidden = false;
  output.lastError.textContent = error.message;
});
