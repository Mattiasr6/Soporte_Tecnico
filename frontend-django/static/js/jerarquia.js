function initRuta(root) {
  if (!root || root.dataset.jerarquiaLista === "1") return;
  var dataArbol = root.querySelector(".arbol-data");
  if (!dataArbol) return;
  var ARBOL;
  try {
    ARBOL = JSON.parse(dataArbol.textContent);
  } catch (e) {
    return;
  }

  var arbolEl = root.querySelector(".arbol");
  var filtroEl = root.querySelector(".filtro-arbol");
  var cajaEl = root.querySelector(".selector-jerarquia");
  var rutaEl = root.querySelector(".ruta-elegida");
  var rutaTexto = root.querySelector(".ruta-texto");
  var errorEl = root.querySelector("[data-error-area]");
  var inpP = root.querySelector('[data-rol="padre"]');
  var inpG = root.querySelector('[data-rol="grupo"]');
  var inpA = root.querySelector('[data-rol="area"]');
  if (!arbolEl || !filtroEl || !cajaEl || !rutaEl || !inpA) return;

  var CONTEOS = null;
  var dataConteos = root.querySelector(".conteos-data");
  if (dataConteos) {
    try {
      CONTEOS = JSON.parse(dataConteos.textContent);
    } catch (e) {
      CONTEOS = null;
    }
  }

  function cuenta(clave, id) {
    var items = CONTEOS && CONTEOS[clave];
    if (!items) return "";
    for (var i = 0; i < items.length; i++) {
      if (items[i].id == id) return items[i].total;
    }
    return "";
  }

  function norm(texto) {
    return (texto || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function esc(texto) {
    return String(texto == null ? "" : texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var areasPorPadre = {};
  var areasPorGrupo = {};
  (ARBOL.areas || []).forEach(function (a) {
    if (!areasPorPadre[a.grupo_padre_id]) areasPorPadre[a.grupo_padre_id] = [];
    areasPorPadre[a.grupo_padre_id].push(a);
    if (a.grupo_id) {
      if (!areasPorGrupo[a.grupo_id]) areasPorGrupo[a.grupo_id] = [];
      areasPorGrupo[a.grupo_id].push(a);
    }
  });
  var gruposPorPadre = {};
  (ARBOL.grupos || []).forEach(function (g) {
    if (!gruposPorPadre[g.grupo_padre_id]) gruposPorPadre[g.grupo_padre_id] = [];
    gruposPorPadre[g.grupo_padre_id].push(g);
  });

  function botonArea(area, padre, grupo) {
    var ruta = padre.nombre + (grupo ? " › " + grupo.nombre : "") + " › " + area.nombre;
    var c = cuenta("areas", area.id);
    return (
      '<button type="button" class="arbol-area" data-area="' +
      area.id +
      '" data-padre="' +
      padre.id +
      '"' +
      (grupo ? ' data-grupo="' + grupo.id + '"' : "") +
      ' data-busca="' +
      esc(norm(ruta)) +
      '" data-ruta="' +
      esc(ruta) +
      '"><span class="arbol-nombre">' +
      esc(area.nombre) +
      "</span>" +
      (c === "" ? "" : '<span class="arbol-cuenta">' + c + "</span>") +
      "</button>"
    );
  }

  function filaConteo(clase, nombre, total, extras) {
    return (
      '<div class="arbol-fila ' +
      clase +
      '"' +
      (extras || "") +
      '><button type="button" class="arbol-toggle" data-toggle aria-expanded="true">▾</button>' +
      "<span>" +
      esc(nombre) +
      "</span>" +
      (total === "" ? "" : '<span class="arbol-cuenta">' + total + "</span>") +
      "</div>"
    );
  }

  var html = "";
  (ARBOL.padres || []).forEach(function (padre) {
    var grupos = gruposPorPadre[padre.id] || [];
    var directas = (areasPorPadre[padre.id] || []).filter(function (a) {
      return !a.grupo_id;
    });
    html += '<div class="arbol-sector" data-sector="' + padre.id + '">';
    html += filaConteo("arbol-sector-fila", padre.nombre, cuenta("padres", padre.id));
    html += '<div class="arbol-hijos">';
    grupos.forEach(function (grupo) {
      var rutaGrupo = padre.nombre + " › " + grupo.nombre;
      html += '<div class="arbol-grupo" data-grupo="' + grupo.id + '">';
      html += filaConteo(
        "arbol-grupo-fila",
        grupo.nombre,
        cuenta("grupos", grupo.id),
        ' data-padre="' +
          padre.id +
          '" data-grupo="' +
          grupo.id +
          '" data-ruta="' +
          esc(rutaGrupo) +
          '"'
      );
      html += '<div class="arbol-hijos">';
      (areasPorGrupo[grupo.id] || []).forEach(function (a) {
        html += botonArea(a, padre, grupo);
      });
      html += "</div></div>";
    });
    directas.forEach(function (a) {
      html += botonArea(a, padre, null);
    });
    html += "</div></div>";
  });
  arbolEl.innerHTML = html;

  function aplicarFiltro() {
    var q = norm(filtroEl.value);
    var areas = arbolEl.querySelectorAll(".arbol-area");
    for (var i = 0; i < areas.length; i++) {
      areas[i].hidden = !!q && areas[i].dataset.busca.indexOf(q) === -1;
    }
    var sectores = arbolEl.querySelectorAll(".arbol-sector");
    for (var s = 0; s < sectores.length; s++) {
      var sector = sectores[s];
      var visiblesSector = sector.querySelectorAll(".arbol-area:not([hidden])").length;
      sector.hidden = visiblesSector === 0;
      if (q && visiblesSector) {
        sector.querySelector(".arbol-hijos").hidden = false;
        sector.querySelector(".arbol-toggle").textContent = "▾";
      }
      var grupos = sector.querySelectorAll(".arbol-grupo");
      for (var g = 0; g < grupos.length; g++) {
        var visiblesGrupo = grupos[g].querySelectorAll(".arbol-area:not([hidden])").length;
        grupos[g].hidden = visiblesGrupo === 0;
        if (q && visiblesGrupo) {
          grupos[g].querySelector(".arbol-hijos").hidden = false;
          grupos[g].querySelector(".arbol-toggle").textContent = "▾";
        }
      }
    }
  }

  function elegir(boton) {
    inpP.value = boton.dataset.padre || "";
    inpG.value = boton.dataset.grupo || "";
    inpA.value = boton.dataset.area || "";
    rutaTexto.textContent = boton.dataset.ruta;
    rutaEl.hidden = false;
    cajaEl.hidden = true;
    if (errorEl) errorEl.hidden = true;
  }

  function mostrarArbol() {
    cajaEl.hidden = false;
    rutaEl.hidden = true;
    filtroEl.value = "";
    aplicarFiltro();
    filtroEl.focus();
  }

  arbolEl.addEventListener("click", function (ev) {
    var toggle = ev.target.closest("[data-toggle]");
    if (toggle) {
      var contenedor = toggle.closest(".arbol-sector, .arbol-grupo");
      var hijos = contenedor.querySelector(".arbol-hijos");
      hijos.hidden = !hijos.hidden;
      toggle.textContent = hijos.hidden ? "▸" : "▾";
      toggle.setAttribute("aria-expanded", hijos.hidden ? "false" : "true");
      return;
    }
    var grupoFila = ev.target.closest(".arbol-grupo-fila");
    if (grupoFila) {
      elegir(grupoFila);
      return;
    }
    var area = ev.target.closest(".arbol-area");
    if (area) elegir(area);
  });
  filtroEl.addEventListener("input", aplicarFiltro);

  var btnCambiar = root.querySelector("[data-cambiar-area]");
  if (btnCambiar) btnCambiar.addEventListener("click", mostrarArbol);

  var idPrevio = root.dataset.area;
  if (idPrevio) {
    var previo = arbolEl.querySelector('.arbol-area[data-area="' + idPrevio + '"]');
    if (previo) {
      elegir(previo);
    } else {
      rutaTexto.textContent = "Área actual (ya no está en la lista activa)";
      rutaEl.hidden = false;
      cajaEl.hidden = true;
    }
  } else if (root.dataset.grupo) {
    var previoGrupo = arbolEl.querySelector(
      '.arbol-grupo-fila[data-grupo="' + root.dataset.grupo + '"]'
    );
    if (previoGrupo) elegir(previoGrupo);
  }

  var form = root.closest("form");
  if (form) {
    form.addEventListener("submit", function (ev) {
      if (!inpA.value && !inpG.value) {
        ev.preventDefault();
        if (errorEl) {
          errorEl.hidden = false;
          errorEl.scrollIntoView({ block: "center" });
        }
        mostrarArbol();
      }
    });
  }

  root.dataset.jerarquiaLista = "1";
}

function initJerarquias(scope) {
  (scope || document).querySelectorAll("[data-ruta3]").forEach(initRuta);
}

window.initJerarquias = initJerarquias;
document.addEventListener("DOMContentLoaded", function () {
  initJerarquias(document);
});
