(function () {
  function applyState(hidden) {
    const button = document.querySelector(".toggle-access-code-button");
    if (button === null) {
      return;
    }
    const code = button.dataset.accessCode;
    button.textContent = hidden ? "•".repeat(code.length) : code;
    button.setAttribute("aria-pressed", String(!hidden));
    button.setAttribute(
      "aria-label",
      hidden ? button.dataset.showLabel : button.dataset.hideLabel
    );
  }

  KtpWui.initHiddenToggle({
    attr: "data-access-code-hidden",
    triggerSelector: ".toggle-access-code-button",
    swapTargetId: "student-access-code",
    applyState,
  });
})();
