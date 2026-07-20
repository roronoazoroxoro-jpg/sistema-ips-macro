const METODOS_EFECTIVO = ["tas_macro", "ventanilla_macro"];

const METODOS_TRANSFERENCIA = ["transferencia_macro", "home_banking"];



const form = document.getElementById("form-deposito");

const resultado = document.getElementById("resultado");

const montoTotal = document.getElementById("monto_total");

const montoEfectivo = document.getElementById("monto_efectivo");

const montoTransferencia = document.getElementById("monto_transferencia");

const metodoDeposito = document.getElementById("metodo_deposito");

const toggleDesglose = document.getElementById("toggle_desglose");

const bloqueDesglose = document.getElementById("bloque_desglose");

const selectorMetodo = document.getElementById("selector-metodo");

const previewEfectivo = document.getElementById("preview-efectivo");

const previewTransferencia = document.getElementById("preview-transferencia");

const panelAsignacion = document.getElementById("panel-asignacion");



function obtenerFarmaciaId() {
  const hidden = document.getElementById("farmacia_id_valor");
  if (hidden?.value) {
    const id = parseInt(hidden.value, 10);
    if (id > 0) return id;
  }
  const select = document.getElementById("farmacia_select");
  if (select?.value) {
    const id = parseInt(select.value, 10);
    if (id > 0) return id;
  }
  const dataId = form?.dataset?.farmaciaId;
  if (dataId) {
    const id = parseInt(dataId, 10);
    if (id > 0) return id;
  }
  return 0;
}


