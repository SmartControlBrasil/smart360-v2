(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};

  function emit(eventName, detail) {
    document.dispatchEvent(new CustomEvent(eventName, {
      detail: detail || {},
      bubbles: false
    }));
  }

  function on(eventName, callback) {
    document.addEventListener(eventName, callback);
  }

  namespace.events = {
    emit: emit,
    on: on
  };
})(window);
