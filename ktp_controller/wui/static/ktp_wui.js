(function () {
  window.KtpWui = window.KtpWui || {};
  const KtpWui = window.KtpWui;

  KtpWui.pick = function (n, templateOne, templateOther) {
    const template = n === 1 ? templateOne : templateOther;
    return template.replace("{n}", n);
  };

  // SVGElement doesn't reflect the `.hidden` IDL property back to the
  // `hidden` content attribute the way HTMLElement does, so toggle the
  // attribute directly instead.
  KtpWui.setHidden = function (el, hide) {
    if (hide) {
      el.setAttribute("hidden", "");
    } else {
      el.removeAttribute("hidden");
    }
  };

  KtpWui.formatLongDateTime = function (date) {
    // "long" includes the timezone name/offset, and with no explicit
    // `timeZone` option this renders in the browser's local timezone.
    return date.toLocaleString(document.documentElement.lang, {
      dateStyle: "long",
      timeStyle: "long",
    });
  };

  KtpWui.startTicking = function (update, intervalMs) {
    // This runs in <head>, before <body> (and the elements `update`
    // looks for) exist, so this first call is a no-op.
    update();
    document.addEventListener("DOMContentLoaded", update);
    setTimeout(() => {
      update();
      setInterval(update, intervalMs);
    }, intervalMs - (Date.now() % intervalMs));
  };

  function closeOverlay(overlay) {
    overlay.classList.remove("is-visible");
  }

  KtpWui.initConfirmOverlay = function ({
    triggerSelector,
    overlayId,
    yesSelector,
    noSelector,
    onOpen,
    onConfirm,
  }) {
    let pendingTrigger = null;

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest(triggerSelector);
      if (trigger === null) {
        return;
      }
      const overlay = document.getElementById(overlayId);
      if (overlay === null) {
        return;
      }
      pendingTrigger = trigger;
      if (onOpen) {
        onOpen(trigger);
      }
      overlay.classList.add("is-visible");
    });

    document.addEventListener("click", (event) => {
      const overlay = document.getElementById(overlayId);
      if (overlay === null || !overlay.classList.contains("is-visible")) {
        return;
      }
      if (event.target.closest(yesSelector) !== null && onConfirm) {
        onConfirm(pendingTrigger);
      }
      if (
        event.target === overlay ||
        event.target.closest(`${noSelector}, ${yesSelector}`) !== null
      ) {
        closeOverlay(overlay);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") {
        return;
      }
      const overlay = document.getElementById(overlayId);
      if (overlay !== null) {
        closeOverlay(overlay);
      }
    });
  };

  KtpWui.initHiddenToggle = function ({ attr, triggerSelector, swapTargetId, applyState }) {
    function isHidden() {
      return document.documentElement.getAttribute(attr) !== "false";
    }

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest(triggerSelector);
      if (trigger === null) {
        return;
      }
      document.documentElement.setAttribute(attr, String(!isHidden()));
      applyState(isHidden());
    });

    document.addEventListener("htmx:afterSwap", (event) => {
      if (event.detail.target.id !== swapTargetId) {
        return;
      }
      applyState(isHidden());
    });
  };
})();
