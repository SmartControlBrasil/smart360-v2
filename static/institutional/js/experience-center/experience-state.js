(function (window) {
  "use strict";

  var namespace = window.Smart360Experience = window.Smart360Experience || {};
  var config = namespace.config;
  var events = namespace.events;
  var storage = namespace.storage;
  var state = null;

  function uniqueList(value) {
    return Array.isArray(value) ? value.filter(function (item, index, array) {
      return typeof item === "string" && array.indexOf(item) === index;
    }) : [];
  }

  function isAuthenticated() {
    return Boolean(config && config.auth && config.auth.authenticated);
  }

  function defaultState() {
    return {
      version: config.version,
      totalPoints: 0,
      xp: 0,
      levelId: config.levels[0].id,
      levelLabel: config.levels[0].label,
      visitedSections: [],
      completedInteractions: [],
      completedMissions: [],
      unlockedAchievements: [],
      audioEnabled: false,
      progress: 0,
      lastInteractionAt: null
    };
  }

  function sanitizeState(savedState) {
    var fallback = defaultState();

    if (!savedState || savedState.version !== config.version) {
      return fallback;
    }

    return {
      version: config.version,
      totalPoints: Number(savedState.totalPoints) || 0,
      xp: Number(savedState.xp) || 0,
      levelId: savedState.levelId || fallback.levelId,
      levelLabel: savedState.levelLabel || fallback.levelLabel,
      visitedSections: uniqueList(savedState.visitedSections),
      completedInteractions: uniqueList(savedState.completedInteractions),
      completedMissions: uniqueList(savedState.completedMissions),
      unlockedAchievements: uniqueList(savedState.unlockedAchievements),
      audioEnabled: Boolean(savedState.audioEnabled),
      progress: Number(savedState.progress) || 0,
      lastInteractionAt: savedState.lastInteractionAt || null
    };
  }

  function calculateLevel(xp) {
    return config.levels.reduce(function (current, level) {
      return xp >= level.minXp ? level : current;
    }, config.levels[0]);
  }

  function calculateProgress(nextState) {
    var interactionCount = nextState.completedInteractions.length;
    var missionCount = nextState.completedMissions.length;
    var achievementCount = nextState.unlockedAchievements.length;
    var target = 12;
    return Math.min(100, Math.round(((interactionCount + missionCount + achievementCount) / target) * 100));
  }

  function persist() {
    state.progress = calculateProgress(state);
    if (isAuthenticated()) {
      storage.save(state);
    }
    events.emit("experience:state-changed", { state: getState() });
  }

  function init() {
    state = sanitizeState(storage.load());
    persist();
    return getState();
  }

  function getState() {
    return JSON.parse(JSON.stringify(state || defaultState()));
  }

  function updateState(updater) {
    var draft = getState();
    var nextState = typeof updater === "function" ? updater(draft) : Object.assign(draft, updater || {});
    state = sanitizeState(nextState);
    persist();
    return getState();
  }

  function addPoints(points, context) {
    if (!isAuthenticated()) {
      events.emit("experience:auth-required", { context: context || {} });
      return getState();
    }

    var amount = Math.max(0, Number(points) || 0);
    if (!amount) {
      return getState();
    }

    var previousLevel = calculateLevel(state.xp);
    state.totalPoints += amount;
    state.xp += amount;
    state.lastInteractionAt = new Date().toISOString();

    var nextLevel = calculateLevel(state.xp);
    state.levelId = nextLevel.id;
    state.levelLabel = nextLevel.label;
    persist();

    events.emit("experience:points-added", {
      points: amount,
      context: context || {},
      state: getState()
    });

    if (previousLevel.id !== nextLevel.id) {
      events.emit("experience:level-up", {
        level: nextLevel,
        state: getState()
      });
    }

    return getState();
  }

  function registerInteraction(interaction) {
    if (!isAuthenticated()) {
      events.emit("experience:auth-required", { interaction: interaction || {} });
      return { state: getState(), accepted: false, locked: true };
    }

    var id = interaction && interaction.id;
    var once = Boolean(interaction && interaction.once);

    if (!id) {
      return { state: getState(), accepted: false };
    }

    if (once && state.completedInteractions.indexOf(id) !== -1) {
      return { state: getState(), accepted: false, duplicate: true };
    }

    state.completedInteractions.push(id);

    if (interaction.section && state.visitedSections.indexOf(interaction.section) === -1) {
      state.visitedSections.push(interaction.section);
    }

    state.lastInteractionAt = new Date().toISOString();
    persist();

    events.emit("experience:interaction", {
      interaction: interaction,
      state: getState()
    });

    if (interaction.points) {
      addPoints(interaction.points, { interactionId: id });
    }

    return { state: getState(), accepted: true };
  }

  function completeMission(missionId) {
    if (!isAuthenticated()) {
      events.emit("experience:auth-required", { missionId: missionId });
      return false;
    }

    var mission = config.missions.find(function (item) {
      return item.id === missionId;
    });

    if (!mission || state.completedMissions.indexOf(missionId) !== -1) {
      return false;
    }

    var isComplete = mission.requiredInteractions.every(function (interactionId) {
      return state.completedInteractions.indexOf(interactionId) !== -1;
    });

    if (!isComplete) {
      return false;
    }

    state.completedMissions.push(missionId);
    persist();
    addPoints(mission.reward, { missionId: missionId });
    events.emit("experience:mission-completed", { mission: mission, state: getState() });
    return true;
  }

  function unlockAchievement(achievementId) {
    if (!isAuthenticated()) {
      events.emit("experience:auth-required", { achievementId: achievementId });
      return false;
    }

    var achievement = config.achievements.find(function (item) {
      return item.id === achievementId;
    });

    if (!achievement || state.unlockedAchievements.indexOf(achievementId) !== -1) {
      return false;
    }

    state.unlockedAchievements.push(achievementId);
    persist();
    addPoints(achievement.points, { achievementId: achievementId });
    events.emit("experience:achievement-unlocked", { achievement: achievement, state: getState() });
    return true;
  }

  function evaluateMissions() {
    config.missions.forEach(function (mission) {
      completeMission(mission.id);
    });
  }

  function evaluateAchievements() {
    config.achievements.forEach(function (achievement) {
      var unlocked = false;

      if (achievement.interactionId) {
        unlocked = state.completedInteractions.indexOf(achievement.interactionId) !== -1;
      }

      if (achievement.requiredInteractions) {
        unlocked = achievement.requiredInteractions.every(function (interactionId) {
          return state.completedInteractions.indexOf(interactionId) !== -1;
        });
      }

      if (achievement.missionId) {
        unlocked = state.completedMissions.indexOf(achievement.missionId) !== -1;
      }

      if (unlocked) {
        unlockAchievement(achievement.id);
      }
    });
  }

  function setAudioEnabled(enabled) {
    if (!isAuthenticated()) {
      events.emit("experience:auth-required", { action: "audio" });
      return false;
    }

    state.audioEnabled = Boolean(enabled);
    persist();
    events.emit("experience:audio-changed", { enabled: state.audioEnabled, state: getState() });
    return state.audioEnabled;
  }

  function resetExperience() {
    storage.reset();
    state = defaultState();
    persist();
    events.emit("experience:state-reset", { state: getState() });
    return getState();
  }

  namespace.state = {
    init: init,
    getState: getState,
    updateState: updateState,
    addPoints: addPoints,
    registerInteraction: registerInteraction,
    completeMission: completeMission,
    unlockAchievement: unlockAchievement,
    evaluateMissions: evaluateMissions,
    evaluateAchievements: evaluateAchievements,
    resetExperience: resetExperience,
    setAudioEnabled: setAudioEnabled
  };
})(window);
