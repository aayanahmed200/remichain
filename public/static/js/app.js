// Progressive enhancement only: every form still submits without JavaScript.
(function () {
  "use strict";

  // Show a spinner and block double submits once the form has been sent.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches || !form.matches("form[data-busy]")) return;

    var button = form.querySelector('button[type="submit"]');
    if (!button) return;

    var label = button.textContent.trim();

    // Runs after the browser has dispatched the submission, so the request is not cancelled.
    window.setTimeout(function () {
      button.setAttribute("aria-busy", "true");
      button.disabled = true;
      button.textContent = "";
      var spinner = document.createElement("span");
      spinner.className = "spinner";
      spinner.setAttribute("aria-hidden", "true");
      button.appendChild(spinner);
      button.appendChild(document.createTextNode(" " + label));
    }, 0);
  });

  // Fade confirmations out after a while so they do not pile up on repeat actions.
  document.querySelectorAll("[data-flash]").forEach(function (flash) {
    if (flash.classList.contains("flash-error")) return;
    window.setTimeout(function () {
      flash.classList.add("is-leaving");
      window.setTimeout(function () { flash.remove(); }, 350);
    }, 6000);
  });
})();
