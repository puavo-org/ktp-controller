(function () {
  function applyState() {
    document.querySelectorAll(".last-changed-value").forEach((el) => {
      const parsed = new Date(Date.parse(el.dataset.lastChanged));
      el.textContent = KtpWui.formatShortDateTime(parsed);
    });
  }

  document.addEventListener("DOMContentLoaded", applyState);
  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id !== "student-list-groups") {
      return;
    }
    applyState();
  });
})();
