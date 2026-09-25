(function () {
  var payloadEl = document.getElementById("payload");
  if (!payloadEl || typeof echarts === "undefined") return;
  var P = JSON.parse(payloadEl.textContent || "null");
  if (!P) return;

  var VERDE = "#006241", VERDE2 = "#00754a", DORADO = "#cba258";
  var GRIS = "#6b7280", TEXTO = "#1e3932";
  var SIN = "Sin atenciones registradas en este período";
  var charts = {};
  var num = function (v) { return Number(v).toLocaleString("es"); };

  function vacio(id, msg) {
    var el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '<p class="sin-datos">' + (msg || SIN) + "</p>";
  }

  function montar(id, option) {
    var el = document.getElementById(id);
    if (!el) return;
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

  function anchoLabel(id) {
    var el = document.getElementById(id);
    var w = el ? el.clientWidth : 480;
    return Math.max(88, Math.min(200, Math.round(w * 0.38)));
  }

  function barrasH(labels, values, color, id) {
    var o = base();
    o.grid.right = 66;
    o.xAxis = {
      type: "value",
      axisLabel: { color: GRIS, fontSize: 10, hideOverlap: true },
    };
    o.yAxis = {
      type: "category",
      data: labels.slice().reverse(),
      axisLabel: { color: TEXTO, fontSize: 11, width: anchoLabel(id), overflow: "break" },
    };
    o.series = [{
      type: "bar",
      data: values.slice().reverse(),
      itemStyle: { color: color, borderRadius: [0, 3, 3, 0] },
      label: { show: true, position: "right", color: TEXTO, fontSize: 11 },
    }];
    return o;
  }

  function pintarBarras(id, d, color) {
    if (!d.labels.length) return vacio(id);
    montar(id, barrasH(d.labels, d.values, color, id));
  }

  function pintarEvolucion(d) {
    var o = base();
    o.grid.left = 18;
    o.xAxis = {
      type: "category",
      data: d.labels,
      boundaryGap: false,
      axisLabel: { color: GRIS, fontSize: 10 },
    };
    o.yAxis = {
      type: "value",
      axisLabel: { show: false },
      splitLine: { lineStyle: { color: "#e7ece9" } },
    };
    o.series = [{
      type: "line",
      data: d.values,
      smooth: true,
      symbolSize: 7,
      lineStyle: { color: VERDE, width: 3 },
      itemStyle: { color: VERDE },
      areaStyle: { color: "rgba(0,98,65,0.12)" },
      label: { show: true, position: "top", color: TEXTO, fontSize: 10 },
    }];
    montar("rep-evolucion", o);
  }

  function pintarDonut(id, d) {
    var colores = [VERDE, VERDE2, DORADO, "#3f7d7a", "#6d9b89", "#b1d0ce"];
    var total = d.values.reduce(function (a, b) { return a + b; }, 0) || 1;
    montar(id, {
      tooltip: {
        trigger: "item",
        formatter: function (p) {
          return p.name + ": <b>" + num(p.value) + "</b> (" + num(p.percent) + "%)";
        },
      },
      legend: {
        bottom: 0,
        icon: "circle",
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: TEXTO, fontSize: 11 },
        formatter: function (nombre) {
          var i = d.labels.indexOf(nombre);
          if (i < 0) return nombre;
          return nombre + " " + num(d.values[i]) + " (" + Math.round((d.values[i] * 100) / total) + "%)";
        },
      },
      series: [{
        type: "pie",
        radius: ["46%", "68%"],
        center: ["50%", "42%"],
        avoidLabelOverlap: true,
        labelLayout: { hideOverlap: true },
        itemStyle: { borderColor: "#ffffff", borderWidth: 2 },
        label: { show: false },
        data: d.labels.map(function (l, i) {
          return {
            name: l,
            value: d.values[i],
            itemStyle: { color: colores[i % colores.length] },
          };
        }),
      }],
    });
  }

  function pintarDona(id, d, vacioMsg) {
    if (!d.labels.length) return vacio(id, vacioMsg);
    pintarDonut(id, d);
  }

  function resizeTodo() {
    Object.keys(charts).forEach(function (k) { charts[k].resize(); });
  }

  function render() {
    var c = P.charts;
    pintarEvolucion(c.evolucion);
    pintarBarras("rep-categoria", c.categoria, VERDE);
    pintarBarras("rep-sectores", c.sectores, VERDE2);
    pintarDona("rep-medio", c.medio);
    pintarDona("rep-tipo", c.tipo_solicitante);
  }

  render();

  var ancho = window.innerWidth;
  window.addEventListener("resize", function () {
    if (window.innerWidth === ancho) return;
    ancho = window.innerWidth;
    resizeTodo();
  });
  window.addEventListener("beforeprint", resizeTodo);
  window.addEventListener("afterprint", resizeTodo);
  if (window.matchMedia) {
    var mq = window.matchMedia("print");
    var alCambiar = function () { resizeTodo(); };
    if (mq.addEventListener) mq.addEventListener("change", alCambiar);
    else if (mq.addListener) mq.addListener(alCambiar);
  }
})();
