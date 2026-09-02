(function ($) {
  "use strict";

  function isHomePage() {
    var path = window.location.pathname || "/";
    return path === "/" || path === "/index.html";
  }

  var swiperScriptPromise = null;
  var SWIPER_SCRIPT_SRC = "/static/institutional/js/plugins/swiper.min.js";

  function loadSwiperScript() {
    if (typeof window.Swiper !== "undefined") {
      return Promise.resolve(window.Swiper);
    }

    if (swiperScriptPromise) {
      return swiperScriptPromise;
    }

    swiperScriptPromise = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = SWIPER_SCRIPT_SRC;
      script.async = true;
      script.onload = function () {
        if (typeof window.Swiper !== "undefined") {
          resolve(window.Swiper);
          return;
        }

        swiperScriptPromise = null;
        reject(new Error("Swiper unavailable after load"));
      };
      script.onerror = function () {
        swiperScriptPromise = null;
        reject(new Error("Swiper script failed"));
      };
      document.head.appendChild(script);
    });

    return swiperScriptPromise;
  }

  var externalScriptPromises = {};

  function loadExternalScript(src) {
    if (externalScriptPromises[src]) {
      return externalScriptPromises[src];
    }

    externalScriptPromises[src] = new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = function () {
        resolve();
      };
      script.onerror = function () {
        externalScriptPromises[src] = null;
        reject(new Error("Script failed: " + src));
      };
      document.head.appendChild(script);
    });

    return externalScriptPromises[src];
  }

  function loadInstitutionalScript(relativePath) {
    return loadExternalScript("/static/institutional/js/" + relativePath);
  }

  function ensureSplitTextReady(callback) {
    if (pluginAvailable("SplitText")) {
      callback();
      return;
    }

    loadInstitutionalScript("plugins/SplitText.js")
      .then(callback)
      .catch(function () {
        /* keep static text visible */
      });
  }

  function ensureChromaReady(callback) {
    if (pluginAvailable("chroma")) {
      callback();
      return;
    }

    loadInstitutionalScript("vendor/chroma.min.js")
      .then(callback)
      .catch(function () {
        /* keep static footer text visible */
      });
  }

  function createSwiper(selector, options) {
    if (typeof Swiper === "undefined" || !document.querySelector(selector)) {
      return null;
    }
    return new window.Swiper(selector, options);
  }

  function createLazySwiper(selector, options, rootMargin) {
    var element = document.querySelector(selector);
    if (!element) {
      return null;
    }

    var lazyRootMargin = rootMargin || "600px 0px";

    function initSwiperInstance() {
      if (element.classList.contains("swiper-initialized")) {
        return;
      }

      if (typeof window.Swiper === "undefined") {
        return;
      }

      new window.Swiper(selector, options);
    }

    function scheduleSwiperInit() {
      loadSwiperScript()
        .then(function () {
          initSwiperInstance();
        })
        .catch(function () {
          /* keep static carousel markup visible */
        });
    }

    if (typeof IntersectionObserver === "undefined") {
      scheduleSwiperInit();
      return null;
    }

    observeOnce(element, scheduleSwiperInit, lazyRootMargin);

    return null;
  }

  function pluginAvailable(name) {
    return typeof window[name] !== "undefined";
  }

  var mobileMediaQuery = window.matchMedia ? window.matchMedia("(max-width: 767px)") : null;

  function isMobile() {
    return mobileMediaQuery ? mobileMediaQuery.matches : window.innerWidth <= 767;
  }

  var gsapBootstrapStarted = false;

  function isHomeMobileGsapDeferred() {
    return isHomePage() && isMobile() && !gsapBootstrapStarted;
  }

  var scrollTriggerRefreshTimeout = null;
  var scrollTriggerRefreshRaf = null;
  var scrollTriggerRefreshPending = false;
  var scrollTriggerRefreshScrollEndBound = false;
  var SCROLL_TRIGGER_REFRESH_DELAY_MS = 100;

  function bindScrollTriggerRefreshOnScrollEnd() {
    if (scrollTriggerRefreshScrollEndBound || !pluginAvailable("ScrollTrigger")) {
      return;
    }

    scrollTriggerRefreshScrollEndBound = true;
    ScrollTrigger.addEventListener("scrollEnd", flushScheduledScrollTriggerRefresh);
  }

  function isScrollSmootherScrolling() {
    return usesScrollSmootherLayout()
      && pluginAvailable("ScrollTrigger")
      && ScrollTrigger.isScrolling
      && ScrollTrigger.isScrolling();
  }

  function runDebouncedScrollTriggerRefresh() {
    if (isHomeMobileGsapDeferred()) {
      return;
    }

    if (scrollTriggerRefreshTimeout != null) {
      clearTimeout(scrollTriggerRefreshTimeout);
      scrollTriggerRefreshTimeout = null;
    }

    if (scrollTriggerRefreshRaf != null) {
      cancelAnimationFrame(scrollTriggerRefreshRaf);
      scrollTriggerRefreshRaf = null;
    }

    scrollTriggerRefreshTimeout = setTimeout(function () {
      scrollTriggerRefreshTimeout = null;
      scrollTriggerRefreshRaf = requestAnimationFrame(function () {
        scrollTriggerRefreshRaf = null;
        scrollTriggerRefreshPending = false;
        if (pluginAvailable("ScrollTrigger")) {
          ScrollTrigger.refresh();
        }
      });
    }, SCROLL_TRIGGER_REFRESH_DELAY_MS);
  }

  function flushScheduledScrollTriggerRefresh() {
    if (!scrollTriggerRefreshPending) {
      return;
    }

    if (isScrollSmootherScrolling()) {
      return;
    }

    runDebouncedScrollTriggerRefresh();
  }

  function scheduleScrollTriggerRefresh() {
    if (!pluginAvailable("ScrollTrigger")) {
      return;
    }

    if (isHomeMobileGsapDeferred()) {
      return;
    }

    if (viewportInitFlushInProgress) {
      viewportInitRefreshRequested = true;
      return;
    }

    scrollTriggerRefreshPending = true;
    bindScrollTriggerRefreshOnScrollEnd();

    if (isScrollSmootherScrolling()) {
      return;
    }

    runDebouncedScrollTriggerRefresh();
  }

  function parseRootMarginPx(rootMargin, fallback) {
    if (!rootMargin) {
      return fallback || 320;
    }

    var match = String(rootMargin).match(/(-?\d+)/);
    return match ? parseInt(match[1], 10) : (fallback || 320);
  }

  function usesScrollSmootherLayout() {
    return !isMobile()
      && document.querySelector("#smooth-wrapper")
      && document.querySelector("#smooth-content");
  }

  function isWithinExpandedViewport(element, marginPx) {
    var node = element instanceof jQuery ? element[0] : element;
    if (!node || typeof node.getBoundingClientRect !== "function") {
      return false;
    }

    var rect = node.getBoundingClientRect();
    var margin = marginPx || 0;
    return rect.top < window.innerHeight + margin && rect.bottom > -margin;
  }

  function hasEnteredLazyZone(element, marginPx) {
    var node = element instanceof jQuery ? element[0] : element;
    if (!node || typeof node.getBoundingClientRect !== "function") {
      return false;
    }

    var rect = node.getBoundingClientRect();
    var margin = marginPx || 0;
    return rect.top <= window.innerHeight + margin;
  }

  var pendingViewportInits = [];
  var viewportInitListenersBound = false;
  var viewportInitFlushScheduled = false;
  var viewportInitFlushInProgress = false;
  var viewportInitRefreshRequested = false;

  function flushPendingViewportInits() {
    if (!pendingViewportInits.length) {
      return;
    }

    viewportInitFlushInProgress = true;
    viewportInitRefreshRequested = false;

    try {
      pendingViewportInits = pendingViewportInits.filter(function (item) {
        if (!item.element || item.done) {
          return false;
        }

        if (hasEnteredLazyZone(item.element, item.marginPx)) {
          item.done = true;
          item.callback(item.element);
          return false;
        }

        return true;
      });
    } finally {
      viewportInitFlushInProgress = false;
    }

    if (viewportInitRefreshRequested) {
      viewportInitRefreshRequested = false;
      scheduleScrollTriggerRefresh();
    }
  }

  function schedulePendingViewportInitFlush() {
    if (viewportInitFlushScheduled) {
      return;
    }

    if (isScrollSmootherScrolling()) {
      return;
    }

    viewportInitFlushScheduled = true;
    requestAnimationFrame(function () {
      viewportInitFlushScheduled = false;
      flushPendingViewportInits();
    });
  }

  function bindViewportInitListeners() {
    if (viewportInitListenersBound || !pluginAvailable("ScrollTrigger")) {
      return;
    }

    viewportInitListenersBound = true;
    ScrollTrigger.addEventListener("scroll", schedulePendingViewportInitFlush);
    ScrollTrigger.addEventListener("scrollEnd", flushPendingViewportInits);
    window.addEventListener("scroll", schedulePendingViewportInitFlush, { passive: true });
    window.addEventListener("resize", flushPendingViewportInits);
    schedulePendingViewportInitFlush();
  }

  function observeOnce(element, callback, rootMargin) {
    if (!element || typeof callback !== "function") {
      return;
    }

    var marginPx = parseRootMarginPx(rootMargin, 320);

    if (usesScrollSmootherLayout()) {
      pendingViewportInits.push({
        element: element,
        callback: callback,
        marginPx: marginPx,
        done: false
      });
      bindViewportInitListeners();
      schedulePendingViewportInitFlush();
      return;
    }

    if (typeof IntersectionObserver === "undefined") {
      callback(element);
      return;
    }

    var observer = new IntersectionObserver(function (entries, currentObserver) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) {
          return;
        }

        currentObserver.unobserve(entry.target);
        callback(entry.target);
      });
    }, {
      rootMargin: rootMargin || "320px 0px",
      threshold: 0.01
    });

    observer.observe(element);
  }

  function applyDataBackground(element) {
    var node = element instanceof jQuery ? element[0] : element;
    if (!node) {
      return;
    }

    var background = node.getAttribute("data-background");
    if (!background) {
      return;
    }

    node.style.backgroundImage = "url(" + background + ")";
  }

  function initWowAnimations() {
    if (!$(".wow").length || typeof WOW === "undefined") {
      return;
    }

    var wow = new WOW({
      boxClass: "wow",
      animateClass: "animated",
      offset: 0,
      mobile: false,
      live: true
    });

    if (isHomePage()) {
      var startWow = function () {
        wow.init();
      };

      if (typeof requestIdleCallback === "function") {
        requestIdleCallback(startWow, { timeout: 2000 });
      } else {
        window.setTimeout(startWow, 150);
      }
      return;
    }

    wow.init();
  }

  var windowOn = $(window);


    /*-----------------------------------------------------------------------------------

        Template Name: Artificial Intelligence Startup HTML5 Template
        Author: RRDevs
        Support: https://support.rrdevs.net
        Description: Artificial Intelligence Startup HTML5 Template
        Version: 1.0
        Developer: Soukhin khan (https://github.com/Soukhinkhan)

    -----------------------------------------------------------------------------------

      /*======================================
        Preloader activation
        ========================================*/
    
        handleQuantityButtons();
    
        $(document.body).on('updated_cart_totals', function() {
            handleQuantityButtons();
        });

    let odometerWaypointInitialized = false;

    function initOdometerWaypoint() {
        if (odometerWaypointInitialized || !$('.odometer').length || typeof $.fn.waypoint !== "function") {
            return;
        }

        odometerWaypointInitialized = true;

        $('.odometer').waypoint(function(direction) {
            if (direction === 'down') {
                let countNumber = $(this.element).attr("data-count");
                $(this.element).html(countNumber);
            }
        }, {
            offset: '80%'
        });
    }

    $(function () {
        initOdometerWaypoint();
    });


    function pushTrackingEvent(eventName, payload) {
        if (!eventName) {
            return;
        }

        var trackingPayload = $.extend({
            event: eventName,
            page_path: window.location.pathname
        }, payload || {});

        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push(trackingPayload);

        if (typeof window.gtag === 'function') {
            var gtagParams = {
                page_path: trackingPayload.page_path
            };

            if (trackingPayload.cta_location) {
                gtagParams.cta_location = trackingPayload.cta_location;
            }

            if (trackingPayload.cta_label) {
                gtagParams.cta_label = trackingPayload.cta_label;
            }

            window.gtag('event', eventName, gtagParams);
        }
    }

    $('[data-track-on-load="true"][data-track-event]').each(function () {
        var element = $(this);
        pushTrackingEvent(element.data('track-event'), {
            cta_location: element.data('track-location') || undefined,
            cta_label: element.data('track-label') || $.trim(element.text()) || undefined
        });
    });

    $(document).on('click', '[data-track-event]:not([data-track-on-load="true"])', function () {
        var element = $(this);
        pushTrackingEvent(element.data('track-event'), {
            cta_location: element.data('track-location') || undefined,
            cta_label: element.data('track-label') || $.trim(element.text()) || undefined
        });
    });

    $(document).on('click', 'a[href*="wa.me"], a[href*="whatsapp"]', function () {
        pushTrackingEvent('click_whatsapp');
    });

    $(document).on('click', 'a[href^="tel:"]', function () {
        pushTrackingEvent('click_phone');
    });

    $(document).on('click', 'a[href^="mailto:"]', function () {
        pushTrackingEvent('click_email');
    });

    //GSAP START

    function initEndGradientAnimation() {
        if (!document.querySelector(".end")) {
            return;
        }

        ensureSplitTextReady(function () {
            ensureChromaReady(function () {
                if (!pluginAvailable("SplitText") || !pluginAvailable("chroma")) {
                    return;
                }

                let endTl = gsap.timeline({
                    repeat: -1,
                    delay: 0.5,
                    scrollTrigger: {
                        trigger: ".end",
                        start: "bottom 100%-=50px"
                    }
                });

                gsap.set(".end", {
                    opacity: 0
                });

                gsap.to(".end", {
                    opacity: 1,
                    duration: 1,
                    ease: "power2.out",
                    scrollTrigger: {
                        trigger: ".end",
                        start: "bottom 100%-=50px",
                        once: true
                    }
                });

                let mySplitText = new SplitText(".end", {
                    type: "words,chars"
                });
                let chars = mySplitText.chars;
                let endGradient = chroma.scale(["#F9D371", "#F47340", "#EF2F88", "#8843F2"]);

                endTl.to(chars, {
                    duration: 0.5,
                    scaleY: 0.6,
                    ease: "power3.out",
                    stagger: 0.04,
                    transformOrigin: "center bottom"
                });
                endTl.to(chars, {
                    yPercent: -20,
                    ease: "elastic",
                    stagger: 0.03,
                    duration: 0.8
                }, 0.5);
                endTl.to(chars, {
                    scaleY: 1,
                    ease: "elastic.out(2.5, 0.2)",
                    stagger: 0.03,
                    duration: 1.5
                }, 0.5);
                endTl.to(chars, {
                    color: function (i, el, arr) {
                        return endGradient(i / arr.length).hex();
                    },
                    ease: "power2.out",
                    stagger: 0.03,
                    duration: 0.3
                }, 0.5);
                endTl.to(chars, {
                    yPercent: 0,
                    ease: "back",
                    stagger: 0.03,
                    duration: 0.8
                }, 0.7);
                endTl.to(chars, {
                    color: "#FFDA59",
                    duration: 1.4,
                    stagger: 0.05
                });
            });
        });
    }

    function initGsapContentAnimations() {
        initEndGradientAnimation();

        let revealContainers = document.querySelectorAll(".return");

        function initReturnReveal(container) {
            let image = container.querySelector("img");
            let tl = gsap.timeline({
                scrollTrigger: {
                    trigger: container,
                    toggleActions: "restart none none reset"
                }
            });

            tl.set(container, { autoAlpha: 1 });
            tl.from(container, 1.5, {
                xPercent: -100,
                ease: Power2.out
            });
            tl.from(image, 1.5, {
                xPercent: 100,
                scale: 1.3,
                delay: -1.5,
                ease: Power2.out
            });
        }

        revealContainers.forEach(function (container) {
            observeOnce(container, initReturnReveal, "320px 0px");
        });

        if ($(".rr_title_anim").length > 0) {
            let splitTitleLines = gsap.utils.toArray(".rr_title_anim");

            function initTitleLine(splitTextLine) {
                if (isHomePage() && splitTextLine.closest(".banner-before")) {
                    return;
                }

                ensureSplitTextReady(function () {
                    if (!pluginAvailable("SplitText")) {
                        return;
                    }

                    const itemSplitted = new SplitText(splitTextLine, { type: "words, lines" });
                    gsap.set(splitTextLine, { perspective: 400 });
                    itemSplitted.split({ type: "lines" });

                    const tl = gsap.timeline({
                        scrollTrigger: {
                            trigger: splitTextLine,
                            start: "top 90%",
                            end: "bottom 60%",
                            scrub: false,
                            markers: false,
                            toggleActions: "play none none reverse"
                        }
                    });

                    tl.from(itemSplitted.lines, {
                        duration: 1,
                        delay: 0.3,
                        opacity: 0,
                        rotationX: -80,
                        force3D: true,
                        transformOrigin: "top center -50",
                        stagger: 0.1
                    });
                });
            }

            splitTitleLines.forEach(function (splitTextLine) {
                observeOnce(splitTextLine, initTitleLine, "320px 0px");
            });
        }

        let heroes = document.querySelectorAll(".hero");

        function initHeroSplit(hero) {
            const splitTarget = hero.querySelector("._split_text");

            if (!splitTarget) {
                return;
            }

            ensureSplitTextReady(function () {
                if (!pluginAvailable("SplitText")) {
                    return;
                }

                let split = new SplitText(splitTarget, { type: "chars, words" }),
                    tl = gsap.timeline({
                        scrollTrigger: {
                            trigger: hero,
                            start: "top bottom",
                            toggleActions: "play none none reverse",
                            onEnter: function () {
                                tl.timeScale(2.3);
                            },
                            onLeaveBack: function () {
                                tl.timeScale(2.3).reverse();
                            }
                        }
                    });
                tl.to(hero.querySelector(".sup_hero"), { opacity: 1, x: -50, ease: "back" })
                    .from(split.chars, {
                        opacity: 0,
                        y: 50,
                        rotation: 1,
                        duration: 2,
                        ease: "back",
                        stagger: 0.05
                    });
            });
        }

        heroes.forEach(function (hero) {
            observeOnce(hero, initHeroSplit, "320px 0px");
        });

        if ($(".fade-wrapper").length > 0) {
            $(".fade-wrapper").each(function () {
                var section = $(this);
                var fadeItems = section.find(".fade-top");

                function initFadeItem(element, delay) {
                    gsap.set(element, {
                        opacity: 0,
                        y: 100
                    });

                    ScrollTrigger.create({
                        trigger: element,
                        start: "top 100%",
                        end: "bottom 60%",
                        toggleActions: "play none none reverse",
                        scrub: 0.5,
                        onEnter: function () {
                            gsap.to(element, {
                                opacity: 1,
                                y: 0,
                                duration: 1,
                                delay: delay
                            });
                        },
                        once: true
                    });
                }

                fadeItems.each(function (index, element) {
                    var delay = index * 0.15;
                    observeOnce(element, function () {
                        initFadeItem(element, delay);
                    }, "320px 0px");
                });
            });
        }
    }

    function initGsapPinAnimations() {
        if (!pluginAvailable("gsap") || !pluginAvailable("ScrollTrigger")) {
            return;
        }

        var device_width = window.screen.width;
        var pinElement = document.querySelector(".pin-element");

        if (pinElement && device_width > 1199) {
            gsap.to(".pin-element", {
                scrollTrigger: {
                    trigger: ".pin-area",
                    pin: ".pin-element",
                    start: "top top",
                    end: "bottom 60%",
                    pinSpacing: false
                }
            });
        }

        var pinElement2 = document.querySelector(".pin-element_2");

        if (pinElement2 && device_width > 1199) {
            gsap.to(".pin-element_2", {
                scrollTrigger: {
                    trigger: ".pin-area-2",
                    pin: ".pin-element_2",
                    start: "top top",
                    end: "bottom botttom",
                    pinSpacing: false
                }
            });
        }

        var latesUpdateItems = document.querySelectorAll(".lates-update__item");

        if (device_width > 1199) {
            latesUpdateItems.forEach(function (gallery) {
                gsap.to(gallery, {
                    scrollTrigger: {
                        trigger: gallery,
                        pin: gallery,
                        pinSpacing: false,
                        start: "top 80px",
                        delay: 1
                    }
                });
            });
        }
    }

    function initGsapBootstrap() {
        if (!pluginAvailable("gsap") || !pluginAvailable("ScrollTrigger")) {
            return;
        }

        gsap.registerPlugin(ScrollTrigger);
        gsap.config({
            nullTargetWarn: false
        });

        function runGsapAnimations() {
            initGsapContentAnimations();
            initGsapPinAnimations();
        }

        if (usesScrollSmootherLayout()) {
            loadInstitutionalScript("plugins/ScrollSmoother.js")
                .then(function () {
                    if (pluginAvailable("ScrollSmoother")) {
                        gsap.registerPlugin(ScrollSmoother);
                        ScrollSmoother.create({
                            smooth: 2,
                            effects: true,
                            smoothTouch: false,
                            normalizeScroll: false,
                            ignoreMobileResize: true,
                            onUpdate: schedulePendingViewportInitFlush,
                            onStop: flushPendingViewportInits
                        });
                        bindViewportInitListeners();
                        flushPendingViewportInits();
                    }
                    runGsapAnimations();
                })
                .catch(runGsapAnimations);
            return;
        }

        runGsapAnimations();
    }

    function runGsapBootstrapOnce() {
        if (gsapBootstrapStarted) {
            return;
        }

        gsapBootstrapStarted = true;
        initGsapBootstrap();
    }

    function scheduleHomeMobileGsapAfterLcp(callback) {
        var HOME_MOBILE_GSAP_FAILSAFE_MS = 4500;
        var HOME_MOBILE_LCP_SETTLE_MS = 200;
        var triggered = false;
        var lcpObserver = null;
        var settleTimer = null;
        var failsafeTimer = null;
        var interactionHandler = null;

        function cleanup() {
            if (settleTimer != null) {
                clearTimeout(settleTimer);
                settleTimer = null;
            }

            if (failsafeTimer != null) {
                clearTimeout(failsafeTimer);
                failsafeTimer = null;
            }

            if (lcpObserver) {
                try {
                    lcpObserver.disconnect();
                } catch (ignore) {
                    /* noop */
                }
                lcpObserver = null;
            }

            if (interactionHandler) {
                window.removeEventListener("scroll", interactionHandler);
                window.removeEventListener("touchstart", interactionHandler);
                window.removeEventListener("pointerdown", interactionHandler);
                window.removeEventListener("keydown", interactionHandler);
                interactionHandler = null;
            }
        }

        function trigger() {
            if (triggered) {
                return;
            }

            triggered = true;
            cleanup();
            requestAnimationFrame(callback);
        }

        function scheduleLcpSettle() {
            if (settleTimer != null) {
                clearTimeout(settleTimer);
            }

            settleTimer = setTimeout(function () {
                settleTimer = null;
                trigger();
            }, HOME_MOBILE_LCP_SETTLE_MS);
        }

        interactionHandler = function () {
            trigger();
        };

        window.addEventListener("scroll", interactionHandler, { passive: true, once: true });
        window.addEventListener("touchstart", interactionHandler, { passive: true, once: true });
        window.addEventListener("pointerdown", interactionHandler, { once: true });
        window.addEventListener("keydown", interactionHandler, { once: true });

        failsafeTimer = setTimeout(trigger, HOME_MOBILE_GSAP_FAILSAFE_MS);

        if (typeof PerformanceObserver === "function") {
            try {
                lcpObserver = new PerformanceObserver(function (entryList) {
                    if (!entryList.getEntries().length) {
                        return;
                    }

                    scheduleLcpSettle();
                });
                lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
            } catch (ignore) {
                /* failsafe / interaction handle unsupported browsers */
            }
        }
    }

    function scheduleGsapBootstrap() {
        var startGsap = function () {
            runGsapBootstrapOnce();
        };

        if (isHomePage() && isMobile()) {
            scheduleHomeMobileGsapAfterLcp(startGsap);
            return;
        }

        if (typeof requestIdleCallback === "function") {
            requestIdleCallback(startGsap, { timeout: 2500 });
            return;
        }

        window.setTimeout(startGsap, 200);
    }

    window.addEventListener("load", scheduleGsapBootstrap);

    //GSAP END
    
    /*======================================
   Data Css js
   ========================================*/
    $("[data-background]").each(function() {
        if (isHomePage()) {
            if (isWithinExpandedViewport(this, 240)) {
                applyDataBackground(this);
                return;
            }

            observeOnce(this, applyDataBackground, "240px 0px");
            return;
        }

        applyDataBackground(this);
    });

    $("[data-width]").each(function() {
        $(this).css("width", $(this).attr("data-width"));
    });

    $("[data-bg-color]").each(function() {
        $(this).css("background-color", $(this).attr("data-bg-color"));
    });

  /*======================================
	Mobile Menu Js
	========================================*/
  if ($("#mobile-menu").length && $.fn.meanmenu) {
  $("#mobile-menu").meanmenu({
    meanMenuContainer: ".mobile-menu",
    meanScreenWidth: "991",
    meanExpand: ['<img src="/static/institutional/icons/next.svg" alt="" aria-hidden="true" class="site-icon">'],
  });
  }

  /*======================================
	Sidebar Toggle
	========================================*/
  $(".offcanvas__close,.offcanvas__overlay").on("click", function () {
    $(".offcanvas__area").removeClass("info-open");
    $(".offcanvas__overlay").removeClass("overlay-open");
  });
  // Scroll to bottom then close navbar
  $(window).scroll(function(){
    if($("body").scrollTop() > 0 || $("html").scrollTop() > 0) {
        $(".offcanvas__area").removeClass("info-open");
        $(".offcanvas__overlay").removeClass("overlay-open");
    }
  });
  $(".sidebar__toggle").on("click", function () {
    $(".offcanvas__area").addClass("info-open");
    $(".offcanvas__overlay").addClass("overlay-open");
  });

  /*======================================
	Body overlay Js
	========================================*/
  $(".body-overlay").on("click", function () {
    $(".offcanvas__area").removeClass("opened");
    $(".body-overlay").removeClass("opened");
  });

  /*======================================
	Sticky Header Js
	========================================*/
  (function () {
    var headerStickyPending = false;
    var headerIsSticky = false;
    var $headerSticky = $("#header-sticky");

    if (!$headerSticky.length) {
      return;
    }

    function updateStickyHeader() {
      headerStickyPending = false;
      var scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0;

      if (scrollTop > 250) {
        if (!headerIsSticky) {
          $headerSticky.addClass("rs-sticky");
          headerIsSticky = true;
        }
        return;
      }

      if (headerIsSticky) {
        $headerSticky.removeClass("rs-sticky");
        headerIsSticky = false;
      }
    }

    function scheduleStickyHeaderUpdate() {
      if (headerStickyPending) {
        return;
      }

      headerStickyPending = true;
      requestAnimationFrame(updateStickyHeader);
    }

    window.addEventListener("scroll", scheduleStickyHeaderUpdate, { passive: true });
    scheduleStickyHeaderUpdate();
  })();

    /*** pricing table */
    const pricingMonthlyBtn = $("#monthly-btn"),
        pricingYearlyBtn = $("#yearly-btn"),
        pricingValues = $(".pricing-card-price h2");

    if (pricingMonthlyBtn[0] && pricingYearlyBtn[0] && pricingValues.length > 0) {
        pricingMonthlyBtn[0].addEventListener("click", function () {
            updatePricingValues("monthly");
            pricingYearlyBtn[0].classList.remove("active");
            pricingMonthlyBtn[0].classList.add("active");
        });

        pricingYearlyBtn[0].addEventListener("click", function () {
            updatePricingValues("yearly");
            pricingMonthlyBtn[0].classList.remove("active");
            pricingYearlyBtn[0].classList.add("active");
        });
    }

    function updatePricingValues(option) {
        pricingValues.each(function () {
            const pricingValue = $(this);
            const yearlyValue = pricingValue.attr("data-yearly");
            const monthlyValue = pricingValue.attr("data-monthly");

            const newValue = option === "monthly" ? monthlyValue : yearlyValue;
            pricingValue.html(newValue);
        });
    }

  /*======================================
	MagnificPopup image view
	========================================*/
  if ($.fn.magnificPopup && ($(".popup-image").length || $(".popup-video").length)) {
  $(".popup-image").magnificPopup({
    type: "image",
    gallery: {
      enabled: true,
    },
  });

  /*======================================
	MagnificPopup video view
	========================================*/
  $(".popup-video").magnificPopup({
    type: "iframe",
  });
  }


  /*======================================
	Wow Js
	========================================*/
    initWowAnimations();

  /*======================================
	Button scroll up js
	========================================*/
    
    /*======================================
	One Page Scroll Js
	========================================*/
    /*** Scroll Nav */
    var link = $(".mean-nav ul li a[href^=\"#\"]");

    if (link.length) {
        link.on("click", function(e) {
            var target = $($(this).attr("href"));
            if (!target.length) {
                return;
            }

            $("html, body").animate({
                scrollTop: target.offset().top - 76
            }, 600);
            $(this).parent().addClass("active");
            e.preventDefault();
        });

        $(window).on("scroll", function(){
            scrNav();
        });

        function scrNav() {
            var sTop = $(window).scrollTop();
            $("section[id]").each(function() {
                var id = $(this).attr("id"),
                    offset = $(this).offset().top-1,
                    height = $(this).height();
                if(sTop >= offset && sTop < offset + height) {
                    link.parent().removeClass("active");
                    $(".main-menu").find("a").filter(function() { return $(this).attr("href") === "#" + id; }).parent().addClass("active");
                }
            });
        }
        scrNav();
    }

    /*======================================
	Smoth animatio Js
	========================================*/
    $(document).on('click', '.smoth-animation', function (event) {
        event.preventDefault();
        $('html, body').animate({
            scrollTop: $($.attr(this, 'href')).offset().top - 50
        }, 300);
    });

  /*======================================
    All Swiper Slide
  ========================================*/

    // seken testimonial__carousel
    var swiperProject = createLazySwiper(".testimonial__carousel", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });
    // hero-10-slide js  --------
    var swiper = createSwiper(".hero-10-slide-active", {
        slidesPerView: 5.5,
        spaceBetween: 30,
        loop: true,
        slidesPerGroupSkip: 0,
        centeredSlides: true,
        autoplay: true,
        centerMode: false,
        breakpoints: {
            1200: {
                slidesPerView: 4.5,
                spaceBetween: 30,
            },
            992: {
                sliderPerView: 4,
                spaceBetween: 30,
            },
            768: {
                slidesPerView: 3,

            },
            576: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
            360: {
                slidesPerView: 1,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });
    // seken testimonial-6__carousel
    var swiperProject = createSwiper(".testimonial-6__carousel", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-6__slider-arrow-prev",
            nextEl: ".testimonial-6__slider-arrow-next",
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });

    //  brands-10 js start ----------
    var swiper = createSwiper(".brands-10-active", {
        slidesPerView: 'auto',
        spaceBetween: 80,
        freemode: true,
        centeredSlides: true,
        loop: true,
        speed: 4000,
        allowTachMode: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1200: {
                slidesPerView: 6,
                spaceBetween: 30,
            },
            992: {
                sliderPerView: 5,
                spaceBetween: 30,
            },
            768: {
                slidesPerView: 3,
                spaceBetween: 20,
            },
            576: {
                slidesPerView: 3,
                spaceBetween: 30,
            },
            360: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
            0: {
                slidesPerView: 2,
                spaceBetween: 30,
            },
        },
    });

    // support-10 slide js ----------
    var swiper = createSwiper(".support-slider-actives", {
        slidesPerView: 'auto',
        spaceBetween: 10,
        freemode: true,
        centeredSlides: true,
        loop: true,
        speed: 4000,
        allowTachMode: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1200: {
                slidesPerView: 4,
            },
            992: {
                sliderPerView: 3,
                spaceBetween: 10,
            },
            768: {
                slidesPerView: 3,
                spaceBetween: 10,
            },
            576: {
                slidesPerView: 3,
                spaceBetween: 10,
            },
            360: {
                slidesPerView: 2,
                spaceBetween: 10,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    // testimonial-10 js  ----------
    var swiper = createSwiper(".testimonial-10-active", {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        // autoplay: true,
        centerMode: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        navigation: {
          nextEl: ".testimonial-10__swiper-button-next",
          prevEl: ".testimonial-10__swiper-button-prev",
        },
    });

    // seken testimonial-4__carousel
    var swiperProject = createSwiper(".testimonial-4__slider", {
        slidesPerView: 1,
        spaceBetween: 50,
        loop: true,
        slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-4__slider-arrow-prev",
            nextEl: ".testimonial-4__slider-arrow-next",
        },
    });
    // blog-list__slider
    var swiperProject = createSwiper(".blog-list__slider", {
        slidesPerView: 1,
        // spaceBetween: 50,
        loop: true,
        // slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        // scrollbar: {
        //     el: ".swiper-scrollbar",
        //     hide: false,
        //     draggable: true,
        // },
        navigation: {
            prevEl: ".testimonial-4__slider-arrow-prev",
            nextEl: ".testimonial-4__slider-arrow-next",
        },
    });


    // seken Show more review button
    $(document).ready(function() {
        let itemsToShow = 3; 
        let itemsIncrement = 3;
        let totalItems = $('.content').length;
      
        $('.content').slice(itemsToShow).hide();
      
        $('.loadmore').on('click', function() {
          let hiddenItems = $('.content:hidden'); 
          hiddenItems.slice(0, itemsIncrement).fadeIn(); 
      
          if (hiddenItems.length <= itemsIncrement) {
            $('.loadmore').fadeOut();
          }

          $('.testimonial-2__area').addClass('hide_overlay');
        });
      });
    // seken Show more review button end

      //seken rr__latest-blog H3
      var swiper = createSwiper(".rr__latest-blog", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });
      //seken review-9__slider H9
      var swiper = createSwiper(".review-9__slider", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });

      //seken blog-4-slider H4
      var swiper = createSwiper(".blog-4-slider", {
        slidesPerView: 3,
        autoplay: true,
        speed: 600,
        spaceBetween: 30,
        loop: true,
        keyboard: {
          enabled: true,
        },
        pagination: {
          el: ".swiper-pagination-4",
          clickable: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
      });

      //seken testi-slider H3
      var testimonials = createSwiper(".testi-slider", {
        slidesPerView: 1,
        slidesPerGroup: 1,
        spaceBetween: 0,
        loop: true,
        autoplay: true,
        speed: 600,
        navigation: {
            nextEl: ".testi-next",
            prevEl: ".testi-prev",
        }, 
    });

    //seken rrseken__fast-content H5
    var swiper = createSwiper(".rrseken__fast-content", {
        slidesPerView: 4,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".rrseken-swiper-button-next",
            prevEl: ".rrseken-swiper-button-prev",
          },
        breakpoints: {
            1301: {
                slidesPerView: 4,
            },
            992: {
                slidesPerView: 3,
            },
            600: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //seken testimonial-5__slide H5
    var swiper = createSwiper(".testimonial-5__slide", {
        slidesPerView: 2,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".rrseken-swiper-button-next",
            prevEl: ".rrseken-swiper-button-prev",
          },
        breakpoints: {
            1301: {
                slidesPerView: 2,
            },
            992: {
                slidesPerView: 2,
            },
            600: {
                slidesPerView: 1,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //seken blog-5__slider H5
    var swiper = createSwiper(".blog-5__slider", {
        slidesPerView: 3,
        spaceBetween: 30,
        loop: true,
        navigation: {
            nextEl: ".blog-5-next",
            prevEl: ".blog-5-prev",
          },
          breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    if ($.fn.isotope && $('.grid').length) {
    $('.grid').isotope({
        itemSelector: '.grid-item',
        percentPosition: true,
        masonry: {
          columnWidth: 1
          
        }
    })

    }
    var swiper = createSwiper(".aifunction-slide", {
    slidesPerView: 4,
    spaceBetween: 30,
    loop: true,
    navigation: {
        prevEl: ".aifunction-slide-button-prev",
        nextEl: ".aifunction-slide-button-next",
    },
    pagination: {
        el: ".swiper-pagination",
        clickable: true,
    },
    breakpoints: {
        1201: {
            slidesPerView: 4,
        },
        716: {
            slidesPerView: 2,
        },
        0: {
            slidesPerView: 1,
        },
    },
    });

    //seken related-products-slide shop-details
    var swiper = createSwiper(".related-products", {
    slidesPerView: 4,
    spaceBetween: 30,
    loop: true,
    autoplay: true,
    speed: 1000,
    breakpoints: {
        1201: {
            slidesPerView: 4,
        },
        716: {
            slidesPerView: 2,
        },
        0: {
            slidesPerView: 1,
        },
    },
    });
    // SEKEN blog__slider-6
    var swiper = createSwiper(".latest-trends__item", {
        slidesPerView: 3,
        loop: true,
        autoplay: true,
        centeredSlides: false,
        spaceBetween: 30,
        slidesPerGroupSkip: 1,
        grabCursor: true,
        keyboard: {
          enabled: true,
        },
        breakpoints: {
          1850: {
            slidesPerView: 3,
            slidesPerGroup: 1,
          },

          1230: {
            slidesPerView: 2,
            slidesPerGroup: 1,
          },

          768: {
            slidesPerView: 1.5,
            slidesPerGroup: 1,
          },
          0: {
            slidesPerView: 1,
            slidesPerGroup: 1,
          },
        },
        scrollbar: {
          el: ".swiper-scrollbar-drag",
        },
      });
    //seken hero-4-slider H4
    var swiper = createSwiper(".hero-4-slider", {
    slidesPerView: 6,
    spaceBetween: 30,
    loop: true,
    centeredSlides: true,
    freemode: true,
    speed:4000,
    allowTouchMove: false,
        autoplay:{
        delay: 1,
        disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 6,
            },
            1024: {
                slidesPerView: 4,
            },
            // 740: {
            //     slidesPerView: 3,
            // },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });

    //Swiper Slider For Shop
    var swiper = createSwiper(".product-gallary-thumb", {
        spaceBetween: 10,
        slidesPerView: 5,
        freeMode: true,
        watchSlidesProgress: true,
        direction: 'vertical',
    });
    
    var swiper2 = createSwiper(".product-gallary", {
        spaceBetween: 10,
        loop: true,
        navigation: {
            nextEl: ".swiper-nav-next",
            prevEl: ".swiper-nav-prev",
        },
        thumbs: {
            swiper: swiper,
        },
    });
    $('.audio[data-audio-src]').on("click keydown", function(event){
        if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') {
            return;
        }

        if (event.type === 'keydown') {
            event.preventDefault();
        }

        var $button = $(this);
        var audio = $button.data('audio-player');

        var setAudioState = function(state) {
            var label = state === 'pause'
                ? 'Pausar áudio institucional sobre LIRO e inclusão'
                : 'Ouvir áudio institucional sobre LIRO e inclusão';
            var iconSrc = state === 'pause'
                ? $button.data('audio-icon-pause')
                : $button.data('audio-icon-play');

            $button.attr('data-audio-state', state);
            $button.attr('aria-label', label);
            $button.find('img.site-icon').attr('src', iconSrc);
        };

        if (!audio) {
            audio = new Audio($button.data('audio-src'));
            audio.onended = function() {
                setAudioState('play');
            };
            $button.data('audio-player', audio);
        }

        if ($button.attr('data-audio-state') === 'play') {
            setAudioState('pause');
            audio.play();
        } else {
            setAudioState('play');
            audio.pause();
        }
    });
    //count
    function handleQuantityButtons() {
        $('.count-wrap .minus').click(function() {
            var input = $(this).closest('.count-wrap').find('input.qty');
            var currentValue = parseInt(input.val());
            if (currentValue > 1) {
                input.val(currentValue - 1).change();
            }
        });

        $('.count-wrap .plus').click(function() {
            var input = $(this).closest('.count-wrap').find('input.qty');
            var currentValue = parseInt(input.val());
            input.val(currentValue + 1).change();
        });
    }
    // Easy Pie Chart
    const piechart = document.querySelectorAll(".piechart");
    if (typeof Waypoint !== "undefined" && piechart.length) {
    piechart.forEach(function (el) {
        const waypoint = new Waypoint({
            element: el,
            handler: function () {
                const easyPieChart = new EasyPieChart(el, {
                    scaleColor: "transparent",
                    lineWidth: 10,
                    lineCap: "round",
                    trackColor: " rgba(255, 255, 255, 0.3)",
                    barColor: "#fff",
                    size: 150,
                    rotate: 0,
                    animate: 1000,
                    onStep: function (value) {
                        this.el.querySelector("span").textContent = Math.round(value);
                    },
                    onStop: function (value, to) {
                        this.el.querySelector("span").textContent = Math.round(to);
                    },
                });
                this.destroy();
            },
            offset: "80%",
            triggerOnce: true,
        });
    });
    }

      // Project Style3
    if ($(".slider_hover__item li").length) {
        $(".slider_hover__item li").each(function () {
            let self = $(this);

            self.on("mouseenter", function () {
                console.log($(this));
                $(".slider_hover__item li").removeClass("active");
                $(this).addClass("active");
            });
        });
    }

      $('.col-custom').on("click", function () {
		$('#features-item-thumb').removeClass().addClass($(this).attr('rel'));
		$(this).addClass('active').siblings().removeClass('active');
	});

    // Popup Search Box
    $(function () {
        $("#popup-search-box").removeClass("toggled");

        $(".dl-search-icon").on("click", function (e) {
            e.stopPropagation();
            $("#popup-search-box").toggleClass("toggled");
            $("#popup-search").focus();
        });

        $("#popup-search-box input").on("click", function (e) {
            e.stopPropagation();
        });

        $("#popup-search-box, body").on("click", function () {
            $("#popup-search-box").removeClass("toggled");
        });
    });

    // $('.lan-select select, .nice-select-select select').niceSelect();
    if (($('.take-appointment-3__form-input-select select, .lan-select select, .nice-select-select select').length) && $.fn.niceSelect) {
    $('.take-appointment-3__form-input-select select, .lan-select select, .nice-select-select select').niceSelect();
    }
    if ($('#getting-started').length && $.fn.countdown) {
    $('#getting-started').countdown('2025/01/01', function(event) {
        $(this).html(event.strftime(' <div><span>%D</span></div>  <div><span>%H</span></div> <div><span>%M</span></div> <div><span>%S</span></div>'));
      });
    }


      /*** lastNobullet */
    function lastNobullet() {
        var lastElement = false;
        $(".footer__copyright-menu ul li, .last_item_not_horizental_bar .col-lg-4").each(function() {
            if (lastElement && lastElement.offset().top != $(this).offset().top) {
                $(lastElement).addClass("no_bullet");
            } else {
                $(lastElement).removeClass("no_bullet");
            }
            lastElement = $(this);
        }).last().addClass("no_bullet");
    };
    lastNobullet();

    $(window).resize(function(){
        lastNobullet();
    });


    $('#showlogin').on('click', function () {
        $('#checkout-login').slideToggle(400);
    });
    $('#showcoupon').on('click', function () {
        $('#checkout_coupon').slideToggle(400);
    });
    

    // Custom Cursor
    if ($(".cursor-effect, .cross-cursor").length) {
    $("body").append('<div class="mt-cursor"></div>');
    var cursor = $(".mt-cursor"),
        linksCursor = $("a, .swiper-nav, button, .cursor-effect"),
        crossCursor = $(".cross-cursor");

    $(window).on("mousemove", function (e) {
        cursor.css({
            transform: "translate(" + (e.clientX - 15) + "px," + (e.clientY - 15) + "px)",
            visibility: "inherit",
        });
    });
    }

    // Page Scroll Percentage
    function scrollTopPercentage() {
        var scrollElementWrap = $("#scroll-percentage");
        var scrollValueEl = $("#scroll-percentage-value");
        var scrollPercentagePending = false;
        var lastScrollValue = -1;
        var lastIsActive = null;
        var topIconHtml = '<img src="/static/institutional/icons/top.svg" alt="" aria-hidden="true" class="site-icon">';

        function flushScrollPercentage() {
            scrollPercentagePending = false;

            var scrollTopPos = document.documentElement.scrollTop;
            var calcHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            var scrollValue = calcHeight > 0 ? Math.round((scrollTopPos / calcHeight) * 100) : 0;

            if (scrollValue !== lastScrollValue) {
                scrollElementWrap.css(
                    "background",
                    "conic-gradient( var(--rr-theme-primary2) " + scrollValue + "%, var(--rr-common-white) " + scrollValue + "%)"
                );

                if (scrollValue < 96) {
                    scrollValueEl.text(scrollValue + "%");
                } else {
                    scrollValueEl.html(topIconHtml);
                }

                lastScrollValue = scrollValue;
            }

            var isActive = scrollTopPos > 100;
            if (isActive !== lastIsActive) {
                if (isActive) {
                    scrollElementWrap.addClass("active");
                } else {
                    scrollElementWrap.removeClass("active");
                }
                lastIsActive = isActive;
            }
        }

        function scheduleScrollPercentageUpdate() {
            if (scrollPercentagePending) {
                return;
            }

            scrollPercentagePending = true;
            requestAnimationFrame(flushScrollPercentage);
        }

        window.addEventListener("scroll", scheduleScrollPercentageUpdate, { passive: true });
        window.addEventListener("load", scheduleScrollPercentageUpdate);

        function scrollToTop() {
            document.documentElement.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        }

        $("#scroll-percentage").on("click", scrollToTop);
        scheduleScrollPercentageUpdate();
    }

    scrollTopPercentage();

    // slider js -----------
    $(document).ready(function () {
        function sliderAnimations(elements) {
            var animationEndEvents = "webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend";
            elements.each(function () {
                var $this = $(this);
                var $animationDelay = $this.data("delay");
                var $animationDuration = $this.data("duration");
                var $animationType = "pixfix-animation " + $this.data("animation");
                $this.css({
                    "animation-delay": $animationDelay,
                    "-webkit-animation-delay": $animationDelay,
                    "animation-duration": $animationDuration,
                });
                $this.addClass($animationType).one(animationEndEvents, function () {
                    $this.removeClass($animationType);
                });
            });
        }
        var sliderOptions = {
            speed: 1500,
            autoplay: {
                delay: 7000,
            },
            disableOnInteraction: false,
            initialSlide: 0,
            parallax: false,
            mousewheel: false,
            loop: true,
            grabCursor: true,
            navigation: {
                nextEl: ".slider-arrow .slider-next",
                prevEl: ".slider-arrow .slider-prev",
            }
        };
        sliderOptions.on = {
            slideChangeTransitionStart: function () {
                var swiper = this;
                var animatingElements = $(swiper.slides[swiper.activeIndex]).find("[data-animation]");
                sliderAnimations(animatingElements);
            },

            resize: function () {
                this.update();
            },
        };

        var swiper = createSwiper(".banner-4__active", sliderOptions);
    });
    
    // Progress Item 7
    document.addEventListener("DOMContentLoaded", () => {
        const progressItems = document.querySelectorAll(".progress-7__item");
        const progressBox = document.querySelector(".progress-7__box");

        if(progressItems && progressBox){
            // Define colors for each step
        const colors = ["#36F165"];

        window.addEventListener("scroll", () => {
            let activeIndex = -1;

            progressItems.forEach((item, index) => {
                const rect = item.getBoundingClientRect();
                const isInView = rect.top < window.innerHeight / 2 && rect.bottom > 0;

                if (isInView) {
                    item.classList.add("active");
                    activeIndex = index;
                } else {
                    item.classList.remove("active");
                }
            });

            if (activeIndex >= 0) {
                const activeItem = progressItems[activeIndex];
                const boxRect = progressBox.getBoundingClientRect();
                const itemRect = activeItem.getBoundingClientRect();

                // Calculate the height for the progress line
                const newHeight = itemRect.top + itemRect.height / 1 - boxRect.top;

                // Update the progress line height and color
                progressBox.style.setProperty("--line-height", `${newHeight}px`);
                progressBox.style.setProperty("--line-color", colors[activeIndex] || "#36F165");
            } else {
                // Reset the line height when no item is active
                progressBox.style.setProperty("--line-height", `0px`);
            }
        });
        }
    });

    // seken testimonial-8__carousel
    var swiperProject1 = createSwiper(".testimonial-8__slider", {
        slidesPerView: 2,
        spaceBetween: 30,
        loop: true,
        slidesPerGroupSkip: 3,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        pagination: {
            el: ".swiper-pagination-8",
            clickable: true,
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 2,
            },
        },
    });
    //seken blog-8__slider H5
    var swiper = createSwiper(".blog-8__slider", {
        slidesPerView: 3,
        spaceBetween: 30,
        loop: true,
        autoplay: true,
        speed: 600,
        navigation: {
            nextEl: ".blog-8__button__next",
            prevEl: ".blog-8__button__prev",
        },
        breakpoints: {
            1201: {
                slidesPerView: 3,
            },
            716: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 1,
            },
        },
    });
    var swiper1 = createSwiper(".about-us-7__slider-1", {
        direction: "vertical",
        slidesPerView: "auto",
        spaceBetween: 10,
        speed: 7e3,
        loop: !0,
        freemode: true,
        autoplay: {
            delay: 0.9,
            disableOnInteraction: !1
        }
    }),
        swiper4 = createSwiper(".about-us-7__slider-2", {
            direction: "vertical",
            spaceBetween: 10,
            speed: 8e3,
            loop: !0,
            slidesPerView: "auto",
            freemode: true,
            autoplay: {
                delay: 0.9,
                disableOnInteraction: !1
            }
        }),
        swiper3 = createSwiper(".about-us-7__slider-3", {
            direction: "vertical",
            spaceBetween: 10,
            speed: 13e3,
            loop: !0,
            slidesPerView: "auto",
            freemode: true,
            autoplay: {
                delay: 0.9,
                disableOnInteraction: !1
            }
        });

    //seken brand-7__silder H7
    var swiper = createSwiper(".brand-7__silder", {
        slidesPerView: 6,
        spaceBetween: 30,
        loop: true,
        centeredSlides: true,
        freemode: true,
        speed: 4000,
        allowTouchMove: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 6,
            },
            1024: {
                slidesPerView: 4,
            },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 2,
            },
        },
    });
    //seken secure-refined-silder H7
    var swiper = createSwiper(".secure-refined-silder", {
        slidesPerView: 4,
        spaceBetween: 30,
        loop: true,
        centeredSlides: true,
        freemode: true,
        speed: 4000,
        allowTouchMove: false,
        autoplay: {
            delay: 1,
            disableOnInteraction: true,
        },
        breakpoints: {
            1201: {
                slidesPerView: 4,
            },
            1024: {
                slidesPerView: 4,
            },
            575: {
                slidesPerView: 3,
            },
            370: {
                slidesPerView: 2,
            },
            0: {
                slidesPerView: 2,
            },
        },
    });

    // seken testimonial-7__silder
    var testimonial = createSwiper(".testimonial-7__silder", {
        slidesPerView: 4,
        spaceBetween: 20,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".testimonial-7__slider-arrow-prev",
            nextEl: ".testimonial-7__slider-arrow-next",
        },
        breakpoints: {
            320: {
                slidesPerView: 1,
                spaceBetween: 20,
            },
            767: {
                slidesPerView: 2,
                spaceBetween: 20,
            },
            1200: {
                slidesPerView: 4,
            },
        },
    });

    //design-services-7__silder
    var design_services = createSwiper(".design-services-7__silder", {
        slidesPerView: 1,
        spaceBetween: 0,
        loop: true,
        slidesPerGroupSkip: 1,
        centeredSlides: true,
        autoplay: true,
        centerMode: true,
        speed: 400,
        scrollbar: {
            el: ".swiper-scrollbar",
            hide: false,
            draggable: true,
        },
        navigation: {
            prevEl: ".design-services-7__slider-arrow-prev",
            nextEl: ".design-services-7__slider-arrow-next",
        },
    });


    var liviaWidgetLoaded = false;

    function initLiviaWidget() {
        if (liviaWidgetLoaded) {
            return;
        }

        var config = document.getElementById("livia-config");
        if (!config) {
            return;
        }

        var widgetSrc = config.getAttribute("data-widget-src");
        if (!widgetSrc) {
            return;
        }

        liviaWidgetLoaded = true;

        var script = document.createElement("script");
        script.src = widgetSrc;
        script.defer = true;
        script.setAttribute("data-tenant", config.getAttribute("data-tenant") || "");
        script.setAttribute("data-api-url", config.getAttribute("data-api-url") || "");
        document.body.appendChild(script);
    }

    function scheduleLiviaWidget() {
        if (typeof requestIdleCallback === "function") {
            requestIdleCallback(initLiviaWidget, { timeout: 4000 });
            return;
        }

        window.setTimeout(initLiviaWidget, 500);
    }

    window.addEventListener("load", scheduleLiviaWidget);

})(jQuery);