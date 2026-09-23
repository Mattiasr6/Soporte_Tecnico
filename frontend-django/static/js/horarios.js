(function () {
  var CAMPOS = ["h1", "f1", "h2", "f2"];

  document.querySelectorAll("select.plantilla").forEach(function (selector) {
    selector.addEventListener("change", function () {
      var fila = selector.dataset.fila;
      if (!fila || !selector.value) return;
      var partes = selector.value.split("|");
      CAMPOS.forEach(function (campo, i) {
        var input = document.getElementById(fila + "_" + campo);
        if (input) input.value = partes[i] || "";
      });
      selector.value = "";
    });
  });
})();
