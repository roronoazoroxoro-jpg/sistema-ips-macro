# Matriz de requisitos — Documentación Macro vs Sistema IPS

**Proyecto:** Sistema de depósito digital de cajas de farmacias  
**Convenio demo:** `05170000005` · Grupo `MUNISAL` · Servicio `5170`  
**Fecha de revisión:** Junio 2026

**Leyenda:** ✅ Cumple · ⚠️ Parcial · ❌ No implementado

---

## Resumen ejecutivo

| Documento | Requisitos revisados | ✅ | ⚠️ | ❌ |
|-----------|---------------------:|---:|---:|---:|
| DeudaPub (TXT ejemplo) | 8 | 6 | 2 | 0 |
| DPPPdat (LIS ejemplo) | 7 | 5 | 2 | 0 |
| Diseño EM590 (XLS) | 18 | 11 | 5 | 2 |
| Excel ejemplo (XLSM) | 10 | 7 | 2 | 1 |
| Ficha Recaudaciones (PDF) | 14 | 8 | 4 | 2 |
| Instructivo TAS (PDF) | 6 | 6 | 0 | 0 |
| **Total** | **63** | **43 (68%)** | **15 (24%)** | **5 (8%)** |

---

## 1. DeudaPubBancoMacro (archivo de recaudación — TXT)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 1.1 | Encabezado `H` + grupo de deudas | Generación → Panel IPS → Descargar DeudaPub | ✅ |
| 1.2 | Registros detalle tipo `D` + servicio `5170` | `services/macro_archivos.py` | ✅ |
| 1.3 | Identificación deudor por CUIT/CUIL | Registro de farmacia + campo documento en archivo | ✅ |
| 1.4 | Nombre del deudor en el registro | Nombre farmacia en línea de detalle | ✅ |
| 1.5 | Trailer `T` con cantidad y total | Generación automática del trailer | ✅ |
| 1.6 | Archivo listo para envío al banco | Descarga `.txt` desde Panel IPS | ✅ |
| 1.7 | Coincidencia byte-a-byte con archivo ejemplo (774 vs 775 pos.) | Validado contra muestra; spec EM590 usa 775 | ⚠️ |
| 1.8 | Modalidad pago previo (importe en cero, vigencia 2099) | Configurable; por defecto deuda publicada con monto | ⚠️ |

---

## 2. DPPPdat (archivo de rendición — LIS)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 2.1 | Encabezado `HMUNISAL` | Parser `parsear_archivo_rendicion()` | ✅ |
| 2.2 | Registros `D5170` con pagos | Importación Panel IPS | ✅ |
| 2.3 | Extracción de monto pagado | Posición EM590 + fallback campo `N` | ✅ |
| 2.4 | Cuenta recaudadora `8030585583533` | Config + parser | ✅ |
| 2.5 | Trailer con total de registros e importe | Lectura y muestra en resumen de conciliación | ✅ |
| 2.6 | Cruce automático con depósitos IPS | Conciliación por CUIT/código/monto/nombre | ✅ |
| 2.7 | Confirmación automática de coincidencias | Checkbox en Panel IPS | ✅ |
| 2.8 | Parseo de todos los campos bancarios (pos. 631+) | Solo campos necesarios para conciliar | ⚠️ |

---

## 3. Diseño de Registro EM590 (XLS oficial)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 3.1 | Registro cabecera `H` (pos. 1–33) | `_linea_cabecera()` | ✅ |
| 3.2 | Registro detalle `D` (775 caracteres) | `_linea_detalle()` | ✅ |
| 3.3 | Código servicio pos. 2–5 (`5170`) | `config.py` → `codigo_servicio` | ✅ |
| 3.4 | Código deudor pos. 6–23 (18 chars) | Código IPS farmacia | ✅ |
| 3.5 | Nro. comprobante pos. 24–41 | Código `IPS-MACRO-…` | ✅ |
| 3.6 | Tipo documento `80` (CUIT) pos. 42–43 | Generación automática | ✅ |
| 3.7 | Nro. documento pos. 44–56 (13 chars) | CUIT farmacia | ✅ |
| 3.8 | Fecha origen / vigencia pos. 57–72 | Periodo del depósito | ✅ |
| 3.9 | Importe 1er vencimiento pos. 73–87 | Monto total del depósito | ✅ |
| 3.10 | Nombre deudor pos. 142–171 | Nombre farmacia | ✅ |
| 3.11 | Identificación deuda pos. 172–201 | Código de depósito | ✅ |
| 3.12 | Código moneda `80` pos. 238–239 | `codigo_moneda` en config | ✅ |
| 3.13 | Trailer `T` pos. 1–21 | `_linea_trailer()` | ✅ |
| 3.14 | 2do y 3er vencimiento (importes/fechas opcionales) | No requerido para cajas IPS | ❌ |
| 3.15 | Leyendas 1–10 para ticket de caja (pos. 251+) | No generadas | ❌ |
| 3.16 | Campo email depositante (pos. 631) | No incluido | ⚠️ |
| 3.17 | Campos banco en rendición (pos. 631–749) | Parseo parcial para conciliación | ⚠️ |
| 3.18 | Certificación formal contra herramienta Excel Macro | Inferido de ejemplos; sin test oficial cruzado | ⚠️ |

---

