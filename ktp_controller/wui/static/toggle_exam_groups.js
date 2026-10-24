(function () {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("#toggle-exam-groups-button");
    if (trigger === null) {
      return;
    }
    const groups = document.querySelectorAll("#student-list-groups .exam-group");
    const anyOpen = Array.from(groups).some((details) => details.open);
    groups.forEach((details) => {
      details.open = !anyOpen;
    });
    const label = anyOpen
      ? trigger.dataset.expandLabel
      : trigger.dataset.collapseLabel;
    trigger.title = label;
    trigger.setAttribute("aria-label", label);
    trigger.querySelector(".icon-chevron-up").toggleAttribute("hidden", anyOpen);
    trigger.querySelector(".icon-chevron-down").toggleAttribute("hidden", !anyOpen);
  });
})();
