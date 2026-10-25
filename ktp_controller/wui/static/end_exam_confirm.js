(function () {
  function closeOverlay(overlay) {
    overlay.classList.remove("is-visible");
  }

  let pendingButton = null;

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".end-exam-button");
    if (trigger === null) {
      return;
    }
    const overlay = document.getElementById("end-exam-confirm-overlay");
    if (overlay === null) {
      return;
    }
    pendingButton = trigger;
    document.getElementById("end-exam-confirm-session-uuid").value =
      trigger.dataset.sessionUuid;
    document.getElementById("end-exam-confirm-student-uuid").value =
      trigger.dataset.studentUuid;
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
    if (event.target.closest(".end-exam-confirm-yes") !== null) {
      armBusyState(pendingButton);
    }
    if (event.target === overlay || event.target.closest(".end-exam-confirm-no, .end-exam-confirm-yes") !== null) {
      closeOverlay(overlay);
    }
  });

  function armBusyState(button) {
    if (button === null || !button.isConnected) {
      return;
    }
    button.disabled = true;
    button.setAttribute("aria-busy", "true");

    function onAfterRequest(event) {
      if (!event.target.classList || !event.target.classList.contains("end-exam-confirm-yes")) {
        return;
      }
      document.removeEventListener("htmx:afterRequest", onAfterRequest);
      if (event.detail.successful) {
        // Left busy on purpose: cleared for real when the next live
        // table refresh replaces this button with a fresh one (see
        // student_list_groups.html.j2 / invigilator-live-update).
        return;
      }
      if (button.isConnected) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }
    }
    document.addEventListener("htmx:afterRequest", onAfterRequest);
  }

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
