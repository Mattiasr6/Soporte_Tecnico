(function () {
  var raiz = document.getElementById("inicio");
  if (!raiz) return;

  var NOMBRES = {
    disponible: "Disponible",
    ocupado: "Ocupado",
    extraturno: "Fuera de turno",
    ausente: "Ausente",
  };

  function csrf() {
    var campo = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return campo ? campo.value : "";
  }

  function enviar(url, campos) {
    var datos = new FormData();
    Object.keys(campos).forEach(function (k) { datos.append(k, campos[k]); });
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf() },
      body: datos,
    }).then(function (r) {
      return r.json().then(function (d) {
        return { ok: r.ok && d.ok, error: d.error, datos: d };
      });
    });
  }

  var chip = document.getElementById("mi-estado-chip");
  var boton = document.getElementById("btn-estado");

  function pintarMiEstado(estado) {
    if (chip) {
      chip.className = "estado estado-" + estado;
      chip.textContent = NOMBRES[estado] || estado;
    }
    if (!boton) return;
    boton.dataset.estado = estado;
    if (estado === "ocupado") boton.textContent = "Ponerme disponible";
    else if (estado === "disponible") boton.textContent = "Ponerme ocupado";
    else boton.textContent = "Marcarme disponible";
  }

  if (boton && raiz.dataset.puedeEstado === "1") {
    boton.addEventListener("click", function () {
      var nuevo = boton.dataset.estado === "disponible" ? "ocupado" : "disponible";
      boton.disabled = true;
      enviar(raiz.dataset.urlEstado, { estado: nuevo })
        .then(function (d) {
          if (d.ok) {
            pintarMiEstado(d.datos.estado);
            refrescarEquipo();
          } else {
            avisar(d.error);
          }
        })
        .catch(function () { avisar("Sin conexión."); })
        .finally(function () { boton.disabled = false; });
    });
  }

  var conteo = document.getElementById("presencia-conteo");
  var lista = document.getElementById("presencia-lista");

  function tarjeta(t) {
    var detalle = t.rol;
    if (t.horario_hoy) detalle += " · " + t.horario_hoy;
    detalle += " · " + t.atenciones_hoy + " hoy";
    if (t.entra_a_las) detalle += " · entra " + t.entra_a_las;
    return '<div class="t-card"><div><strong>' + t.nombre + "</strong><small>" + detalle +
      '</small></div><span class="estado estado-' + t.estado + '">' +
      (NOMBRES[t.estado] || t.estado) + "</span></div>";
  }

  function refrescarEquipo() {
    fetch(raiz.dataset.urlEstados)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !conteo || !lista) return;
        Object.keys(d.conteo).forEach(function (k) {
          var b = conteo.querySelector('[data-estado="' + k + '"] b');
          if (b) b.textContent = d.conteo[k];
        });
        lista.innerHTML = d.tecnicos.map(tarjeta).join("");
      })
      .catch(function () {});
  }

  var formAnuncio = document.getElementById("anuncio-form");
  var area = document.getElementById("anuncio-mensaje");
  var borrar = document.getElementById("anuncio-borrar");
  var aviso = document.getElementById("anuncio-aviso");
  var cuerpo = document.getElementById("anuncio-cuerpo");
  var firma = document.getElementById("anuncio-firma");

  function avisar(texto) {
    if (!aviso) return;
    aviso.textContent = texto || "";
    aviso.className = "sub" + (texto ? " error" : "");
    aviso.hidden = !texto;
  }

  function pintarAnuncio(a) {
    if (firma) firma.textContent = a.author ? a.author + " · " + a.at : "";
    if (area) {
      if (document.activeElement !== area) area.value = a.message || "";
      if (borrar) borrar.hidden = !a.message;
      return;
    }
    if (!cuerpo) return;
    cuerpo.innerHTML = a.message
      ? '<div class="anuncio"><p>' + a.message + "</p><small>" +
        (a.author ? a.author + " · " + a.at : "") + "</small></div>"
      : '<p class="sub">No hay anuncios por ahora.</p>';
  }

  function publicar(mensaje) {
    avisar("");
    enviar(raiz.dataset.urlAnuncioGuardar, { mensaje: mensaje })
      .then(function (d) {
        if (d.ok) {
          pintarAnuncio(d.datos.anuncio || {});
          avisar("Publicado ✓");
        } else {
          avisar(d.error);
        }
      })
      .catch(function () { avisar("Sin conexión."); });
  }

  if (formAnuncio) {
    formAnuncio.addEventListener("submit", function (e) {
      e.preventDefault();
      publicar(area.value.trim());
    });
    if (borrar) {
      borrar.addEventListener("click", function () { publicar(""); });
    }
  }

  function refrescarAnuncio() {
    fetch(raiz.dataset.urlAnuncio)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) pintarAnuncio(d); })
      .catch(function () {});
  }

  setInterval(function () {
    refrescarEquipo();
    refrescarAnuncio();
  }, 20000);
})();
