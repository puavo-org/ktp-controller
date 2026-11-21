(function () {
  function applyState(hidden) {
    document.querySelectorAll(".birthday-value").forEach((el) => {
      el.textContent = hidden
        ? "•".repeat(el.dataset.birthday.length)
        : el.dataset.birthday;
    });

    document
      .querySelectorAll(".toggle-birthday-visibility-button")
      .forEach((button) => {
        button.setAttribute("aria-pressed", String(!hidden));
        button.setAttribute(
          "aria-label",
          hidden ? button.dataset.showLabel : button.dataset.hideLabel
        );
        KtpWui.setHidden(button.querySelector(".icon-eye-open"), !hidden);
        KtpWui.setHidden(button.querySelector(".icon-eye-closed"), hidden);
      });
  }

  KtpWui.initHiddenToggle({
    attr: "data-birthdays-hidden",
    triggerSelector: ".toggle-birthday-visibility-button",
    swapTargetId: "student-list-groups",
    applyState,
  });
})();
