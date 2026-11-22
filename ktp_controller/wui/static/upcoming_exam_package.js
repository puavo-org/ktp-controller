(function () {
  const TICK_MS = 5000;

  // Returns true if the scheduled start time is in the past.
  function updateScheduledStart() {
    const el = document.getElementById("upcoming-exam-package-scheduled-start");
    if (el === null) {
      return false;
    }
    const scheduledStart = Date.parse(el.dataset.scheduledStart);
    el.setAttribute("data-tooltip", KtpWui.formatShortDateTime(new Date(scheduledStart)));

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

    const cell = document.getElementById(
      "upcoming-exam-package-scheduled-start-cell",
    );
    if (cell !== null) {
      cell.classList.toggle("value-error", late);
    }
    const icon = document.getElementById(
      "upcoming-exam-package-scheduled-start-icon",
    );
    if (icon !== null) {
      KtpWui.setHidden(icon, !late);
    }
    return late;
  }

  // Returns true if the scheduled end time is in the past.
  function updateScheduledEnd() {
    const el = document.getElementById("upcoming-exam-package-scheduled-end");
    if (el === null) {
      return false;
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

    const cell = document.getElementById(
      "upcoming-exam-package-scheduled-end-cell",
    );
    if (cell !== null) {
      cell.classList.toggle("value-warning", overdue);
    }
    const icon = document.getElementById(
      "upcoming-exam-package-scheduled-end-icon",
    );
    if (icon !== null) {
      KtpWui.setHidden(icon, !overdue);
    }
    return overdue;
  }

  function update() {
    const late = updateScheduledStart();
    const overdue = updateScheduledEnd();

    const header = document.getElementById("upcoming-exam-package-header");
    if (header !== null) {
      header.classList.toggle("value-error", late);
      header.classList.toggle("value-warning", !late && overdue);
    }
    const headerIcon = document.getElementById(
      "upcoming-exam-package-header-icon",
    );
    if (headerIcon !== null) {
      KtpWui.setHidden(headerIcon, !(late || overdue));
    }
  }

  // A live-update swap replaces the whole card, including all the
  // elements above - refresh immediately instead of waiting up to
  // TICK_MS for the next tick.
  document.addEventListener("htmx:afterSwap", update);
  KtpWui.startTicking(update, TICK_MS);
})();
