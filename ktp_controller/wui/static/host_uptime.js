(function () {
  const TICK_MS = 5000;

  function update() {
    const el = document.getElementById("host-uptime");
    if (el === null || !el.dataset.startedAt) {
      return;
    }
    const startedAt = Date.parse(el.dataset.startedAt);
    el.setAttribute("data-tooltip", KtpWui.formatShortDateTime(new Date(startedAt)));

    const seconds = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
    let text;
    if (seconds < 3600) {
      text = KtpWui.pick(Math.floor(seconds / 60), el.dataset.minutesOne, el.dataset.minutesOther);
    } else if (seconds < 86400) {
      text = KtpWui.pick(Math.floor(seconds / 3600), el.dataset.hoursOne, el.dataset.hoursOther);
    } else {
      text = KtpWui.pick(Math.floor(seconds / 86400), el.dataset.daysOne, el.dataset.daysOther);
    }
    el.textContent = text;

    const warn = seconds < 60 || seconds > 60 * 86400;
    const cell = document.getElementById("host-uptime-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", warn);
    }
    const valueIcon = document.getElementById("host-uptime-icon");
    if (valueIcon !== null) {
      KtpWui.setHidden(valueIcon, !warn);
    }
  }

  KtpWui.startTicking(update, TICK_MS);
})();
