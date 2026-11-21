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
})();