function parseMonto(valor) {
  if (valor === "" || valor === null || valor === undefined) return 0;
  const n = parseFloat(String(valor).replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}



function formatoPesos(valor) {

  return new Intl.NumberFormat("es-AR", {

    style: "currency",

    currency: "ARS",

    minimumFractionDigits: 2,

  }).format(valor);

}



function esMetodoEfectivo(metodo) {

  return METODOS_EFECTIVO.includes(metodo);

}



function seleccionarMetodo(valor) {

  if (!metodoDeposito) return;

  metodoDeposito.value = valor;

  selectorMetodo?.querySelectorAll(".metodo-opcion").forEach((btn) => {

    const activo = btn.dataset.metodo === valor;

    btn.classList.toggle("activo", activo);

    btn.setAttribute("aria-pressed", activo ? "true" : "false");

  });

  aplicarMontosPorMetodo();

  actualizarPreviewAsignacion();

}



function actualizarPreviewAsignacion() {

  const total = parseMonto(montoTotal?.value);

  const metodo = metodoDeposito?.value || "tas_macro";

  let efectivo = 0;

  let transferencia = 0;



  if (toggleDesglose?.checked) {

    efectivo = parseMonto(montoEfectivo?.value);

    transferencia = parseMonto(montoTransferencia?.value);

  } else if (total > 0) {

    if (esMetodoEfectivo(metodo)) {

      efectivo = total;

    } else {

      transferencia = total;

    }

  }



  if (previewEfectivo) previewEfectivo.textContent = formatoPesos(efectivo);

  if (previewTransferencia) previewTransferencia.textContent = formatoPesos(transferencia);



  const filaEfectivo = panelAsignacion?.querySelector(".asignacion-efectivo");

  const filaTransferencia = panelAsignacion?.querySelector(".asignacion-transferencia");

  filaEfectivo?.classList.toggle("activo", efectivo > 0);

  filaTransferencia?.classList.toggle("activo", transferencia > 0);

}



/** Asigna efectivo/transferencia según canal cuando no hay desglose manual. */

function aplicarMontosPorMetodo() {

  const total = parseMonto(montoTotal?.value);

  if (total <= 0 || !montoEfectivo || !montoTransferencia) return;



  if (toggleDesglose?.checked) {

    return;

  }



  if (esMetodoEfectivo(metodoDeposito?.value)) {

    montoEfectivo.value = total.toFixed(2);

    montoTransferencia.value = "0.00";

  } else {

    montoEfectivo.value = "0.00";

    montoTransferencia.value = total.toFixed(2);

  }

  actualizarPreviewAsignacion();

}



function recalcularDesgloseManual() {

  if (!toggleDesglose?.checked) return;



  const total = parseMonto(montoTotal?.value);

  if (total <= 0) return;



  const efectivo = parseMonto(montoEfectivo?.value);

  const transferencia = parseMonto(montoTransferencia?.value);

  const editoEfectivo = montoEfectivo?.dataset.ultimoEdit === "efectivo";

  const editoTransferencia = montoTransferencia?.dataset.ultimoEdit === "transferencia";



  if (editoEfectivo && !editoTransferencia) {

    montoTransferencia.value = Math.max(0, total - efectivo).toFixed(2);

  } else if (editoTransferencia && !editoEfectivo) {

    montoEfectivo.value = Math.max(0, total - transferencia).toFixed(2);

  } else if (!editoEfectivo && !editoTransferencia) {

    montoEfectivo.value = total.toFixed(2);

    montoTransferencia.value = "0.00";

  }

  actualizarPreviewAsignacion();

}



function normalizarPayload(payload) {

  const total = payload.monto_total;

  let efectivo = payload.monto_efectivo;

  let transferencia = payload.monto_transferencia;



  if (Math.abs(efectivo + transferencia - total) > 0.01) {

    if (!toggleDesglose?.checked || (efectivo > 0 && transferencia > 0 && efectivo === transferencia)) {

      if (esMetodoEfectivo(payload.metodo_deposito)) {

        efectivo = total;

        transferencia = 0;

      } else {

        efectivo = 0;

        transferencia = total;

      }

    }

  }



  return { ...payload, monto_efectivo: efectivo, monto_transferencia: transferencia };

}



selectorMetodo?.addEventListener("click", (e) => {

  const btn = e.target.closest(".metodo-opcion");

  if (!btn) return;

  seleccionarMetodo(btn.dataset.metodo);

});



toggleDesglose?.addEventListener("change", () => {

  if (bloqueDesglose) {

    bloqueDesglose.classList.toggle("oculto", !toggleDesglose.checked);

  }

  if (panelAsignacion) {

    panelAsignacion.classList.toggle("oculto", toggleDesglose.checked);

  }

  delete montoEfectivo?.dataset.ultimoEdit;

  delete montoTransferencia?.dataset.ultimoEdit;

  aplicarMontosPorMetodo();

  actualizarPreviewAsignacion();

});



montoTotal?.addEventListener("input", () => {

  delete montoEfectivo?.dataset.ultimoEdit;

  delete montoTransferencia?.dataset.ultimoEdit;

  if (toggleDesglose?.checked) {

    recalcularDesgloseManual();

  } else {

    aplicarMontosPorMetodo();

  }

  actualizarPreviewAsignacion();

});



metodoDeposito?.addEventListener("change", () => {

  seleccionarMetodo(metodoDeposito.value);

});



montoEfectivo?.addEventListener("input", () => {

  montoEfectivo.dataset.ultimoEdit = "efectivo";

  recalcularDesgloseManual();

});



montoTransferencia?.addEventListener("input", () => {

  montoTransferencia.dataset.ultimoEdit = "transferencia";

  recalcularDesgloseManual();

});



form?.addEventListener("submit", async (e) => {

  e.preventDefault();

  const boton = form.querySelector("button[type='submit']");



  if (!toggleDesglose?.checked) {

    aplicarMontosPorMetodo();

  }



  let payload = {

    farmacia_id: obtenerFarmaciaId(),

    periodo_desde: form.periodo_desde.value,

    periodo_hasta: form.periodo_hasta.value,

    cantidad_recetas: parseInt(form.cantidad_recetas.value, 10) || 0,

    monto_total: parseMonto(form.monto_total.value),

    metodo_deposito: form.metodo_deposito.value,

    observaciones: form.observaciones.value.trim(),

  };



  if (toggleDesglose?.checked) {

    payload.monto_efectivo = parseMonto(form.monto_efectivo.value);

    payload.monto_transferencia = parseMonto(form.monto_transferencia.value);

    payload = normalizarPayload(payload);

  }



  if (!payload.farmacia_id) {

    mostrarError(resultado, "Selecciona una farmacia válida.");

    return;

  }

  if (payload.periodo_hasta < payload.periodo_desde) {

    mostrarError(resultado, "El periodo 'hasta' no puede ser anterior a 'desde'.");

    return;

  }

  if (payload.monto_total <= 0) {

    mostrarError(resultado, "El monto total debe ser mayor a cero.");

    return;

  }

  if (toggleDesglose?.checked) {

    const suma = (payload.monto_efectivo || 0) + (payload.monto_transferencia || 0);

    if (Math.abs(suma - payload.monto_total) > 0.01) {

      mostrarError(

        resultado,

        "La suma de efectivo y transferencia debe coincidir con el monto total."

      );

      return;

    }

  }



  boton.disabled = true;

  resultado.classList.remove("oculto", "error", "resultado-exito");

  resultado.innerHTML = `

    <div class="resultado-exito-card">

      <div class="resultado-cargando">Generando depósito…</div>

    </div>

  `;



  try {

    const res = await fetch("/api/depositos", {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      body: JSON.stringify(payload),

    });

    const data = await res.json();

    if (!res.ok) throw new Error(data.error || "Error al registrar");



    resultado.classList.add("resultado-exito");

    resultado.innerHTML = `

      <div class="resultado-exito-card">

        <div class="resultado-exito-icono" aria-hidden="true">

          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>

        </div>

        <h3>Depósito registrado correctamente</h3>

        <div class="resultado-datos">

          <span>Código: <code>${data.codigo_deposito}</code></span>

          <span>Referencia: <strong>${data.referencia_banco}</strong></span>

        </div>

        <a class="btn btn-primario btn-lg" href="/comprobante/${data.id}" target="_blank">Abrir comprobante para Macro</a>

      </div>

    `;

    form.reset();

    seleccionarMetodo("tas_macro");

    if (toggleDesglose) toggleDesglose.checked = false;

    if (bloqueDesglose) bloqueDesglose.classList.add("oculto");

    if (panelAsignacion) panelAsignacion.classList.remove("oculto");

    if (montoTransferencia) montoTransferencia.value = "0.00";

    actualizarPreviewAsignacion();

  } catch (err) {

    resultado.classList.add("error");

    resultado.innerHTML = `<p>${err.message}</p>`;

  } finally {

    boton.disabled = false;

  }

});



function mostrarError(contenedor, mensaje) {

  contenedor.classList.remove("oculto");

  contenedor.classList.add("error");

  contenedor.innerHTML = `<p>${mensaje}</p>`;

}



// Estado inicial

if (bloqueDesglose) bloqueDesglose.classList.add("oculto");

actualizarPreviewAsignacion();

