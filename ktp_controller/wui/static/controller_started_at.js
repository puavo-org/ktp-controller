(function () {
  const TICK_MS = 5000;

  function pick(n, templateOne, templateOther) {
    const template = n === 1 ? templateOne : templateOther;
    return template.replace("{n}", n);
  }

  // SVGElement doesn't reflect the `.hidden` IDL property back to the
  // `hidden` content attribute the way HTMLElement does, so toggle the
  // attribute directly instead.
  function setHidden(el, hide) {
    if (hide) {
      el.setAttribute("hidden", "");
    } else {
      el.removeAttribute("hidden");
    }
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

    const warn = seconds < 60;
    const cell = document.getElementById("controller-started-at-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", warn);
    }
    const valueIcon = document.getElementById("controller-started-at-icon");
    if (valueIcon !== null) {
      setHidden(valueIcon, !warn);
    }
    const header = document.getElementById("controller-info-header");
    if (header !== null) {
      header.classList.toggle("value-warning", warn);
    }
    const headerIcon = document.getElementById("controller-info-header-icon");
    if (headerIcon !== null) {
      setHidden(headerIcon, !warn);
    }
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
