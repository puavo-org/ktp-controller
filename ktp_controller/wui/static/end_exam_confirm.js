(function () {
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
        // student_list_groups.html.j2 / live-update).
        return;
      }
      if (button.isConnected) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }
    }
    document.addEventListener("htmx:afterRequest", onAfterRequest);
  }

  KtpWui.initConfirmOverlay({
    triggerSelector: ".end-exam-button",
    overlayId: "end-exam-confirm-overlay",
    yesSelector: ".end-exam-confirm-yes",
    noSelector: ".end-exam-confirm-no",
    onOpen: (trigger) => {
      document.getElementById("end-exam-confirm-session-uuid").value =
        trigger.dataset.sessionUuid;
      document.getElementById("end-exam-confirm-student-uuid").value =
        trigger.dataset.studentUuid;
      const name = document.getElementById("end-exam-confirm-name");
      if (name !== null) {
        name.textContent = trigger.dataset.name;
      }
    },
    onConfirm: armBusyState,
  });
})();
