(function () {
  var data = document.getElementById("charts-data");
  if (!data || typeof echarts === "undefined") return;
  var C = JSON.parse(data.textContent);
  var VERDE = "#006241";
  var DORADO = "#cba258";
  var ROJO = "#d6311f";
  var GRIS = "#6b7280";
  var TEXTO = "#1e3932";
  var charts = [];

  function base() {
    return {
      grid: { left: 10, right: 20, top: 20, bottom: 10, containLabel: true },
      tooltip: { trigger: "axis" },
      textStyle: { color: TEXTO, fontSize: 12 },
    };
  }

  function montar(id, option) {
    var el = document.getElementById(id);
    if (!el) return;
    var ch = echarts.init(el);
    ch.setOption(option);
    charts.push(ch);
  }

  function barrasH(labels, values, color) {
    var o = base();
    o.grid.left = 0;
    o.grid.right = 46;
    o.xAxis = { type: "value", axisLabel: { color: GRIS, fontSize: 10 } };
    o.yAxis = {
      type: "category",
      data: labels.slice().reverse(),
      axisLabel: { color: TEXTO, fontSize: 11, width: 150, overflow: "truncate" },
    };
    o.series = [
      {
        type: "bar",
        data: values.slice().reverse(),
        itemStyle: { color: color, borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: "right", color: TEXTO },
      },
    ];
    return o;
  }

  if (C.categoria.labels.length) {
    montar("chart-categoria", barrasH(C.categoria.labels, C.categoria.values, VERDE));
  }

  if (C.rendimiento.labels.length) {
    montar("chart-rendimiento", barrasH(C.rendimiento.labels, C.rendimiento.values, VERDE));
  }

  if (C.colaboraciones.labels.length) {
    montar(
      "chart-colaboraciones",
      barrasH(C.colaboraciones.labels, C.colaboraciones.values, DORADO)
    );
  }

  if (C.evolucion.labels.length) {
    var oe = base();
    oe.xAxis = { type: "category", data: C.evolucion.labels, boundaryGap: false };
    oe.yAxis = { type: "value" };
    oe.series = [
      {
        type: "line",
        data: C.evolucion.values,
        smooth: true,
        symbolSize: 7,
        lineStyle: { color: VERDE, width: 3 },
        itemStyle: { color: VERDE },
        areaStyle: { color: "rgba(0,98,65,0.12)" },
      },
    ];
    montar("chart-evolucion", oe);
  }

  if (C.pareto.labels.length) {
    var op = base();
    op.tooltip = { trigger: "axis", axisPointer: { type: "shadow" } };
    op.xAxis = {
      type: "category",
      data: C.pareto.labels,
      axisLabel: { rotate: 30, color: TEXTO, fontSize: 10 },
    };
    op.yAxis = [
      { type: "value", name: "casos" },
      { type: "value", name: "% acum.", max: 100, axisLabel: { formatter: "{value}%" } },
    ];
    op.series = [
      {
        type: "bar",
        name: "casos",
        data: C.pareto.values,
        itemStyle: { color: VERDE, borderRadius: [3, 3, 0, 0] },
      },
      {
        type: "line",
        name: "% acumulado",
        yAxisIndex: 1,
        data: C.pareto.acumulado,
        smooth: true,
        lineStyle: { color: DORADO, width: 3 },
        itemStyle: { color: DORADO },
      },
    ];
    montar("chart-pareto", op);
  }

  if (C.categoria_mes.celdas.length) {
    var oh = base();
    oh.grid.left = 0;
    oh.grid.right = 66;
    oh.grid.bottom = 26;
    oh.tooltip = { position: "top" };
    oh.xAxis = {
      type: "category",
      data: C.categoria_mes.meses,
      splitArea: { show: true },
    };
    oh.yAxis = {
      type: "category",
      data: C.categoria_mes.categorias,
      splitArea: { show: true },
      axisLabel: { color: TEXTO, fontSize: 10 },
    };
    oh.visualMap = {
      min: 0,
      max: C.categoria_mes.max || 1,
      calculable: true,
      orient: "vertical",
      right: 4,
      top: "middle",
      itemHeight: 110,
      inRange: { color: ["#faf6ee", "#cba258", "#006241"] },
      textStyle: { color: GRIS, fontSize: 10 },
    };
    oh.series = [
      {
        type: "heatmap",
        data: C.categoria_mes.celdas,
        label: { show: true, fontSize: 10, color: TEXTO },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: "rgba(0,0,0,0.3)" } },
      },
    ];
    montar("chart-categoria-mes", oh);
  }

  var anchoViejo = window.innerWidth;
  window.addEventListener("resize", function () {
    if (window.innerWidth === anchoViejo) return;
    anchoViejo = window.innerWidth;
    charts.forEach(function (c) {
      c.resize();
    });
  });

  var bloque = document.querySelector("[data-estados-url]");
  if (!bloque) return;
  var conteo = document.getElementById("presencia-conteo");
  var lista = document.getElementById("presencia-lista");

  function pintar(payload) {
    Object.keys(payload.conteo).forEach(function (k) {
      var chip = conteo.querySelector('[data-estado="' + k + '"] b');
      if (chip) chip.textContent = payload.conteo[k];
    });
    lista.innerHTML = payload.tecnicos
      .map(function (t) {
        return (
          '<div class="t-card"><div><strong>' +
          t.nombre +
          "</strong><small>" +
          t.rol +
          '</small></div><span class="estado estado-' +
          t.estado +
          '">' +
          t.estado +
          "</span></div>"
        );
      })
      .join("");
  }

  function refrescar() {
    fetch(bloque.dataset.estadosUrl, { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (d) {
        if (d) pintar(d);
      })
      .catch(function () {});
  }
  setInterval(refrescar, 20000);
})();
