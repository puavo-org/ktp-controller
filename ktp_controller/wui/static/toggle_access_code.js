(function () {
  const HIDDEN_ATTR = "data-access-code-hidden";

  function accessCodeHidden() {
    return document.documentElement.getAttribute(HIDDEN_ATTR) !== "false";
  }

  function applyState() {
    const hidden = accessCodeHidden();

    const codeText = document.querySelector(".access-code-text[data-access-code]");
    if (codeText !== null) {
      const code = codeText.dataset.accessCode;
      codeText.textContent = hidden ? "•".repeat(code.length) : code;
    }

    const button = document.querySelector(".toggle-access-code-button");
    if (button === null) {
      return;
    }
    button.setAttribute("aria-pressed", String(!hidden));
    button.setAttribute(
      "aria-label",
      hidden ? button.dataset.showLabel : button.dataset.hideLabel
    );
    button.querySelector(".icon-eye-open").toggleAttribute("hidden", !hidden);
    button.querySelector(".icon-eye-closed").toggleAttribute("hidden", hidden);
  }

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".toggle-access-code-button");
    if (trigger === null) {
      return;
    }
    document.documentElement.setAttribute(HIDDEN_ATTR, String(!accessCodeHidden()));
    applyState();
  });

  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id !== "student-access-code") {
      return;
    }
    applyState();
  });
})();
