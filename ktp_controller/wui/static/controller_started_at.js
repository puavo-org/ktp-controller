(function () {
  const TICK_MS = 5000;

  function pick(n, templateOne, templateOther) {
    const template = n === 1 ? templateOne : templateOther;
    return template.replace("{n}", n);
  }

  function update() {
    const el = document.getElementById("controller-started-at");
    if (el === null) {
      return;
    }
    const startedAt = Date.parse(el.dataset.startedAt);
    const seconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
    let text;
    if (seconds < 60) {
      text = pick(seconds, el.dataset.secondsOne, el.dataset.secondsOther);
    } else if (seconds < 3600) {
      text = pick(Math.floor(seconds / 60), el.dataset.minutesOne, el.dataset.minutesOther);
    } else if (seconds < 86400) {
      text = pick(Math.floor(seconds / 3600), el.dataset.hoursOne, el.dataset.hoursOther);
    } else {
      text = pick(Math.floor(seconds / 86400), el.dataset.daysOne, el.dataset.daysOther);
    }
    el.textContent = text;
    el.classList.toggle("value-warning", seconds < 60);
  }

  // This script runs in <head>, before <body> (and #controller-started-at)
  // exist, so the element isn't there yet for this first call to find.
  update();
  document.addEventListener("DOMContentLoaded", update);
  setTimeout(() => {
    update();
    setInterval(update, TICK_MS);
  }, TICK_MS - (Date.now() % TICK_MS));
})();
