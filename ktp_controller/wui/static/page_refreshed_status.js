(function () {
  // Animation timeline, replayed from the top on every refresh ("beat"):
  //   0s -> 1s:  quick charge to full size/color
  //   1s -> 30s: slow discharge to 50% size / lightest green
  //   30s -> 35s: size stays at 50%, color fades from light green to red
  //   35s+:      stays red until the next beat
  const CHARGE_MS = 1000;
  const DISCHARGE_MS = 29000;
  const ALARM_MS = 5000;
  const TITLE_UPDATE_MS = 1000;

  let anchor = Date.now();
  let dischargeTimer = null;
  let alarmTimer = null;

  function statusEl() {
    return document.getElementById("page-refreshed-status");
  }

  function updateTitle() {
    const el = statusEl();
    if (el === null) {
      return;
    }
    const seconds = Math.max(0, Math.round((Date.now() - anchor) / 1000));
    const template = seconds === 1 ? el.dataset.templateOne : el.dataset.templateOther;
    el.title = template.replace("{n}", seconds);
  }

  function beat() {
    const el = statusEl();
    if (el === null) {
      return;
    }
    clearTimeout(dischargeTimer);
    clearTimeout(alarmTimer);

    el.style.transitionDuration = `${CHARGE_MS}ms`;
    el.classList.remove("is-discharged", "is-alarm");

    dischargeTimer = setTimeout(() => {
      el.style.transitionDuration = `${DISCHARGE_MS}ms`;
      el.classList.add("is-discharged");

      alarmTimer = setTimeout(() => {
        el.style.transitionDuration = `${ALARM_MS}ms`;
        el.classList.add("is-alarm");
      }, DISCHARGE_MS);
    }, CHARGE_MS);
  }

  document.addEventListener("htmx:afterRequest", () => {
    anchor = Date.now();
    beat();
  });

  // This script runs in <head>, before <body> (and #page-refreshed-status)
  // exist, so the element isn't there yet for this first call to find.
  beat();
  updateTitle();
  document.addEventListener("DOMContentLoaded", () => {
    beat();
    updateTitle();
  });
  setInterval(updateTitle, TITLE_UPDATE_MS);
})();
