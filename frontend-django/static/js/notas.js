(function () {
  var form = document.getElementById("form-notas");
  var area = document.getElementById("notas-texto");
  var estado = document.getElementById("notas-estado");
  if (!form || !area || !estado) return;

  var espera = null;
  var enviando = false;
  var pendiente = false;

  function pintar(texto, clase) {
    estado.textContent = texto;
    estado.className = "notas-estado" + (clase ? " " + clase : "");
  }

  function guardar() {
    if (enviando) {
      pendiente = true;
      return;
    }
    enviando = true;
    pintar("Guardando…", "");
    var token = form.querySelector('input[name="csrfmiddlewaretoken"]');
    var datos = new FormData();
    datos.append("contenido", area.value);
    fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": token ? token.value : "" },
      body: datos,
    })
      .then(function (r) {
        return r.json().then(function (d) {
          return { ok: r.ok && d.ok, error: d.error };
        });
      })
      .then(function (d) {
        if (d.ok) {
          pintar("Guardado ✓", "ok");
        } else {
          pintar(d.error || "No se pudo guardar", "error");
        }
      })
      .catch(function () {
        pintar("Sin conexión", "error");
      })
      .finally(function () {
        enviando = false;
        if (pendiente) {
          pendiente = false;
          guardar();
        }
      });
  }

  area.addEventListener("input", function () {
    pintar("Sin guardar…", "");
    if (espera) clearTimeout(espera);
    espera = setTimeout(guardar, 1200);
  });

  area.addEventListener("blur", function () {
    if (espera) clearTimeout(espera);
    guardar();
  });

  window.addEventListener("beforeunload", function () {
    if (espera) {
      clearTimeout(espera);
      guardar();
    }
  });

  pintar(area.value.trim() ? "Guardado ✓" : "Vacío", area.value.trim() ? "ok" : "");
})();
