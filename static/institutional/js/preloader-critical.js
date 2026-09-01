(function (window, document) {
    "use strict";

    var CLOSED = false;
    var TRANSITION_MS = 300;
    var FAILSAFE_MS = 4000;

    function closePreloader(options) {
        if (CLOSED) {
            return;
        }
        CLOSED = true;

        var preloader = document.getElementById("preloader");
        if (!preloader) {
            return;
        }

        var immediate = options && options.immediate;

        if (!immediate) {
            preloader.style.transition = "opacity " + TRANSITION_MS + "ms ease";
        }

        preloader.style.opacity = "0";
        preloader.style.visibility = "hidden";
        preloader.style.pointerEvents = "none";
        document.documentElement.style.removeProperty("overflow");
        document.body.style.removeProperty("overflow");

        window.setTimeout(function () {
            if (preloader.parentNode) {
                preloader.parentNode.removeChild(preloader);
            }
        }, immediate ? 0 : TRANSITION_MS);
    }

    window.smart360ClosePreloader = closePreloader;

    function bindControls() {
        var closeButton = document.querySelector("#preloader .preloader-close");
        if (closeButton) {
            closeButton.addEventListener("click", function (event) {
                event.preventDefault();
                closePreloader();
            });
        }

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closePreloader();
            }
        });
    }

    bindControls();

    function scheduleAutoClose() {
        if (document.readyState === "interactive" || document.readyState === "complete") {
            closePreloader({ immediate: true });
            return;
        }

        document.addEventListener("readystatechange", function onReadyStateChange() {
            if (document.readyState !== "interactive") {
                return;
            }

            document.removeEventListener("readystatechange", onReadyStateChange);
            closePreloader({ immediate: true });
        });
    }

    scheduleAutoClose();
    window.setTimeout(function () {
        closePreloader({ immediate: true });
    }, FAILSAFE_MS);
})(window, document);
