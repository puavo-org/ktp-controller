(function () {
  function closeOverlay(overlay) {
    overlay.classList.remove("is-visible");
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".allow-audio-replay-button");
    if (trigger === null) {
      return;
    }
    const overlay = document.getElementById("allow-audio-replay-confirm-overlay");
    if (overlay === null) {
      return;
    }
    document.getElementById("allow-audio-replay-confirm-student-uuid").value =
      trigger.dataset.studentUuid;
    const name = document.getElementById("allow-audio-replay-confirm-name");
    if (name !== null) {
      name.textContent = trigger.dataset.name;
    }
    const lastAudio = document.getElementById(
      "allow-audio-replay-confirm-last-audio",
    );
    if (lastAudio !== null) {
      lastAudio.textContent = trigger.dataset.lastAudio;
    }
    const examTitle = document.getElementById(
      "allow-audio-replay-confirm-exam-title",
    );
    if (examTitle !== null) {
      examTitle.textContent = trigger.dataset.examTitle;
    }
    overlay.classList.add("is-visible");
  });

  document.addEventListener("click", (event) => {
    const overlay = document.getElementById("allow-audio-replay-confirm-overlay");
    if (overlay === null || !overlay.classList.contains("is-visible")) {
      return;
    }
    if (event.target === overlay || event.target.closest(".allow-audio-replay-confirm-no, .allow-audio-replay-confirm-yes") !== null) {
      closeOverlay(overlay);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    const overlay = document.getElementById("allow-audio-replay-confirm-overlay");
    if (overlay !== null) {
      closeOverlay(overlay);
    }
  });
})();
