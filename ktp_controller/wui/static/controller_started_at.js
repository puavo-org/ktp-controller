(function () {
  const TICK_MS = 5000;

  function update() {
    const el = document.getElementById("controller-started-at");
    if (el === null) {
      return;
    }
    const startedAt = Date.parse(el.dataset.startedAt);
    el.setAttribute("data-tooltip", KtpWui.formatLongDateTime(new Date(startedAt)));

    const seconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
    let text;
    if (seconds < 60) {
      text = KtpWui.pick(seconds, el.dataset.secondsOne, el.dataset.secondsOther);
    } else if (seconds < 3600) {
      text = KtpWui.pick(Math.floor(seconds / 60), el.dataset.minutesOne, el.dataset.minutesOther);
    } else if (seconds < 86400) {
      text = KtpWui.pick(Math.floor(seconds / 3600), el.dataset.hoursOne, el.dataset.hoursOther);
    } else {
      text = KtpWui.pick(Math.floor(seconds / 86400), el.dataset.daysOne, el.dataset.daysOther);
    }
    el.textContent = text;

    const warn = seconds < 60;
    const cell = document.getElementById("controller-started-at-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", warn);
    }
    const valueIcon = document.getElementById("controller-started-at-icon");
    if (valueIcon !== null) {
      KtpWui.setHidden(valueIcon, !warn);
    }
    const header = document.getElementById("controller-info-header");
    if (header !== null) {
      header.classList.toggle("value-warning", warn);
    }
    const headerIcon = document.getElementById("controller-info-header-icon");
    if (headerIcon !== null) {
      KtpWui.setHidden(headerIcon, !warn);
    }
  }

  KtpWui.startTicking(update, TICK_MS);
})();
