(function () {
  function closeOverlay(overlay) {
    overlay.classList.remove("is-visible");
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".change-access-code-button");
    if (trigger === null) {
      return;
    }
    const overlay = document.getElementById("change-access-code-confirm-overlay");
    if (overlay === null) {
      return;
    }
    overlay.classList.add("is-visible");
  });

  document.addEventListener("click", (event) => {
    const overlay = document.getElementById("change-access-code-confirm-overlay");
    if (overlay === null || !overlay.classList.contains("is-visible")) {
      return;
    }
    if (event.target === overlay || event.target.closest(".change-access-code-confirm-no, .change-access-code-confirm-yes") !== null) {
      closeOverlay(overlay);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    const overlay = document.getElementById("change-access-code-confirm-overlay");
    if (overlay !== null) {
      closeOverlay(overlay);
    }
  });
})();
