/* global chrome */
(function attachSmart360Api(globalScope) {
  const JSON_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
  };

  function normalizeBaseUrl(value) {
    return String(value || "").trim().replace(/\/+$/, "");
  }

  function readCookie(url, name) {
    return new Promise((resolve) => {
      if (!chrome.cookies) {
        resolve(null);
        return;
      }
      chrome.cookies.get({ url, name }, (cookie) => {
        resolve(cookie ? cookie.value : null);
      });
    });
  }

  class Smart360Api {
    constructor(baseUrl) {
      this.baseUrl = normalizeBaseUrl(baseUrl);
    }

    endpoint(path) {
      return `${this.baseUrl}${path}`;
    }

    async csrfToken() {
      return readCookie(this.baseUrl, "csrftoken");
    }

    async request(path, options = {}) {
      const method = options.method || "GET";
      const headers = { ...JSON_HEADERS, ...(options.headers || {}) };
      if (method !== "GET") {
        const csrfToken = await this.csrfToken();
        if (!csrfToken) {
          throw new Error("CSRF token não encontrado. Abra o Smart360 e faça login antes de iniciar.");
        }
        headers["X-CSRFToken"] = csrfToken;
      }
      const response = await fetch(this.endpoint(path), {
        method,
        headers,
        credentials: "include",
        body: options.body ? JSON.stringify(options.body) : undefined
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch (_error) {
        payload = {};
      }
      if (!response.ok) {
        const message = payload && payload.errors ? JSON.stringify(payload.errors) : `HTTP ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
      }
      return payload;
    }

    getSearchRun(id) {
      return this.request(`/painel/sales-intelligence/api/search-runs/${id}/`);
    }

    sendResults(id, results) {
      return this.request(`/painel/sales-intelligence/api/search-runs/${id}/results/`, {
        method: "POST",
        body: { results }
      });
    }

    completeSearchRun(id) {
      return this.request(`/painel/sales-intelligence/api/search-runs/${id}/complete/`, {
        method: "POST",
        body: {}
      });
    }

    failSearchRun(id, reason) {
      return this.request(`/painel/sales-intelligence/api/search-runs/${id}/fail/`, {
        method: "POST",
        body: { reason }
      });
    }

    cancelSearchRun(id) {
      return this.request(`/painel/sales-intelligence/api/search-runs/${id}/cancel/`, {
        method: "POST",
        body: {}
      });
    }
  }

  globalScope.Smart360Api = Smart360Api;
  globalScope.normalizeSmart360BaseUrl = normalizeBaseUrl;
})(typeof self !== "undefined" ? self : window);
