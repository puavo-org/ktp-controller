(function () {
  const TICK_MS = 5000;
  let anchor = Date.now();

  function update() {
    const el = document.getElementById("page-refreshed-status");
    if (el === null) {
      return;
    }
    const seconds = Math.max(0, Math.round((Date.now() - anchor) / 1000));
    el.textContent = KtpWui.pick(seconds, el.dataset.templateOne, el.dataset.templateOther);
  }

  document.addEventListener("htmx:afterRequest", () => {
    anchor = Date.now();
    update();
  });

  KtpWui.startTicking(update, TICK_MS);
})();
