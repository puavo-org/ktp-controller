(function () {
  function applyState(hidden) {
    const aside = document.getElementById("app-sidebar");
    if (aside !== null) {
      KtpWui.setHidden(aside, hidden);
    }
    document.querySelectorAll(".sidebar-toggle-button").forEach((button) => {
      button.setAttribute("aria-expanded", String(!hidden));
    });
  }

  KtpWui.initHiddenToggle({
    attr: "data-sidebar-hidden",
    triggerSelector: ".sidebar-toggle-button, .sidebar-close-button",
    swapTargetId: "app-sidebar",
    applyState,
  });
})();
