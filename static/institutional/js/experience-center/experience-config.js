(function (window) {
  "use strict";

  window.Smart360Experience = window.Smart360Experience || {};

  window.Smart360Experience.config = {
    name: "Smart360 Experience Center",
    version: "0.1.0",
    debug: true,
    storageKey: "smart360_experience_center_v1",
    auth: {
      required: true,
      authenticated: false,
      loginUrl: "",
      signupUrl: "",
      playUrl: ""
    },
    audio: {
      enabled: true,
      volume: 0.7,
      map: {
        click: "/static/institutional/experience-center/audio/click-ui.mp3",
        points: "/static/institutional/experience-center/audio/points-earned.mp3",
        achievement: "/static/institutional/experience-center/audio/achievement-unlocked.mp3",
        missionComplete: "/static/institutional/experience-center/audio/mission-complete.mp3",
        levelUp: "/static/institutional/experience-center/audio/level-up.mp3",
        modalOpen: "/static/institutional/experience-center/audio/modal-open.mp3",
        liroIntro: "/static/institutional/experience-center/audio/liro-intro.mp3",
        ambient: "/static/institutional/experience-center/audio/ambient-loop.mp3"
      }
    },
    scoring: {
      cardOpened: 10,
      videoCompleted: 25,
      quizCompleted: 50,
      sectionCompleted: 30,
      liroMet: 15,
      interactionCompleted: 20
    },
    levels: [
      { id: "explorer", label: "Explorador", minXp: 0 },
      { id: "technician", label: "Tecnico", minXp: 40 },
      { id: "specialist", label: "Especialista", minXp: 90 },
      { id: "automation-master", label: "Mestre da Automacao", minXp: 150 }
    ],
    missions: [
      {
        id: "visit-three-areas",
        title: "Visitar tres areas",
        description: "Explore pelo menos tres areas do Experience Center.",
        reward: 30,
        requiredInteractions: ["experience-start", "robotics-card", "systems-interaction"]
      },
      {
        id: "open-technical-solution",
        title: "Abrir uma solucao tecnica",
        description: "Abra um card tecnico para conhecer uma solucao.",
        reward: 20,
        requiredInteractions: ["automation-card"]
      },
      {
        id: "complete-interaction",
        title: "Concluir uma interacao",
        description: "Conclua uma acao demonstrativa do centro.",
        reward: 25,
        requiredInteractions: ["systems-interaction"]
      },
      {
        id: "meet-liro",
        title: "Conhecer o Liro",
        description: "Ative o primeiro contato com o guia da experiencia.",
        reward: 15,
        requiredInteractions: ["meet-liro"]
      }
    ],
    achievements: [
      {
        id: "first-exploration",
        title: "Primeira Exploracao",
        description: "Voce iniciou a jornada pelo Experience Center.",
        points: 10,
        interactionId: "experience-start"
      },
      {
        id: "technology-curious",
        title: "Curioso por Tecnologia",
        description: "Voce abriu sua primeira solucao tecnica.",
        points: 15,
        interactionId: "automation-card"
      },
      {
        id: "industrial-connection",
        title: "Conexao Industrial",
        description: "Voce navegou por robotica e sistemas conectados.",
        points: 20,
        requiredInteractions: ["robotics-card", "systems-interaction"]
      },
      {
        id: "mission-complete",
        title: "Missao Cumprida",
        description: "Voce concluiu uma missao demonstrativa.",
        points: 20,
        missionId: "complete-interaction"
      }
    ],
    selectors: {
      root: "[data-experience-root]",
      action: "[data-experience-action]",
      audio: "[data-experience-audio]",
      points: "[data-experience-ui='points']",
      level: "[data-experience-ui='level']",
      xpBar: "[data-experience-ui='xp-bar']",
      xpLabel: "[data-experience-ui='xp-label']",
      progressBar: "[data-experience-ui='progress-bar']",
      progressLabel: "[data-experience-ui='progress-label']",
      missionsPanel: "[data-experience-ui='missions-panel']",
      missionsList: "[data-experience-ui='missions-list']",
      achievement: "[data-experience-ui='achievement']",
      scoreFeedback: "[data-experience-ui='score-feedback']",
      audioButton: "[data-experience-ui='audio-button']"
    },
    assets: {
      iconsBase: "/static/institutional/experience-center/icons/",
      imagesBase: "/static/institutional/experience-center/images/",
      animationsBase: "/static/institutional/experience-center/animations/",
      videoBase: "/static/institutional/experience-center/video/"
    }
  };
})(window);
