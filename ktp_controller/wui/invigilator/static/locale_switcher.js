(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const select = document.querySelector("select[name='locale']");
    if (select !== null) {
      select.addEventListener("change", () => select.form.submit());
    }
  });
})();
