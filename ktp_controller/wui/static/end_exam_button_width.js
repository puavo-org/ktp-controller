(function () {
  function measure() {
    const sample = document.querySelector(".end-exam-button");
    if (sample === null) {
      return;
    }
    const probe = sample.cloneNode(true);
    probe.removeAttribute("data-session-uuid");
    probe.removeAttribute("data-student-uuid");
    probe.removeAttribute("data-name");
    probe.setAttribute("aria-hidden", "true");
    probe.tabIndex = -1;
    probe.style.position = "absolute";
    probe.style.visibility = "hidden";
    probe.style.width = "auto";
    sample.insertAdjacentElement("afterend", probe);
    try {
      probe.disabled = false;
      probe.removeAttribute("aria-busy");
      const plainWidth = probe.offsetWidth;
      probe.disabled = true;
      probe.setAttribute("aria-busy", "true");
      const busyWidth = probe.offsetWidth;
      document.documentElement.style.setProperty(
        "--end-exam-button-width",
        `${Math.max(plainWidth, busyWidth)}px`,
      );
    } finally {
      probe.remove();
    }
  }

  document.addEventListener("DOMContentLoaded", measure);
  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id === "student-list-groups") {
      measure();
    }
  });
})();
