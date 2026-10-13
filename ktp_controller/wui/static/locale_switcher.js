(function () {
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".locale-select").forEach((select) => {
      select.addEventListener("change", () => select.form.submit());
    });
  });
})();
