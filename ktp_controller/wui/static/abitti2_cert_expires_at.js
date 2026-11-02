(function () {
  function update() {
    const el = document.getElementById("abitti2-cert-expires-at");
    if (el === null) {
      return;
    }
    const expiresAt = Date.parse(el.dataset.certExpiresAt);

    // "long" includes the timezone name/offset, and with no explicit
    // `timeZone` option this renders in the browser's local timezone.
    el.setAttribute(
      "data-tooltip",
      new Date(expiresAt).toLocaleString(document.documentElement.lang, {
        dateStyle: "long",
        timeStyle: "long",
      }),
    );
  }

  // This script runs in <head>, before <body> (and
  // #abitti2-cert-expires-at) exist, so the element isn't there yet for
  // this first call to find.
  update();
  document.addEventListener("DOMContentLoaded", update);
})();
