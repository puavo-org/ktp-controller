(function () {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".end-exam-button, .end-exam-confirm-no");
    if (trigger === null) {
      return;
    }
    const cell = trigger.closest(".end-exam-cell");
    cell.querySelector(".end-exam-button").hidden = !cell.querySelector(".end-exam-button").hidden;
    cell.querySelector(".end-exam-confirm-box").hidden = !cell.querySelector(".end-exam-confirm-box").hidden;
  });
})();
