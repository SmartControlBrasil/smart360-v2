(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};
  var config = namespace.config;
  var events = namespace.events;
  var state = namespace.state;
  var audio = namespace.audio;
  var ui = namespace.ui;
  var authRequiredActions = {
    "open-card": true,
    "complete-interaction": true,
    "meet-liro": true,
    start: true,
    "start-experience": true,
    reset: true,
    "open-missions": true,
    "close-missions": true
  };

  function configureAuth(root) {
    var authenticated = root.dataset.experienceAuthenticated === "true";
    config.auth.authenticated = authenticated;
    config.auth.loginUrl = root.getAttribute("data-experience-login-url") || "";
    config.auth.signupUrl = root.getAttribute("data-experience-signup-url") || "";
    config.auth.playUrl = root.getAttribute("data-experience-play-url") || "";
  }

  function requireAuth(context) {
    if (!config.auth.required || config.auth.authenticated) {
      return true;
    }

    events.emit("experience:auth-required", { context: context || {} });
    return false;
  }

  function closestAction(target) {
    return target.closest(config.selectors.action + ", " + config.selectors.audio);
  }

  function parsePoints(element) {
    return Number(element.getAttribute("data-experience-points")) || 0;
  }

  function currentSection(element) {
    var section = element.closest("[data-experience-section]");
    return section ? section.getAttribute("data-experience-section") : null;
  }

  function handleAction(element) {
    var audioToggle = element.getAttribute("data-experience-audio");
    var action = element.getAttribute("data-experience-action");
    var requiresAuth = Boolean(audioToggle === "toggle" || authRequiredActions[action]);

    if (requiresAuth && !requireAuth({ action: action || audioToggle })) {
      return;
    }

    if (audioToggle === "toggle") {
      audio.toggle();
      return;
    }

    if (action === "start-experience") {
      window.location.assign(element.getAttribute("data-experience-play-url") || config.auth.playUrl);
      return;
    }

    if (action === "open-missions") {
      ui.openMissions();
      audio.play("modalOpen");
      return;
    }

    if (action === "close-missions") {
      ui.closeMissions();
      audio.play("click");
      return;
    }

    if (action === "reset") {
      state.resetExperience();
      audio.stopCurrent();
      return;
    }

    var result = state.registerInteraction({
      id: element.getAttribute("data-experience-id"),
      action: action,
      points: parsePoints(element),
      once: element.getAttribute("data-experience-once") === "true",
      mission: element.getAttribute("data-experience-mission"),
      section: currentSection(element)
    });

    if (result.accepted) {
      audio.play(action === "meet-liro" ? "liroIntro" : "click");
      state.evaluateMissions();
      state.evaluateAchievements();
    }
  }

  function bindDelegatedEvents() {
    document.addEventListener("click", function (event) {
      var actionElement = closestAction(event.target);
      if (!actionElement) {
        return;
      }
      handleAction(actionElement);
    });
  }

  function bindExperienceEvents() {
    events.on("experience:mission-completed", function () {
      audio.play("missionComplete");
      state.evaluateAchievements();
    });
    events.on("experience:achievement-unlocked", function () {
      audio.play("achievement");
    });
    events.on("experience:level-up", function () {
      audio.play("levelUp");
    });
  }

  function init() {
    var root = document.querySelector(config.selectors.root);
    if (!root) {
      return;
    }

    configureAuth(root);
    state.init();
    audio.init();
    ui.bindEvents();
    ui.render(state.getState());
    bindDelegatedEvents();
    bindExperienceEvents();
    events.emit("experience:ready", { state: state.getState() });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
