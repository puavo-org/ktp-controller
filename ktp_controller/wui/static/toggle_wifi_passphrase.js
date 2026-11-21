(function () {
  function applyState(hidden) {
    const button = document.querySelector(".toggle-wifi-passphrase-button");
    if (button === null) {
      return;
    }
    const passphrase = button.dataset.wifiPassphrase;
    button.textContent = hidden ? "•".repeat(passphrase.length) : passphrase;
    button.setAttribute("aria-pressed", String(!hidden));
    button.setAttribute(
      "aria-label",
      hidden ? button.dataset.showLabel : button.dataset.hideLabel
    );
  }

  KtpWui.initHiddenToggle({
    attr: "data-wifi-passphrase-hidden",
    triggerSelector: ".toggle-wifi-passphrase-button",
    swapTargetId: "app-sidebar",
    applyState,
  });
})();
