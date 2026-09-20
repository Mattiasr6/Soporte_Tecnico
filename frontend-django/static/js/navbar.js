function mountNavbar(root) {
  var el = typeof root === "string" ? document.querySelector(root) : root;
  if (!el) return null;
  var mq = window.matchMedia("(min-width: 900px)");
  var burger = el.querySelector("[data-navbar-open]");
  var scrim = el.querySelector("[data-navbar-scrim]");
  var aside = el.querySelector("[data-navbar-sidebar]");
  var collapse = el.querySelector("[data-navbar-collapse]");
  var KEY = "st_sidebar_collapsed";
  var SYS = "st_system_view";

  function setCollapsed(v) {
    document.body.classList.toggle("nav-collapsed", v);
    if (collapse) collapse.setAttribute("aria-expanded", String(!v));
    try {
      localStorage.setItem(KEY, v ? "1" : "0");
    } catch (e) {}
  }
  if (collapse) {
    collapse.addEventListener("click", function () {
      if (window.innerWidth < 900) {
        setDrawer(!document.body.classList.contains("nav-open"));
        return;
      }
      setCollapsed(!document.body.classList.contains("nav-collapsed"));
    });
  }
  try {
    if (localStorage.getItem(KEY) === "1" && window.innerWidth >= 900) {
      setCollapsed(true);
    }
  } catch (e) {}

  var open = false;
  function setDrawer(v) {
    open = v;
    document.body.classList.toggle("nav-open", v);
    if (scrim) scrim.hidden = !v;
    if (burger) burger.setAttribute("aria-label", v ? "Cerrar menú" : "Abrir menú");
    document.body.style.overflow = v ? "hidden" : "";
    if (!v && burger) burger.focus();
  }
  function onKey(e) {
    if (e.key === "Escape" && open) setDrawer(false);
  }
  if (burger) burger.addEventListener("click", function () { setDrawer(!open); });
  if (scrim) scrim.addEventListener("click", function () { setDrawer(false); });
  if (aside) {
    aside.addEventListener("click", function (e) {
      if (e.target.closest("a")) setDrawer(false);
    });
  }
  document.addEventListener("keydown", onKey);
  function onMq(e) {
    if (e.matches) setDrawer(false);
  }
  if (mq.addEventListener) mq.addEventListener("change", onMq);

  var sysBtns = Array.prototype.slice.call(el.querySelectorAll("[data-system-view]"));
  function currentSys() {
    try {
      return localStorage.getItem(SYS) || "SOPORTE";
    } catch (e) {
      return "SOPORTE";
    }
  }
  function applySys(s) {
    sysBtns.forEach(function (b) {
      b.setAttribute("aria-selected", String(b.getAttribute("data-system-view") === s));
    });
    el.querySelectorAll("[data-sistema-panel]").forEach(function (p) {
      p.hidden = p.getAttribute("data-sistema-panel") !== s;
    });
    el.setAttribute("data-sistema", s);
    try {
      localStorage.setItem(SYS, s);
    } catch (e) {}
  }
  sysBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      applySys(b.getAttribute("data-system-view"));
      window.dispatchEvent(
        new CustomEvent("od:system-view-change", { detail: b.getAttribute("data-system-view") })
      );
    });
  });
  if (sysBtns.length) {
    applySys(currentSys());
  } else {
    el.setAttribute("data-sistema", "SOPORTE");
  }

  var notes = el.querySelector("[data-navbar-notes]");
  if (notes) {
    notes.addEventListener("click", function () {
      window.dispatchEvent(new CustomEvent("od:notes-placeholder"));
    });
  }

  window.dispatchEvent(new CustomEvent("od:navbar-ready"));
  return {
    destroy: function () {
      document.removeEventListener("keydown", onKey);
      if (mq.removeEventListener) mq.removeEventListener("change", onMq);
    },
  };
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-navbar]").forEach(function (n) {
    mountNavbar(n);
  });
});
