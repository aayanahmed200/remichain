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

  // ---------- Custom dropdowns ----------
  //
  // The native <select> stays in the form as the value that gets submitted;
  // it is only hidden and mirrored by a button + listbox. With JavaScript
  // off, or before this runs, the plain select is what you see and use.

  var TICK =
    '<svg class="select-tick" width="15" height="15" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>';

  var CHEVRON =
    '<svg class="select-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';

  var openState = null;

  function closeDropdown(returnFocus) {
    if (!openState) return;
    var state = openState;
    openState = null;
    state.list.hidden = true;
    state.list.classList.remove("select-list--up");
    state.button.setAttribute("aria-expanded", "false");
    if (returnFocus) state.button.focus();
  }

  function selectedOption(select) {
    return select.options[select.selectedIndex] || null;
  }

  function syncValue(state) {
    var option = selectedOption(state.select);
    state.value.textContent = option ? option.textContent.trim() : "";
    Array.prototype.forEach.call(state.items, function (item, index) {
      item.setAttribute("aria-selected", index === state.select.selectedIndex ? "true" : "false");
    });
  }

  function buildList(state) {
    var select = state.select;
    state.list.textContent = "";
    state.items = [];

    Array.prototype.forEach.call(select.options, function (option, index) {
      var item = document.createElement("li");
      item.className = "select-option";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", index === select.selectedIndex ? "true" : "false");
      item.tabIndex = -1;
      item.dataset.index = String(index);

      var label = document.createElement("span");
      label.className = "select-option-label";
      label.textContent = option.textContent.trim();
      item.appendChild(label);
      item.insertAdjacentHTML("beforeend", TICK);

      if (option.disabled) item.setAttribute("aria-disabled", "true");
      else item.addEventListener("click", function () { choose(state, index); });

      state.list.appendChild(item);
      state.items.push(item);
    });
  }

  function focusIndex(state, index) {
    if (!state.items.length) return;
    var clamped = Math.max(0, Math.min(index, state.items.length - 1));
    state.items[clamped].focus({ preventScroll: false });
  }

  function choose(state, index) {
    var option = state.select.options[index];
    if (!option || option.disabled) return;
    state.select.selectedIndex = index;
    // Fires change so any listener (and the visible label) stays in step.
    state.select.dispatchEvent(new Event("change", { bubbles: true }));
    syncValue(state);
    closeDropdown(true);
  }

  function openDropdown(state, direction) {
    if (openState && openState !== state) closeDropdown(false);
    openState = state;

    buildList(state);
    state.list.hidden = false;
    state.button.setAttribute("aria-expanded", "true");

    var rect = state.button.getBoundingClientRect();
    var below = window.innerHeight - rect.bottom;
    state.list.classList.toggle("select-list--up", below < 240 && rect.top > below);

    var start = state.select.selectedIndex;
    if (direction) start = Math.max(0, Math.min(start + direction, state.items.length - 1));
    focusIndex(state, start < 0 ? 0 : start);
  }

  function enhanceSelect(select) {
    if (select.dataset.enhanced === "true" || select.multiple) return;
    select.dataset.enhanced = "true";

    var wrap = document.createElement("div");
    wrap.className = "select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);

    var button = document.createElement("button");
    button.type = "button";
    button.className = "select-button";
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    if (select.disabled) button.disabled = true;
    if (select.required) button.setAttribute("aria-required", "true");

    // Point the button at the field's own label so screen readers announce it.
    var label = select.id ? document.querySelector('label[for="' + select.id + '"]') : null;
    if (label) {
      if (!label.id) label.id = (select.id || "select") + "-label";
      button.setAttribute("aria-labelledby", label.id);
    } else if (select.getAttribute("aria-label")) {
      button.setAttribute("aria-label", select.getAttribute("aria-label"));
    }

    var value = document.createElement("span");
    value.className = "select-value";
    button.appendChild(value);
    button.insertAdjacentHTML("beforeend", CHEVRON);
    wrap.appendChild(button);

    var list = document.createElement("ul");
    list.className = "select-list";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    if (select.id) list.id = select.id + "-list";
    button.setAttribute("aria-controls", list.id || "");
    wrap.appendChild(list);

    var state = { select: select, wrap: wrap, button: button, value: value, list: list, items: [] };
    syncValue(state);

    button.addEventListener("click", function () {
      if (openState === state) closeDropdown(true);
      else openDropdown(state, 0);
    });

    button.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        openDropdown(state, event.key === "ArrowDown" ? 1 : -1);
      }
    });

    list.addEventListener("keydown", function (event) {
      var current = state.items.indexOf(document.activeElement);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusIndex(state, current + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        focusIndex(state, current - 1);
      } else if (event.key === "Home") {
        event.preventDefault();
        focusIndex(state, 0);
      } else if (event.key === "End") {
        event.preventDefault();
        focusIndex(state, state.items.length - 1);
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (current >= 0) choose(state, Number(state.items[current].dataset.index));
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeDropdown(true);
      } else if (event.key === "Tab") {
        closeDropdown(false);
      } else if (event.key.length === 1 && /\S/.test(event.key)) {
        // Type-ahead: jump to the next option starting with that letter.
        var letter = event.key.toLowerCase();
        var start = current + 1;
        for (var step = 0; step < state.items.length; step += 1) {
          var index = (start + step) % state.items.length;
          var text = state.select.options[index].textContent.trim().toLowerCase();
          if (text.charAt(0) === letter) {
            event.preventDefault();
            focusIndex(state, index);
            break;
          }
        }
      }
    });

    select.addEventListener("change", function () { syncValue(state); });

    var form = select.closest("form");
    if (form) {
      form.addEventListener("reset", function () {
        window.setTimeout(function () { syncValue(state); }, 0);
      });
    }
  }

  document.addEventListener("pointerdown", function (event) {
    if (openState && !openState.wrap.contains(event.target)) closeDropdown(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeDropdown(true);
  });

  window.addEventListener("resize", function () { closeDropdown(false); });

  document.querySelectorAll("select").forEach(enhanceSelect);
})();
