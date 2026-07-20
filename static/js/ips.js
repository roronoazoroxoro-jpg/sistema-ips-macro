async function accionDeposito(id, ruta) {
  const res = await fetch(`/api/depositos/${id}/${ruta}`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "No se pudo completar la acción");
    return;
  }
  location.reload();
}

document.querySelectorAll(".confirmar").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (confirm("¿Confirmar que el depósito fue acreditado en Macro?")) {
      accionDeposito(btn.dataset.id, "confirmar");
    }
  });
});

document.querySelectorAll(".cancelar").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (confirm("¿Cancelar este depósito pendiente?")) {
      accionDeposito(btn.dataset.id, "cancelar");
    }
  });
});

document.getElementById("form-rendicion")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const resultado = document.getElementById("resultado-conciliacion");
  const boton = form.querySelector("button[type='submit']");
  const fd = new FormData(form);

  boton.disabled = true;
  resultado.classList.remove("oculto", "error");
  resultado.innerHTML = "Procesando archivo de rendición…";

  try {
    const res = await fetch("/api/conciliacion/rendicion", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Error al conciliar");

    const filas = data.resultados
      .map((r) => {
        const dep = r.deposito;
        const pago = r.pago;
        const depTxt = dep
          ? `<strong>${dep.codigo_deposito}</strong> — ${dep.farmacia_nombre}`
          : "—";
        return `<tr>
          <td>${pago.nombre || pago.documento}</td>
          <td>$${pago.monto.toFixed(2)}</td>
          <td>${depTxt}</td>
          <td><span class="chip chip-${r.estado}">${r.estado}</span></td>
        </tr>`;
      })
      .join("");

    resultado.innerHTML = `
      <p><strong>Conciliación completada</strong></p>
      <p>Registros en archivo: ${data.resumen.cantidad_registros} ·
         Coincidencias: ${data.coincidencias} ·
         Confirmados: ${data.confirmados} ·
         Sin coincidencia: ${data.sin_coincidencia}</p>
      <div class="tabla-scroll">
        <table class="tabla tabla-suave">
          <thead><tr><th>Pagador (Macro)</th><th>Monto</th><th>Depósito IPS</th><th>Estado</th></tr></thead>
          <tbody>${filas}</tbody>
        </table>
      </div>
      ${data.confirmados > 0 ? '<p class="campo-ayuda">Recargá la página para ver los depósitos confirmados.</p>' : ""}
    `;

    if (data.confirmados > 0) {
      setTimeout(() => location.reload(), 2500);
    }
  } catch (err) {
    resultado.classList.add("error");
    resultado.innerHTML = `<p>${err.message}</p>`;
  } finally {
    boton.disabled = false;
  }
});
