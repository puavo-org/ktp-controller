(function () {
  const HIDDEN_ATTR = "data-birthdays-hidden";

  function birthdaysHidden() {
    return document.documentElement.getAttribute(HIDDEN_ATTR) !== "false";
  }

  function applyState() {
    const hidden = birthdaysHidden();

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
        button.querySelector(".icon-eye-open").toggleAttribute("hidden", !hidden);
        button.querySelector(".icon-eye-closed").toggleAttribute("hidden", hidden);
      });
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".toggle-birthday-visibility-button");
    if (trigger === null) {
      return;
    }
    document.documentElement.setAttribute(HIDDEN_ATTR, String(!birthdaysHidden()));
    applyState();
  });

  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id !== "student-list-groups") {
      return;
    }
    applyState();
  });
})();
