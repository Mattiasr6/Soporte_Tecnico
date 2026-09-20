(function () {
  var payloadEl = document.getElementById("payload");
  var arbolEl = document.getElementById("arbol-data");
  var cfg = document.getElementById("dash-config");
  if (!payloadEl || !arbolEl || !cfg || typeof echarts === "undefined") return;

  var VERDE = "#006241", VERDE2 = "#00754a", DORADO = "#cba258", ROJO = "#d6311f";
  var GRIS = "#6b7280", TEXTO = "#1e3932", CLARO = "#faf6ee";
  var RAMAS = {
    1: ["#12312b", "#1e3932", "#2f5b50", "#4a7c6a", "#6d9b89", "#95bbab"],
    2: ["#7a5d26", "#a8843c", "#cba258", "#dcbb7c", "#e9d2a2", "#f4e6c8"],
    3: ["#1d4b48", "#2b6562", "#3f7d7a", "#5c9a96", "#86b5b2", "#b1d0ce"],
  };
  var RAMA_DEF = { 1: 0, 2: 1, 3: 2 };
  var paleta = function (padreId, idx) {
    var rama = RAMAS[padreId] || RAMAS[1];
    return rama[Math.min(idx, rama.length - 1)];
  };
  var lum = function (h) {
    var c = [1, 3, 5].map(function (i) { return parseInt(h.slice(i, i + 2), 16) / 255; });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  var texto = function (h) { return lum(h) > 0.58 ? "#12312b" : "#ffffff"; };
  var num = function (v) { return Number(v).toLocaleString("es"); };

  var P = JSON.parse(payloadEl.textContent);
  var ARBOL = JSON.parse(arbolEl.textContent);
  var scope = { padre: null, grupo: null, area: null };
  var nivel = 0;
  var charts = {};

  function vacio(id, msg) {
    var el = document.getElementById(id);
    if (!el) return;
    if (charts[id]) { charts[id].dispose(); delete charts[id]; }
    el.innerHTML = '<p class="sin-datos">' + (msg || "Sin datos para este filtro") + "</p>";
  }

  function montar(id, option) {
    var el = document.getElementById(id);
    if (!el) return;
    if (el.firstChild && el.firstChild.className === "sin-datos") el.innerHTML = "";
    var ch = charts[id] || echarts.init(el);
    charts[id] = ch;
    ch.clear();
    ch.setOption(option);
  }

  function base() {
    return {
      grid: { left: 0, right: 60, top: 20, bottom: 10, containLabel: true },
      tooltip: { trigger: "axis" },
      textStyle: { color: TEXTO, fontSize: 12 },
    };
  }

  function barrasH(labels, values, color) {
    var o = base();
    o.grid.right = 66;
    o.xAxis = { type: "value", axisLabel: { color: GRIS, fontSize: 10 } };
    o.yAxis = { type: "category", data: labels.slice().reverse(),
                axisLabel: { color: TEXTO, fontSize: 11, width: 170, overflow: "truncate" } };
    o.series = [{ type: "bar", data: values.slice().reverse(),
                  itemStyle: { color: color, borderRadius: [0, 3, 3, 0] },
                  label: { show: true, position: "right", color: TEXTO, fontSize: 11 } }];
    return o;
  }

  /* ---------------- drill-down ---------------- */
  function conteos() {
    var a = P.charts.arbol_conteos || { padres: [], grupos: [], areas: [] };
    var map = { 0: {}, 1: {}, 2: {} };
    (a.padres || []).forEach(function (p) { map[0][p.id] = { n: p.nombre, v: p.total, color: paleta(p.id, 1) }; });
    (a.grupos || []).forEach(function (g) { map[1][g.id] = { n: g.nombre, v: g.total, padre: g.padre_id, color: paleta(g.padre_id, 2) }; });
    (a.areas || []).forEach(function (x) { map[2][x.id] = { n: x.nombre, v: x.total, padre: x.padre_id, grupo: x.grupo_id, color: paleta(x.padre_id, 4) }; });
    return { map: map, raw: a };
  }

  function pintarDrill() {
    var c = conteos();
    var filas = [];
    var color = VERDE;
    if (nivel === 0) {
      filas = (c.raw.padres || []).map(function (p) { return { id: p.id, n: p.nombre, v: p.total, color: paleta(p.id, 1) }; });
      document.getElementById("drill-nivel").textContent = "Nivel: Grupo Padre — clic para entrar";
    } else if (nivel === 1) {
      var pid = parseInt(scope.padre, 10);
      filas = (c.raw.grupos || []).filter(function (g) { return g.padre_id === pid; })
        .map(function (g) { return { id: g.id, n: g.nombre, v: g.total, color: paleta(pid, 2) }; })
        .concat((c.raw.areas || []).filter(function (x) { return x.padre_id === pid && !x.grupo_id; })
          .map(function (x) { return { id: "a" + x.id, n: x.nombre, v: x.total, color: paleta(pid, 4) }; }));
      document.getElementById("drill-nivel").textContent = "Nivel: " + scope.padreNombre + " — clic en un grupo";
    } else {
      var gid = parseInt(scope.grupo, 10);
      filas = (c.raw.areas || []).filter(function (x) { return x.grupo_id === gid; })
        .map(function (x) { return { id: "a" + x.id, n: x.nombre, v: x.total, color: paleta(parseInt(scope.padre, 10), 4) }; });
      document.getElementById("drill-nivel").textContent = "Nivel: " + scope.padreNombre + " › " + scope.grupoNombre;
    }
    filas.sort(function (a, b) { return b.v - a.v; });
    if (!filas.length) return vacio("chart-drill", "Sin divisiones para este filtro");
    var o = base();
    o.grid.right = 70;
    o.tooltip = { trigger: "axis", axisPointer: { type: "shadow" },
                  formatter: function (p) { return p[0].name + ": <b>" + p[0].value.toLocaleString("es") + "</b> casos"; } };
    o.xAxis = { type: "value", axisLabel: { color: GRIS, fontSize: 10 } };
    o.yAxis = { type: "category", data: filas.map(function (f) { return f.n; }).reverse(),
                axisLabel: { color: TEXTO, fontSize: 12, width: 190, overflow: "truncate" } };
    o.series = [{
      type: "bar", data: filas.map(function (f) { return f.v; }).reverse(),
      itemStyle: { color: function (p) { return filas[filas.length - 1 - p.dataIndex].color; }, borderRadius: [0, 3, 3, 0] },
      label: { show: true, position: "right", color: TEXTO, fontSize: 11, fontWeight: "bold",
               formatter: function (p) { return p.value.toLocaleString("es"); } },
    }];
    montar("chart-drill", o);
    charts["chart-drill"].off("click");
    charts["chart-drill"].on("click", function (p) {
      var f = filas[filas.length - 1 - p.dataIndex];
      if (nivel === 0) { scope.padre = String(f.id); scope.padreNombre = f.n; nivel = 1; scope.grupo = null; scope.area = null; }
      else if (nivel === 1) {
        if (String(f.id).charAt(0) === "a") { scope.area = String(f.id).slice(1); scope.areaNombre = f.n; }
        else { scope.grupo = String(f.id); scope.grupoNombre = f.n; nivel = 2; scope.area = null; }
      } else { scope.area = String(f.id).slice(1); scope.areaNombre = f.n; }
      recargar();
    });
  }

  /* ---------------- ficha ---------------- */
  function pintarFicha(f) {
    var ruta = [scope.padreNombre, scope.grupoNombre, scope.areaNombre].filter(Boolean).join(" › ");
    document.getElementById("ficha-ruta").textContent = ruta || "Todo el período";
    var padre = f.nombre_padre;
    var filas = [["Atenciones", num(f.casos)]];
    if (padre && f.pct_padre !== null) filas.push(["Del total de " + padre, num(f.pct_padre) + "%"]);
    filas.push(["Fuera de turno", num(f.fuera) + " (" + num(f.fuera_pct) + "%)"]);
    if (padre && f.delta_padre !== null) {
      filas.push(["Fuera de turno vs " + padre, (f.delta_padre > 0 ? "+" : "−") + num(Math.abs(f.delta_padre)) + " puntos"]);
    }
    filas.push(["Media por mes", num(f.promedio_mes) + " en " + f.meses_activos + " meses"]);
    filas.push(["Mes más cargado", (f.pico || "—") + " · " + num(f.pico_total) + " casos"]);
    filas.push(["Mes más tranquilo", (f.valle || "—") + " · " + num(f.valle_total) + " casos"]);
    filas.push(["Categoría más frecuente", (f.dominante || "—") + " (" + num(f.dominante_pct) + "%)"]);
    filas.push(["3 categorías más frecuentes", num(f.top3_pct) + "% de las atenciones"]);
    document.getElementById("ficha").innerHTML = filas.map(function (par) {
      return '<div class="ficha-fila"><span>' + par[0] + '</span><b>' + par[1] + "</b></div>";
    }).join("");
  }

  /* ---------------- calendario ---------------- */
  function pintarCalendario(c) {
    if (!c.inicio) return vacio("chart-calendario");
    montar("chart-calendario", {
      tooltip: { formatter: function (p) { return p.value[0] + ": <b>" + p.value[1] + "</b> casos"; } },
      visualMap: { min: 0, max: c.max || 1, orient: "horizontal", left: "center", bottom: 0,
                   inRange: { color: [CLARO, "#cba258", VERDE] }, textStyle: { color: GRIS, fontSize: 10 } },
      calendar: {
        range: [c.inicio, c.fin], left: 40, right: 20, top: 30, bottom: 44,
        cellSize: ["auto", 15],
        itemStyle: { color: CLARO, borderColor: "#ffffff", borderWidth: 2 },
        dayLabel: { color: GRIS, fontSize: 10, firstDay: 1 },
        monthLabel: { color: TEXTO, fontSize: 10 },
        yearLabel: { color: TEXTO, fontSize: 11 },
        splitLine: { lineStyle: { color: "#e7e7e7" } },
      },
      series: [{ type: "heatmap", coordinateSystem: "calendar", data: c.datos }],
    });
  }

  /* ---------------- sankey ---------------- */
  function pintarSankey(s) {
    if (!s.links || !s.links.length) return vacio("chart-sankey");
    var medios = {}, cats = {}, pads = {};
    s.links.forEach(function (l) { medios[l.source] = 1; cats[l.target] = 1; });
    montar("chart-sankey", {
      tooltip: { trigger: "item", triggerOn: "mousemove",
                 formatter: function (p) {
                   if (p.dataType === "edge") return p.data.source + " → " + p.data.target + ": <b>" + p.data.value + "</b>";
                   return p.name;
                 } },
      series: [{
        type: "sankey", left: 10, right: 130, top: 16, bottom: 16,
        nodeWidth: 14, nodeGap: 8, nodeAlign: "justify",
        emphasis: { focus: "adjacency" },
        lineStyle: { color: "gradient", opacity: 0.42, curveness: 0.5 },
        label: { color: TEXTO, fontSize: 11 },
        data: s.nodos.map(function (n, i) {
          return { name: n.name, itemStyle: { color: i % 3 === 0 ? VERDE : (i % 3 === 1 ? DORADO : "#3f7d7a") } };
        }),
        links: s.links,
      }],
    });
  }

  /* ---------------- scatter ---------------- */
  function pintarScatter(sc) {
    if (!sc.datos || !sc.datos.length) return vacio("chart-scatter");
    var maxX = Math.max.apply(null, sc.datos.map(function (d) { return d[0]; })) || 1;
    var maxY = Math.max.apply(null, sc.datos.map(function (d) { return d[1]; })) || 1;
    montar("chart-scatter", {
      grid: { left: 0, right: 30, top: 24, bottom: 10, containLabel: true },
      tooltip: { formatter: function (p) {
        return "<b>" + p.data[2] + "</b><br/>" + p.data[0] + " casos · " + p.data[1] + " fuera de turno (" + p.data[3] + "%)";
      } },
      xAxis: { type: "value", name: "casos", nameTextStyle: { color: GRIS, fontSize: 10 },
               axisLabel: { color: GRIS, fontSize: 10 } },
      yAxis: { type: "value", name: "fuera de turno", nameTextStyle: { color: GRIS, fontSize: 10 },
               axisLabel: { color: GRIS, fontSize: 10 } },
      series: [{
        type: "scatter", data: sc.datos, symbolSize: 16,
        itemStyle: { color: VERDE2, borderColor: "#ffffff", borderWidth: 2 },
        label: { show: true, position: "top", fontSize: 10, color: TEXTO,
                 formatter: function (p) { return p.data[2].split(" ")[0]; } },
        markLine: {
          silent: true, symbol: "none",
          lineStyle: { color: DORADO, type: "dashed" },
          data: [{ xAxis: maxX * 0.5 }, { yAxis: maxY * 0.5 }],
        },
      }],
    });
  }

  /* ---------------- radar ---------------- */
  function pintarRadar(r, seleccion) {
    if (!r.tecnicos || !r.tecnicos.length) return vacio("chart-radar");
    var sel = r.tecnicos.filter(function (t) { return String(t.id) === String(seleccion); })[0] || r.tecnicos[0];
    var max = Math.max.apply(null, [1].concat(r.tecnicos.map(function (t) { return Math.max.apply(null, t.valores); })));
    montar("chart-radar", {
      tooltip: {},
      radar: {
        indicator: r.ejes.map(function (e) { return { name: e, max: max }; }),
        center: ["50%", "54%"], radius: "68%",
        axisName: { color: TEXTO, fontSize: 10 },
        splitLine: { lineStyle: { color: "#e7e7e7" } },
        splitArea: { areaStyle: { color: ["#ffffff", CLARO] } },
      },
      series: [{
        type: "radar", symbolSize: 5,
        data: [{ value: sel.valores, name: sel.nombre,
                 lineStyle: { color: VERDE, width: 2 },
                 itemStyle: { color: VERDE },
                 areaStyle: { color: "rgba(0,98,65,0.22)" } }],
      }],
    });
  }

  /* ---------------- resto ---------------- */
  function pintarResto(c) {
    c.categoria.labels.length
      ? montar("chart-categoria", barrasH(c.categoria.labels, c.categoria.values, VERDE))
      : vacio("chart-categoria");
    c.rendimiento.labels.length
      ? montar("chart-rendimiento", barrasH(c.rendimiento.labels, c.rendimiento.values, VERDE2))
      : vacio("chart-rendimiento");
    c.colaboraciones.labels.length
      ? montar("chart-colaboraciones", barrasH(c.colaboraciones.labels, c.colaboraciones.values, DORADO))
      : vacio("chart-colaboraciones");

    if (c.evolucion.labels.length) {
      var oe = base();
      oe.xAxis = { type: "category", data: c.evolucion.labels, boundaryGap: false, axisLabel: { color: GRIS, fontSize: 10 } };
      oe.yAxis = { type: "value", axisLabel: { color: GRIS, fontSize: 10 } };
      oe.series = [{ type: "line", data: c.evolucion.values, smooth: true, symbolSize: 7,
                     lineStyle: { color: VERDE, width: 3 }, itemStyle: { color: VERDE },
                     areaStyle: { color: "rgba(0,98,65,0.12)" } }];
      montar("chart-evolucion", oe);
    } else {
      vacio("chart-evolucion");
    }

    if (c.pareto.labels.length) {
      var op = base();
      op.tooltip = { trigger: "axis", axisPointer: { type: "shadow" } };
      op.xAxis = { type: "category", data: c.pareto.labels, axisLabel: { rotate: 30, color: TEXTO, fontSize: 10 } };
      op.yAxis = [{ type: "value", name: "casos" },
                  { type: "value", name: "% acum.", max: 100, axisLabel: { formatter: "{value}%" } }];
      op.series = [
        { type: "bar", name: "casos", data: c.pareto.values, itemStyle: { color: VERDE, borderRadius: [3, 3, 0, 0] } },
        { type: "line", name: "% acumulado", yAxisIndex: 1, data: c.pareto.acumulado, smooth: true,
          lineStyle: { color: DORADO, width: 3 }, itemStyle: { color: DORADO } },
      ];
      montar("chart-pareto", op);
    } else {
      vacio("chart-pareto");
    }

    if (c.categoria_mes.celdas.length) {
      var oh = base();
      oh.grid.right = 66; oh.grid.bottom = 26;
      oh.tooltip = { position: "top" };
      oh.xAxis = { type: "category", data: c.categoria_mes.meses, splitArea: { show: true }, axisLabel: { color: GRIS, fontSize: 10 } };
      oh.yAxis = { type: "category", data: c.categoria_mes.categorias, splitArea: { show: true },
                   axisLabel: { color: TEXTO, fontSize: 10 } };
      oh.visualMap = { min: 0, max: c.categoria_mes.max || 1, calculable: true, orient: "vertical",
                       right: 4, top: "middle", itemHeight: 110,
                       inRange: { color: [CLARO, DORADO, VERDE] }, textStyle: { color: GRIS, fontSize: 10 } };
      oh.series = [{ type: "heatmap", data: c.categoria_mes.celdas,
                     label: { show: true, fontSize: 10, color: TEXTO } }];
      montar("chart-categoria-mes", oh);
    } else {
      vacio("chart-categoria-mes");
    }
  }

  function pintarTopAreas(c) {
    var filas = c.top_areas || [];
    document.getElementById("top-areas").innerHTML = filas.length
      ? filas.map(function (a, i) {
          return '<div class="ficha-fila"><span>' + (i + 1) + ". " + a.area + "</span><b>" + num(a.total) + "</b></div>";
        }).join("")
      : '<p class="sin-datos">Sin datos para este filtro</p>';
  }

  /* ---------------- chips + carga ---------------- */
  function pintarChips() {
    var activos = [["padre", scope.padreNombre], ["grupo", scope.grupoNombre], ["area", scope.areaNombre]].filter(function (p) { return p[1]; });
    var cont = document.getElementById("chips");
    if (!activos.length) {
      cont.innerHTML = '<span class="chip vacio">Sin filtro: se muestra todo el período</span>';
      return;
    }
    cont.innerHTML = activos.map(function (p) {
      return '<span class="chip">' + p[1] + '<button data-quitar="' + p[0] + '">×</button></span>';
    }).join("") + '<button class="clear" id="limpiar">Limpiar todo</button>';
    cont.querySelectorAll("[data-quitar]").forEach(function (b) {
      b.onclick = function () {
        var k = b.dataset.quitar;
        if (k === "padre") { scope = { padre: null, grupo: null, area: null }; nivel = 0; }
        else if (k === "grupo") { scope.grupo = null; scope.grupoNombre = null; scope.area = null; scope.areaNombre = null; nivel = 1; }
        else { scope.area = null; scope.areaNombre = null; }
        recargar();
      };
    });
    document.getElementById("limpiar").onclick = function () {
      scope = { padre: null, grupo: null, area: null }; nivel = 0; recargar();
    };
  }

  function pintarSelectorRadar(r) {
    var sel = document.getElementById("radar-tec");
    if (!sel) return;
    if (!r.tecnicos || !r.tecnicos.length) { sel.innerHTML = ""; return; }
    if (sel.options.length !== r.tecnicos.length) {
      sel.innerHTML = "";
      sel.innerHTML = r.tecnicos.map(function (t) {
        return '<option value="' + t.id + '">' + t.nombre + "</option>";
      }).join("");
      sel.onchange = function () { pintarRadar(P.charts.radar, sel.value); };
    }
  }

  function recargar() {
    var q = [];
    if (scope.padre) q.push("grupo_padre_id=" + scope.padre);
    if (scope.grupo) q.push("grupo_id=" + scope.grupo);
    if (scope.area) q.push("area_id=" + scope.area);
    if (cfg.dataset.desde) q.push("desde=" + cfg.dataset.desde);
    if (cfg.dataset.hasta) q.push("hasta=" + cfg.dataset.hasta);
    fetch(cfg.dataset.statsUrl + (q.length ? "?" + q.join("&") : ""))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        P = d;
        render();
      })
      .catch(function () {});
  }

  function render() {
    pintarChips();
    pintarDrill();
    pintarFicha(P.ficha);
    pintarCalendario(P.charts.calendario);
    pintarSankey(P.charts.sankey);
    pintarScatter(P.charts.scatter);
    pintarSelectorRadar(P.charts.radar);
    pintarRadar(P.charts.radar, document.getElementById("radar-tec").value);
    pintarResto(P.charts);
    pintarTopAreas(P.charts);
  }

  render();

  var ancho = window.innerWidth;
  window.addEventListener("resize", function () {
    if (window.innerWidth === ancho) return;
    ancho = window.innerWidth;
    Object.keys(charts).forEach(function (k) { charts[k].resize(); });
  });

  var bloque = document.querySelector("[data-estados-url]");
  var conteo = document.getElementById("presencia-conteo");
  var lista = document.getElementById("presencia-lista");
  function refrescarEstados() {
    fetch(bloque.dataset.estadosUrl)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        Object.keys(d.conteo).forEach(function (k) {
          var b = conteo.querySelector('[data-estado="' + k + '"] b');
          if (b) b.textContent = d.conteo[k];
        });
        lista.innerHTML = d.tecnicos.map(function (t) {
          return '<div class="t-card"><div><strong>' + t.nombre + "</strong><small>" + t.rol +
                 '</small></div><span class="estado estado-' + t.estado + '">' + t.estado + "</span></div>";
        }).join("");
      })
      .catch(function () {});
  }
  setInterval(refrescarEstados, 20000);
})();
