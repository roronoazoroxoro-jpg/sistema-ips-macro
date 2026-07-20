document.querySelectorAll("[data-copiar]").forEach((el) => {
  el.style.cursor = "pointer";
  el.addEventListener("click", () => copiarTexto(el.dataset.copiar || el.textContent.trim(), el));
});

document.querySelectorAll(".btn-copiar").forEach((btn) => {
  btn.addEventListener("click", () => {
    const texto = btn.dataset.copiar || "";
    copiarTexto(texto, btn);
  });
});

async function copiarTexto(texto, elemento) {
  try {
    await navigator.clipboard.writeText(texto);
    const original = elemento.textContent;
    if (elemento.classList.contains("btn-copiar")) {
      elemento.textContent = "¡Copiado!";
      setTimeout(() => { elemento.textContent = original; }, 1500);
    } else {
      elemento.classList.add("copiado-flash");
      setTimeout(() => elemento.classList.remove("copiado-flash"), 1200);
    }
  } catch {
    /* sin portapapeles */
  }
}
