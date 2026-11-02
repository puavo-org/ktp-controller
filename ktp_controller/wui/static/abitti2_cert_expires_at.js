(function () {
  function update() {
    const el = document.getElementById("abitti2-cert-expires-at");
    if (el === null || el.dataset.certExpiresAt === undefined) {
      return;
    }
    const expiresAt = new Date(Date.parse(el.dataset.certExpiresAt));

    // With no explicit `timeZone` option, these render in the browser's
    // local timezone, replacing the server-rendered UTC date.
    el.textContent = expiresAt.toLocaleDateString(document.documentElement.lang, {
      dateStyle: "short",
    });

    // "long" additionally includes the timezone name/offset.
    el.setAttribute(
      "data-tooltip",
      expiresAt.toLocaleString(document.documentElement.lang, {
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
