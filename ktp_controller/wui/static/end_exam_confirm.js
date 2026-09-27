(function () {
  function closeOverlay(overlay) {
    overlay.classList.remove("is-visible");
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".end-exam-button");
    if (trigger === null) {
      return;
    }
    const overlay = document.getElementById("end-exam-confirm-overlay");
    if (overlay === null) {
      return;
    }
    overlay.dataset.sessionUuid = trigger.dataset.sessionUuid;
    overlay.dataset.studentUuid = trigger.dataset.studentUuid;
    const name = document.getElementById("end-exam-confirm-name");
    if (name !== null) {
      name.textContent = trigger.dataset.name;
    }
    overlay.classList.add("is-visible");
  });

  document.addEventListener("click", (event) => {
    const overlay = document.getElementById("end-exam-confirm-overlay");
    if (overlay === null || !overlay.classList.contains("is-visible")) {
      return;
    }
    if (event.target === overlay || event.target.closest(".end-exam-confirm-no, .end-exam-confirm-yes") !== null) {
      closeOverlay(overlay);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    const overlay = document.getElementById("end-exam-confirm-overlay");
    if (overlay !== null) {
      closeOverlay(overlay);
    }
  });
})();