## 4. Archivo de recaudación de Ejemplo (XLSM)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 4.1 | Grupo `MUNISAL` | Barra convenio + config + archivo | ✅ |
| 4.2 | Código servicio `5170` | Config + UI | ✅ |
| 4.3 | Moneda `80` (pesos) | Config + generación | ✅ |
| 4.4 | Hoja «Ingresar Datos» → archivo plano | Reemplazado por formulario web `/farmacia` | ✅ |
| 4.5 | Generación en carpeta `C:\Deuda_Publicada\Envio` | Rutas documentadas; descarga manual desde Panel IPS | ⚠️ |
| 4.6 | Recepción `DPPPdat` en `C:\Deuda_Publicada\Recepcion` | Upload web en Panel IPS (equivale a la función del Excel) | ✅ |
| 4.7 | Conversión rendición a planilla Excel | Export CSV + tabla de conciliación en pantalla | ⚠️ |
| 4.8 | Botón «Generación Archivo» integrado | Botón «Descargar DeudaPub» en Panel IPS | ✅ |
| 4.9 | Botón «Recepción Archivo» integrado | Formulario importar `.lis` | ✅ |
| 4.10 | Macros VBA del Excel (automatización local) | No replicadas; sustituidas por app web | ❌ |

---

## 5. BM50464 — Ficha de Producto Recaudaciones (PDF)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 5.1 | Eliminar boletas personalizadas | Inicio: comparación Antes/Ahora | ✅ |
| 5.2 | Publicación de deudores e importes | Export DeudaPub + registro farmacia | ✅ |
| 5.3 | Pago solo total (monto exacto) | Validación monto en depósito | ✅ |
| 5.4 | Pago por efectivo en TAS | Canal `tas_macro` + guía TAS | ✅ |
| 5.5 | Pago por transferencia / home banking | Canales en formulario + comprobante | ✅ |
| 5.6 | Pago por ventanilla (efectivo/cheque) | Canal ventanilla + comprobante QR | ✅ |
| 5.7 | Identificación por CUIT/DNI + convenio | CUIT farmacia + convenio en toda la UI | ✅ |
| 5.8 | Intercambio por SFTP / WinSCP | Rutas y flujo documentados en Panel IPS | ⚠️ |
| 5.9 | Conexión SFTP automática desde el sistema | Solo manual (descarga/upload) | ❌ |
| 5.10 | Información online en Banca Internet Empresas | No integrado (fuera de alcance web) | ❌ |
| 5.11 | Conciliación automatizada | Import DPPPdat + cruce + confirmación | ✅ |
| 5.12 | Carga de cliente eventual (contingencia cajero) | Proceso del banco; no en sistema IPS | ⚠️ |
| 5.13 | eCheq / cheques diferidos | Mencionado en ficha; no como canal en formulario | ⚠️ |
| 5.14 | Mesa de ayuda `0-810-555-2112 op. 7` | Footer + barra convenio + comprobante | ✅ |

---

## 6. Instructivo TAI — Terminal TAS (PDF)

| # | Requisito (documento) | Pantalla / módulo | Estado |
|---|------------------------|-------------------|--------|
| 6.1 | Opción «Pagá» en TAS | Guía en comprobante (sección TAS) | ✅ |
| 6.2 | «Servicio integral de recaudaciones» | Instrucciones en comprobante + lateral farmacia | ✅ |
| 6.3 | Informar número de convenio | Convenio visible + instrucción explícita | ✅ |
| 6.4 | Validar convenio correcto | Texto guía al operador | ✅ |
| 6.5 | Seleccionar registro de la farmacia | Explicado en guía (post-publicación DeudaPub) | ✅ |
| 6.6 | Ingresar billetes y confirmar pago | Paso final en guía TAS | ✅ |

---

## Funcionalidades transversales del sistema

| # | Requisito | Pantalla / módulo | Estado |
|---|-----------|-------------------|--------|
| T.1 | Registro de cierre de caja por farmacia | `/farmacia` | ✅ |
| T.2 | Comprobante con QR y referencia | `/comprobante/<id>` | ✅ |
| T.3 | Roles farmacia / admin IPS | Login + permisos | ✅ |
| T.4 | Panel seguimiento pendientes / confirmados | `/ips` | ✅ |
| T.5 | Auditoría de acciones | Tabla `auditoria` + logs en API | ✅ |
| T.6 | Export CSV para reportes | Panel IPS → Exportar CSV | ✅ |
| T.7 | Usuarios demo para presentación | Login (admin / f001…) | ✅ |
| T.8 | Diseño visual profesional para demo | CSS + templates actualizados | ✅ |

---

## Mapa rápido: documento → pantalla

| Si el auditor pregunta por… | Mostrar en el sistema |
|-----------------------------|------------------------|
| Archivo de recaudación | Panel IPS → **Descargar DeudaPub** |
| Archivo de rendición | Panel IPS → **Importar DPPPdat** |
| Pago en TAS | Farmacia → TAS → **Comprobante** (guía + convenio) |
| Sin boletas manuales | **Inicio** → sección Antes/Ahora |
| Formato oficial EM590 | Código en `macro_archivos.py` + README |
| Seguimiento IPS | **Panel IPS** → tablas pendientes/confirmados |
| Datos del convenio | **Barra verde** superior en todas las pantallas |

---

## Pendientes recomendados (post-presentación)

1. **Validación cruzada** — Generar un DeudaPub y compararlo con el Excel oficial de Macro línea por línea.
2. **SFTP automático** — Integrar WinSCP/script para subir DeudaPub y bajar DPPPdat sin intervención manual.
3. **Modalidad pago previo** — Toggle admin para exportar en modo pago previo (importe cero) si el convenio lo exige.
4. **Leyendas en ticket** — Campos opcionales EM590 (leyendas 1–10) en comprobante/archivo.
5. **Banca Internet Empresas** — Consulta de cobranzas online (API o enlace documentado).

---

*Documento generado para apoyo en presentación. Los ítems ⚠️ son aceptables para demo; los ❌ son alcance fase 2 o responsabilidad del banco/infraestructura.*
