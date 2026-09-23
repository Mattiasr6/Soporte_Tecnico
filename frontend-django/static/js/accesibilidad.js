(function () {
  var CLAVE = "a11y";
  var raiz = document.documentElement;
  var CLASES = ["a11y-letra-grande", "a11y-letra-xl", "a11y-contraste-alto", "a11y-sin-movimiento"];

  function leer() {
    try {
      return JSON.parse(localStorage.getItem(CLAVE) || "{}") || {};
    } catch (e) {
      return {};
    }
  }

  function aplicar(prefs) {
    CLASES.forEach(function (c) {
      raiz.classList.remove(c);
    });
    if (prefs.letra === "grande") raiz.classList.add("a11y-letra-grande");
    if (prefs.letra === "xl") raiz.classList.add("a11y-letra-xl");
    if (prefs.contraste === "alto") raiz.classList.add("a11y-contraste-alto");
    if (prefs.movimiento === "reducido") raiz.classList.add("a11y-sin-movimiento");
  }

  function guardar(prefs) {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(prefs));
    } catch (e) {
      /* modo privado: se aplica igual, solo no persiste */
    }
    aplicar(prefs);
  }

  window.a11y = { leer: leer, guardar: guardar, aplicar: aplicar };

  document.addEventListener("DOMContentLoaded", function () {
    var controles = document.querySelector('[data-a11y="letra"]');
    if (!controles) return;

    var prefs = leer();
    var letras = document.querySelectorAll('input[name="a11y-letra"]');
    var contrastes = document.querySelectorAll('input[name="a11y-contraste"]');
    var movimiento = document.getElementById("a11y-movimiento");

    function pintarControles() {
      letras.forEach(function (r) {
        r.checked = (prefs.letra || "normal") === r.value;
      });
      contrastes.forEach(function (r) {
        r.checked = (prefs.contraste || "normal") === r.value;
      });
      if (movimiento) movimiento.checked = prefs.movimiento === "reducido";
    }

    letras.forEach(function (r) {
      r.addEventListener("change", function () {
        prefs.letra = r.value;
        guardar(prefs);
      });
    });
    contrastes.forEach(function (r) {
      r.addEventListener("change", function () {
        prefs.contraste = r.value;
        guardar(prefs);
      });
    });
    if (movimiento) {
      movimiento.addEventListener("change", function () {
        prefs.movimiento = movimiento.checked ? "reducido" : "normal";
        guardar(prefs);
      });
    }

    var reset = document.getElementById("a11y-reset");
    if (reset) {
      reset.addEventListener("click", function () {
        prefs = {};
        guardar(prefs);
        pintarControles();
      });
    }

    pintarControles();
  });
})();
