(function () {
  "use strict";

  // Mobile navigation toggle
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }

  // Dismissible messages
  document.querySelectorAll("[data-dismiss]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var msg = btn.closest(".message");
      if (msg) msg.remove();
    });
  });

  // Search-as-you-type suggestions
  var input = document.querySelector("[data-search-input]");
  var box = document.querySelector("[data-suggest]");
  if (input && box) {
    var timer = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 2) {
        box.hidden = true;
        return;
      }
      timer = setTimeout(function () {
        fetch(box.dataset.url + "?q=" + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            box.innerHTML = "";
            if (!data.results.length) {
              box.hidden = true;
              return;
            }
            data.results.forEach(function (item) {
              var a = document.createElement("a");
              a.href = item.url;
              var name = document.createElement("span");
              name.textContent = item.name;
              var price = document.createElement("strong");
              price.textContent = item.price;
              a.appendChild(name);
              a.appendChild(price);
              box.appendChild(a);
            });
            box.hidden = false;
          })
          .catch(function () { box.hidden = true; });
      }, 200);
    });
    document.addEventListener("click", function (e) {
      if (e.target !== input && !box.contains(e.target)) box.hidden = true;
    });
  }
})();
