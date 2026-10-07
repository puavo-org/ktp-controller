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
    trigger.textContent = anyOpen
      ? trigger.dataset.expandLabel
      : trigger.dataset.collapseLabel;
  });
})();
