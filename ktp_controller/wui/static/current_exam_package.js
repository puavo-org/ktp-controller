(function () {
  const TICK_MS = 5000;

  // Returns true if the scheduled start time is in the past.
  function updateScheduledStart() {
    const el = document.getElementById("exam-package-scheduled-start");
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

    const cell = document.getElementById("exam-package-scheduled-start-cell");
    if (cell !== null) {
      cell.classList.toggle("value-error", late);
    }
    const icon = document.getElementById("exam-package-scheduled-start-icon");
    if (icon !== null) {
      KtpWui.setHidden(icon, !late);
    }
    return late;
  }

  function updateStartedAt() {
    const el = document.getElementById("exam-package-started-at");
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
  }

  function updateState(overtime) {
    const el = document.getElementById("exam-package-state");
    if (el === null) {
      return;
    }
    el.textContent = overtime
      ? el.dataset.stateLabel + el.dataset.overtimeSuffix
      : el.dataset.stateLabel;

    const cell = document.getElementById("exam-package-state-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", overtime);
    }
    const icon = document.getElementById("exam-package-state-icon");
    if (icon !== null) {
      KtpWui.setHidden(icon, !overtime);
    }
  }

  // Returns true if the package is running past its scheduled end time.
  function updateScheduledEnd() {
    const el = document.getElementById("exam-package-scheduled-end");
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

    const overtime = overdue && el.dataset.state === "running";
    const cell = document.getElementById("exam-package-scheduled-end-cell");
    if (cell !== null) {
      cell.classList.toggle("value-warning", overtime);
    }
    const icon = document.getElementById("exam-package-scheduled-end-icon");
    if (icon !== null) {
      KtpWui.setHidden(icon, !overtime);
    }
    updateState(overtime);
    return overtime;
  }

  function updateScheduledStartFixed() {
    const el = document.getElementById("exam-package-scheduled-start-fixed");
    if (el === null) {
      return;
    }
    const scheduledStart = new Date(Date.parse(el.dataset.scheduledStart));
    el.textContent = KtpWui.formatShortDateTime(scheduledStart);
  }

  function update() {
    const late = updateScheduledStart();
    updateScheduledStartFixed();
    updateStartedAt();
    const overtime = updateScheduledEnd();

    const header = document.getElementById("current-exam-package-header");
    if (header !== null) {
      header.classList.toggle("value-error", late);
      header.classList.toggle("value-warning", !late && overtime);
    }
    const headerIcon = document.getElementById("current-exam-package-header-icon");
    if (headerIcon !== null) {
      KtpWui.setHidden(headerIcon, !(late || overtime));
    }
  }

  // A live-update swap replaces the whole card, including all the
  // elements above - refresh immediately instead of waiting up to
  // TICK_MS for the next tick.
  document.addEventListener("htmx:afterSwap", update);
  KtpWui.startTicking(update, TICK_MS);
})();
