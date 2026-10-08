(function () {
  let collapsedExamTitles = null;

  document.body.addEventListener("htmx:beforeSwap", (event) => {
    if (event.detail.target.id !== "student-list-groups") {
      return;
    }
    collapsedExamTitles = new Set(
      Array.from(
        event.detail.target.querySelectorAll(".exam-group:not([open])")
      ).map((details) => details.dataset.examTitle)
    );
  });

  document.body.addEventListener("htmx:afterSwap", () => {
    if (collapsedExamTitles === null) {
      return;
    }
    document
      .querySelectorAll("#student-list-groups .exam-group")
      .forEach((details) => {
        details.open = !collapsedExamTitles.has(details.dataset.examTitle);
      });
    collapsedExamTitles = null;
  });
})();
