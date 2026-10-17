(function () {
  "use strict";

  var THEMES = ["auto", "light", "dark"];
  var STORAGE_KEY = "agent-meter-theme";
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");

  function readStoredTheme() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || "auto";
    } catch (error) {
      console.warn("agent-meter: theme preference unavailable", error);
      return "auto";
    }
  }

  function storeTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      console.warn("agent-meter: theme preference not saved", error);
    }
  }

  function applyTheme(theme) {
    if (theme === "auto") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    if (toggle) {
      toggle.textContent = "Theme: " + theme;
    }
  }

  var currentTheme = readStoredTheme();
  applyTheme(currentTheme);
  if (toggle) {
    toggle.addEventListener("click", function () {
      currentTheme = THEMES[(THEMES.indexOf(currentTheme) + 1) % THEMES.length];
      applyTheme(currentTheme);
      storeTheme(currentTheme);
    });
  }

  function cellValue(row, index) {
    var cell = row.children[index];
    if (!cell) {
      return "";
    }
    return cell.hasAttribute("data-sort") ? cell.getAttribute("data-sort") : cell.textContent.trim();
  }

  function compare(a, b) {
    var x = parseFloat(a);
    var y = parseFloat(b);
    var numeric = a !== "" && b !== "" && !isNaN(x) && !isNaN(y) && isFinite(a) && isFinite(b);
    if (numeric) {
      return x - y;
    }
    return a.localeCompare(b);
  }

  function makeSortable(table) {
    var headers = table.querySelectorAll(":scope > thead > tr > th");
    headers.forEach(function (header, index) {
      header.addEventListener("click", function () {
        var body = table.tBodies[0];
        if (!body) {
          return;
        }
        var ascending = header.getAttribute("aria-sort") !== "ascending";
        headers.forEach(function (other) { other.removeAttribute("aria-sort"); });
        header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
        var rows = Array.prototype.slice.call(body.querySelectorAll(":scope > tr"));
        rows.sort(function (r1, r2) {
          var result = compare(cellValue(r1, index), cellValue(r2, index));
          return ascending ? result : -result;
        });
        rows.forEach(function (row) { body.appendChild(row); });
      });
    });
  }

  document.querySelectorAll("table.sortable").forEach(makeSortable);

  var filter = document.getElementById("task-filter");
  var tasksTable = document.getElementById("tasks-table");
  if (filter && tasksTable && tasksTable.tBodies[0]) {
    filter.addEventListener("input", function () {
      var needle = filter.value.trim().toLowerCase();
      var rows = tasksTable.tBodies[0].querySelectorAll(":scope > tr");
      rows.forEach(function (row) {
        var visible = needle === "" || row.textContent.toLowerCase().indexOf(needle) !== -1;
        row.hidden = !visible;
      });
    });
  }

  // Tooltips: one shared element; values come from data-tip / data-val via textContent.
  var tip = document.createElement("div");
  tip.className = "tooltip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  var tipKey = document.createElement("i");
  var tipValue = document.createElement("span");
  tipValue.className = "tip-value";
  var tipLabel = document.createElement("span");
  tipLabel.className = "tip-label";
  tip.appendChild(tipKey);
  tip.appendChild(tipValue);
  tip.appendChild(tipLabel);
  document.body.appendChild(tip);

  var TONE = /^(s[1-7]|s-other|o[1-3])$/;

  function markOf(node) {
    return node && node.closest ? node.closest("[data-tip]") : null;
  }

  function place(x, y) {
    var pad = 12;
    var rect = tip.getBoundingClientRect();
    var left = x + pad;
    var top = y + pad;
    if (left + rect.width > window.innerWidth - 4) {
      left = Math.max(4, x - rect.width - pad);
    }
    if (top + rect.height > window.innerHeight - 4) {
      top = Math.max(4, y - rect.height - pad);
    }
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }

  function show(mark, x, y) {
    var tone = mark.getAttribute("data-tone") || "";
    tipKey.className = "tip-key " + (TONE.test(tone) ? tone : "s1");
    tipValue.textContent = mark.getAttribute("data-val") || "";
    tipLabel.textContent = mark.getAttribute("data-tip") || "";
    tip.hidden = false;
    place(x, y);
  }

  function hide() {
    tip.hidden = true;
  }

  document.addEventListener("pointermove", function (event) {
    var mark = markOf(event.target);
    if (mark) {
      show(mark, event.clientX, event.clientY);
    } else if (!tip.hidden) {
      hide();
    }
  });
  document.addEventListener("pointerleave", hide);
  document.addEventListener("focusin", function (event) {
    var mark = markOf(event.target);
    if (mark) {
      var rect = mark.getBoundingClientRect();
      show(mark, rect.left + rect.width / 2, rect.top);
    }
  });
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, { passive: true });
})();
