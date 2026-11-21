(function () {
  KtpWui.initConfirmOverlay({
    triggerSelector: ".allow-audio-replay-button",
    overlayId: "allow-audio-replay-confirm-overlay",
    yesSelector: ".allow-audio-replay-confirm-yes",
    noSelector: ".allow-audio-replay-confirm-no",
    onOpen: (trigger) => {
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
    },
  });
})();
