function initRuta(root) {
  var data = root.querySelector(".arbol-data");
  if (!data) return;
  var ARBOL;
  try {
    ARBOL = JSON.parse(data.textContent);
  } catch (e) {
    return;
  }
  var selP = root.querySelector("#sel-padre");
  var selG = root.querySelector("#sel-grupo");
  var selA = root.querySelector("#sel-area");
  if (!selP || !selG || !selA) return;

  function gruposDe(pid) {
    return ARBOL.grupos.filter(function (g) {
      return g.grupo_padre_id == pid;
    });
  }
  function areasDe(gid, pid) {
    return ARBOL.areas.filter(function (a) {
      return gid ? a.grupo_id == gid : a.grupo_padre_id == pid && !a.grupo_id;
    });
  }
  function llenarGrupos(pid) {
    selG.length = 1;
    gruposDe(pid).forEach(function (g) {
      selG.add(new Option(g.nombre, g.id));
    });
  }
  function llenarAreas(gid, pid) {
    selA.length = 1;
    areasDe(gid, pid).forEach(function (a) {
      selA.add(new Option(a.nombre, a.id));
    });
  }

  selP.onchange = function () {
    llenarGrupos(selP.value);
    llenarAreas("", selP.value);
  };
  selG.onchange = function () {
    llenarAreas(selG.value, selP.value);
  };

  ARBOL.padres.forEach(function (p) {
    selP.add(new Option(p.nombre, p.id));
  });

  var preP = root.dataset.padre;
  var preG = root.dataset.grupo;
  var preA = root.dataset.area;
  if (preP) {
    selP.value = preP;
    llenarGrupos(preP);
    if (preG) {
      selG.value = preG;
      llenarAreas(preG, preP);
    } else {
      llenarAreas("", preP);
    }
    if (preA) selA.value = preA;
  }
}

function initJerarquias(scope) {
  (scope || document).querySelectorAll("[data-ruta3]").forEach(initRuta);
}

window.initJerarquias = initJerarquias;
document.addEventListener("DOMContentLoaded", function () {
  initJerarquias(document);
});
