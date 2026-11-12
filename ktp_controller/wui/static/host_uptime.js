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
    const el = document.getElementById("host-uptime");
    if (el === null || !el.dataset.startedAt) {
      return;
    }
    const startedAt = Date.parse(el.dataset.startedAt);

    // "long" includes the timezone name/offset, and with no explicit
    // `timeZone` option this renders in the browser's local timezone.
    el.setAttribute(
      "data-tooltip",
      new Date(startedAt).toLocaleString(document.documentElement.lang, {
        dateStyle: "long",
        timeStyle: "long",
      }),
    );

    const seconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
    let text;
    if (seconds < 3600) {
      text = pick(Math.floor(seconds / 60), el.dataset.minutesOne, el.dataset.minutesOther);
    } else if (seconds < 86400) {
      text = pick(Math.floor(seconds / 3600), el.dataset.hoursOne, el.dataset.hoursOther);
    } else {
      text = pick(Math.floor(seconds / 86400), el.dataset.daysOne, el.dataset.daysOther);
    }
    el.textContent = text;

    const warn = seconds < 60 || seconds > 60 * 86400;
    const cell = document.getElementById("host-uptime-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", warn);
    }
    const valueIcon = document.getElementById("host-uptime-icon");
    if (valueIcon !== null) {
      setHidden(valueIcon, !warn);
    }
  }

  // This script runs in <head>, before <body> (and #host-uptime)
  // exist, so the element isn't there yet for this first call to find.
  update();
  document.addEventListener("DOMContentLoaded", update);
  setTimeout(() => {
    update();
    setInterval(update, TICK_MS);
  }, TICK_MS - (Date.now() % TICK_MS));
})();
