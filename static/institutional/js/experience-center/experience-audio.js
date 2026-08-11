(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};
  var config = namespace.config;
  var state = namespace.state;
  var currentAudio = null;
  var userInteracted = false;

  function log(message, error) {
    if (config.debug && window.console) {
      console.warn("[Experience Audio] " + message, error || "");
    }
  }

  function markInteraction() {
    userInteracted = true;
    document.removeEventListener("pointerdown", markInteraction);
    document.removeEventListener("keydown", markInteraction);
  }

  function init() {
    document.addEventListener("pointerdown", markInteraction, { once: true });
    document.addEventListener("keydown", markInteraction, { once: true });
  }

  function isEnabled() {
    return state.getState().audioEnabled && userInteracted;
  }

  function stopCurrent() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio = null;
    }
  }

  function play(audioId) {
    var src = config.audio.map[audioId];

    if (!src || !isEnabled()) {
      return;
    }

    stopCurrent();

    try {
      currentAudio = new Audio(src);
      currentAudio.volume = config.audio.volume;
      currentAudio.play().catch(function (error) {
        log("Áudio não reproduzido. Verifique o placeholder ou permissão do navegador.", error);
      });
    } catch (error) {
      log("Falha ao preparar áudio.", error);
    }
  }

  function toggle() {
    var enabled = state.setAudioEnabled(!state.getState().audioEnabled);
    if (!enabled) {
      stopCurrent();
    } else {
      play("click");
    }
    return enabled;
  }

  namespace.audio = {
    init: init,
    play: play,
    toggle: toggle,
    stopCurrent: stopCurrent
  };
})(window);
