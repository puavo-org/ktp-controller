(function () {
  const TICK_MS = 5000;
  let anchor = Date.now();

  function update() {
    const el = document.getElementById("page-refreshed-status");
    if (el === null) {
      return;
    }
    const seconds = Math.max(0, Math.round((Date.now() - anchor) / 1000));
    const template = seconds === 1 ? el.dataset.templateOne : el.dataset.templateOther;
    el.textContent = template.replace("{n}", seconds);
  }

  document.addEventListener("htmx:afterRequest", () => {
    anchor = Date.now();
    update();
  });

  update();
  setTimeout(() => {
    update();
    setInterval(update, TICK_MS);
  }, TICK_MS - (Date.now() % TICK_MS));
})();
