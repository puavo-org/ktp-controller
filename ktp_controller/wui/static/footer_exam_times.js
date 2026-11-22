(function () {
  const TICK_MS = 5000;

  // "Current exam ends": reads as "in X" while still upcoming, "X ago"
  // once overdue.
  function updateCurrentEnds() {
    const el = document.getElementById("footer-current-exam-ends");
    if (el === null) {
      return;
    }
    const scheduledEnd = Date.parse(el.dataset.scheduledEnd);
    el.setAttribute("data-tooltip", KtpWui.formatShortDateTime(new Date(scheduledEnd)));

    const seconds = Math.round((scheduledEnd - Date.now()) / 1000);
    const overdue = seconds < 0;
    const abs = Math.abs(seconds);
    let text;
    if (abs < 3600) {
      const n = Math.floor(abs / 60);
      text = overdue
        ? KtpWui.pick(n, el.dataset.minutesOne, el.dataset.minutesOther)
        : KtpWui.pick(n, el.dataset.inMinutesOne, el.dataset.inMinutesOther);
    } else if (abs < 86400) {
      const n = Math.floor(abs / 3600);
      text = overdue
        ? KtpWui.pick(n, el.dataset.hoursOne, el.dataset.hoursOther)
        : KtpWui.pick(n, el.dataset.inHoursOne, el.dataset.inHoursOther);
    } else {
      const n = Math.floor(abs / 86400);
      text = overdue
        ? KtpWui.pick(n, el.dataset.daysOne, el.dataset.daysOther)
        : KtpWui.pick(n, el.dataset.inDaysOne, el.dataset.inDaysOther);
    }
    el.textContent = text;
  }

  // "Next exam starts": reads as "in X" while still upcoming, "X late"
  // once overdue.
  function updateNextStarts() {
    const el = document.getElementById("footer-next-exam-starts");
    if (el === null) {
      return;
    }
    const scheduledStart = Date.parse(el.dataset.scheduledStart);
    el.setAttribute(
      "data-tooltip",
      KtpWui.formatShortDateTime(new Date(scheduledStart)),
    );

    const seconds = Math.round((scheduledStart - Date.now()) / 1000);
    const late = seconds < 0;
    const abs = Math.abs(seconds);
    let text;
    if (abs < 3600) {
      const n = Math.floor(abs / 60);
      text = late
        ? KtpWui.pick(n, el.dataset.lateMinutesOne, el.dataset.lateMinutesOther)
        : KtpWui.pick(n, el.dataset.inMinutesOne, el.dataset.inMinutesOther);
    } else if (abs < 86400) {
      const n = Math.floor(abs / 3600);
      text = late
        ? KtpWui.pick(n, el.dataset.lateHoursOne, el.dataset.lateHoursOther)
        : KtpWui.pick(n, el.dataset.inHoursOne, el.dataset.inHoursOther);
    } else {
      const n = Math.floor(abs / 86400);
      text = late
        ? KtpWui.pick(n, el.dataset.lateDaysOne, el.dataset.lateDaysOther)
        : KtpWui.pick(n, el.dataset.inDaysOne, el.dataset.inDaysOther);
    }
    el.textContent = text;
  }

  function update() {
    updateCurrentEnds();
    updateNextStarts();
  }

  // A live-update swap replaces the whole fragment, including both
  // elements above - refresh immediately instead of waiting up to
  // TICK_MS for the next tick.
  document.addEventListener("htmx:afterSwap", update);
  KtpWui.startTicking(update, TICK_MS);
})();
