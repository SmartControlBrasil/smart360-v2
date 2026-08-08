(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};
  var config = namespace.config;

  function log(message, error) {
    if (config && config.debug && window.console) {
      console.warn("[Experience Storage] " + message, error || "");
    }
  }

  function isAuthenticated() {
    return Boolean(config && config.auth && config.auth.authenticated);
  }

  function isAvailable() {
    try {
      var key = "__smart360_storage_test__";
      window.localStorage.setItem(key, key);
      window.localStorage.removeItem(key);
      return true;
    } catch (error) {
      log("localStorage indisponivel.", error);
      return false;
    }
  }

  function load() {
    if (!isAuthenticated()) {
      reset();
      return null;
    }

    if (!isAvailable()) {
      return null;
    }

    try {
      var raw = window.localStorage.getItem(config.storageKey);
      if (!raw) {
        return null;
      }

      var parsed = JSON.parse(raw);
      if (!parsed || parsed.version !== config.version || typeof parsed.totalPoints !== "number") {
        return null;
      }

      return parsed;
    } catch (error) {
      log("Estado salvo invalido. Um novo estado sera criado.", error);
      reset();
      return null;
    }
  }

  function save(state) {
    if (!isAuthenticated()) {
      return false;
    }

    if (!isAvailable()) {
      return false;
    }

    try {
      window.localStorage.setItem(config.storageKey, JSON.stringify(state));
      return true;
    } catch (error) {
      log("Nao foi possivel salvar o estado.", error);
      return false;
    }
  }

  function reset() {
    if (!isAvailable()) {
      return false;
    }

    try {
      window.localStorage.removeItem(config.storageKey);
      return true;
    } catch (error) {
      log("Nao foi possivel limpar o estado.", error);
      return false;
    }
  }

  namespace.storage = {
    load: load,
    save: save,
    reset: reset
  };
})(window);
