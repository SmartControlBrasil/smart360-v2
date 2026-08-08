(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};
  var config = namespace.config;
  var events = namespace.events;
  var state = namespace.state;

  function query(selector) {
    return document.querySelector(selector);
  }

  function setText(selector, value) {
    var element = query(selector);
    if (element) {
      element.textContent = value;
    }
  }

  function setBar(selector, value) {
    var element = query(selector);
    if (element) {
      element.style.width = Math.max(0, Math.min(100, value)) + "%";
    }
  }

  function getLevelProgress(currentState) {
    var levels = config.levels;
    var currentIndex = levels.findIndex(function (level) {
      return level.id === currentState.levelId;
    });
    var currentLevel = levels[currentIndex] || levels[0];
    var nextLevel = levels[currentIndex + 1];

    if (!nextLevel) {
      return 100;
    }

    return Math.round(((currentState.xp - currentLevel.minXp) / (nextLevel.minXp - currentLevel.minXp)) * 100);
  }

  function renderMissions(currentState) {
    var list = query(config.selectors.missionsList);
    if (!list) {
      return;
    }

    list.innerHTML = config.missions.map(function (mission) {
      var completed = currentState.completedMissions.indexOf(mission.id) !== -1;
      var progress = mission.requiredInteractions.filter(function (interactionId) {
        return currentState.completedInteractions.indexOf(interactionId) !== -1;
      }).length;
      var status = completed ? "Concluida" : progress > 0 ? "Em andamento" : "Disponivel";

      return [
        "<article class=\"experience-mission " + (completed ? "is-complete" : "") + "\">",
        "<span>" + status + "</span>",
        "<h3>" + mission.title + "</h3>",
        "<p>" + mission.description + "</p>",
        "<small>" + progress + "/" + mission.requiredInteractions.length + " etapas - recompensa: " + mission.reward + " XP</small>",
        "</article>"
      ].join("");
    }).join("");
  }

  function render(currentState) {
    var snapshot = currentState || state.getState();
    setText(config.selectors.points, snapshot.totalPoints);
    setText(config.selectors.level, snapshot.levelLabel);
    setText(config.selectors.xpLabel, snapshot.xp + " XP");
    setText(config.selectors.progressLabel, snapshot.progress + "%");
    setBar(config.selectors.xpBar, getLevelProgress(snapshot));
    setBar(config.selectors.progressBar, snapshot.progress);
    setText(config.selectors.audioButton, snapshot.audioEnabled ? "Audio on" : "Audio off");
    renderMissions(snapshot);
  }

  function showScoreFeedback(points) {
    var element = query(config.selectors.scoreFeedback);
    if (!element || !points) {
      return;
    }

    element.textContent = "+" + points + " XP";
    element.hidden = false;
    element.classList.remove("is-visible");
    window.requestAnimationFrame(function () {
      element.classList.add("is-visible");
    });
    window.setTimeout(function () {
      element.hidden = true;
      element.classList.remove("is-visible");
    }, 1200);
  }

  function showAchievement(achievement) {
    var element = query(config.selectors.achievement);
    if (!element || !achievement) {
      return;
    }

    setText("[data-experience-ui='achievement-title']", achievement.title);
    setText("[data-experience-ui='achievement-description']", achievement.description);
    setText("[data-experience-ui='achievement-points']", "+" + achievement.points + " XP");
    element.hidden = false;
    element.classList.add("is-visible");
    window.setTimeout(function () {
      element.hidden = true;
      element.classList.remove("is-visible");
    }, 4200);
  }


  function showAuthLock() {
    var element = query("[data-experience-ui='auth-lock']");
    if (!element) {
      return;
    }

    element.hidden = false;
    element.textContent = "Crie sua conta gratuita para comecar a experiencia.";
    window.setTimeout(function () {
      element.hidden = true;
    }, 3200);
  }

  function openMissions() {
    var panel = query(config.selectors.missionsPanel);
    if (panel) {
      panel.hidden = false;
      var closeButton = panel.querySelector("button");
      if (closeButton) {
        closeButton.focus();
      }
    }
  }

  function closeMissions() {
    var panel = query(config.selectors.missionsPanel);
    if (panel) {
      panel.hidden = true;
    }
  }

  function bindEvents() {
    events.on("experience:state-changed", function (event) {
      render(event.detail.state);
    });
    events.on("experience:points-added", function (event) {
      showScoreFeedback(event.detail.points);
    });
    events.on("experience:achievement-unlocked", function (event) {
      showAchievement(event.detail.achievement);
    });
    events.on("experience:auth-required", function () {
      showAuthLock();
    });
  }

  namespace.ui = {
    bindEvents: bindEvents,
    render: render,
    openMissions: openMissions,
    closeMissions: closeMissions
  };
})(window);
