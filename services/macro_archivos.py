"""Generación e importación de archivos Banco Macro (DeudaPub / DPPPdat).

Formato basado en:
- Diseño de Registro Deuda Publicada EM590 (xls)
- Archivo de recaudacion de Ejemplo.xlsm
- Ejemplos DeudaPubBancoMacro y DPPPdat provistos por el banco
"""

from __future__ import annotations

import re
from datetime import datetime

from config import BANCO_MACRO
from database import get_db, _utc_now

# EM590: registro detalle de 775 posiciones; rendición banco 850 posiciones.
LINE_WIDTH_RECAUDACION = 775
LINE_WIDTH_RENDICION = 850


def _solo_digitos(valor: str | None, largo: int | None = None) -> str:
    digits = re.sub(r"\D", "", valor or "")
    if largo:
        return digits[:largo].zfill(largo)[-largo:]
    return digits


def _monto_centavos(monto: float) -> int:
    return int(round(float(monto) * 100))


def _formatear_importe(monto: float | None) -> str:
    """Campo numérico 13,2 → 15 dígitos (centavos sin separador)."""
    if monto is None:
        return "0" * 15
    return str(_monto_centavos(monto)).zfill(15)[-15:]


def _campo_alfanumerico(valor: str, largo: int, alinear: str = "left") -> str:
    texto = (valor or "").upper().strip()
    if alinear == "right":
        return texto.rjust(largo)[:largo]
    return texto.ljust(largo)[:largo]


def _campo_numerico(valor: str | int, largo: int) -> str:
    return str(valor).zfill(largo)[-largo:]


def _crear_registro(ancho: int = LINE_WIDTH_RECAUDACION) -> list[str]:
    return [" "] * ancho


def _escribir(registro: list[str], pos_inicial: int, largo: int, valor: str) -> None:
    inicio = pos_inicial - 1
    for i, ch in enumerate(valor[:largo]):
        if inicio + i < len(registro):
            registro[inicio + i] = ch


def _linea_cabecera(ahora: datetime | None = None) -> str:
    ahora = ahora or datetime.now()
    grupo = BANCO_MACRO.get("grupo_deudas", "MUNISAL")
    return f"H{grupo[:10].ljust(10)}{ahora.strftime('%Y%m%d%H%M%S')}0000".ljust(29)[:29]


def _linea_detalle(deposito: dict, farmacia: dict, modo: str = "deuda_publicada") -> str:
    """Arma registro D según EM590 (posiciones 1-based del diseño oficial)."""
    registro = _crear_registro()
    codigo_servicio = BANCO_MACRO.get("codigo_servicio", "5170")
    codigo_deudor = _campo_alfanumerico(
        farmacia.get("codigo_ips") or _solo_digitos(farmacia.get("cuit"), 11), 18, "right"
    )
    comprobante = _campo_alfanumerico(deposito.get("codigo_deposito", ""), 18, "right")
    tipo_doc = "80"
    nro_doc = _campo_alfanumerico(_solo_digitos(farmacia.get("cuit"), 11), 13, "right")
    fecha_origen = deposito["periodo_desde"].replace("-", "")
    fecha_vigencia = deposito["periodo_hasta"].replace("-", "")
    nombre = _campo_alfanumerico(
        farmacia.get("nombre") or deposito.get("farmacia_nombre", ""), 30
    )
    identificacion = _campo_alfanumerico(deposito.get("codigo_deposito", ""), 30)
    moneda = BANCO_MACRO.get("codigo_moneda", "80")

    if modo == "pago_previo":
        importe = _formatear_importe(None)
        fecha_vigencia = "20990305"
        comprobante = "0" * 18
    else:
        importe = _formatear_importe(deposito["monto_total"])

    _escribir(registro, 1, 1, "D")
    _escribir(registro, 2, 4, _campo_numerico(codigo_servicio, 4))
    _escribir(registro, 6, 18, codigo_deudor)
    _escribir(registro, 24, 18, comprobante)
    _escribir(registro, 42, 2, tipo_doc)
    _escribir(registro, 44, 13, nro_doc)
    _escribir(registro, 57, 8, fecha_origen)
    _escribir(registro, 65, 8, fecha_vigencia)
    _escribir(registro, 73, 15, importe)
    _escribir(registro, 88, 8, fecha_vigencia if modo != "pago_previo" else " " * 8)
    _escribir(registro, 142, 30, nombre)
    _escribir(registro, 172, 30, identificacion)
    _escribir(registro, 238, 2, moneda)
    return "".join(registro)


def _linea_trailer(cantidad_registros: int, total_importe: float) -> str:
    """Trailer T: cantidad incluye cabecera + detalles + trailer (EM590)."""
    return f"T{_campo_numerico(cantidad_registros, 5)}{_formatear_importe(total_importe)}"


def generar_archivo_recaudacion(
    deposito_ids: list[int] | None = None,
    modo: str | None = None,
) -> tuple[str, str, list[int]]:
    """Genera DeudaPub y marca depósitos incluidos en el archivo."""
    modo = modo or BANCO_MACRO.get("modalidad_publicacion", "deuda_publicada")

    with get_db() as conn:
        query = """
            SELECT d.*, f.codigo_ips, f.nombre AS farmacia_nombre, f.localidad,
                   f.cuit, f.cbu_farmacia
            FROM depositos_caja d
            JOIN farmacias f ON f.id = d.farmacia_id
            WHERE d.estado = 'pendiente'
        """
        params: list = []
        if deposito_ids:
            placeholders = ",".join("?" * len(deposito_ids))
            query += f" AND d.id IN ({placeholders})"
            params.extend(deposito_ids)
        else:
            query += " AND d.archivo_recaudacion_en IS NULL"
        query += " ORDER BY d.creado_en ASC"
        rows = conn.execute(query, params).fetchall()

        if not rows:
            raise ValueError("No hay depósitos pendientes para exportar a recaudación")

        ahora = datetime.now()
        header = _linea_cabecera(ahora)
        detalles = [_linea_detalle(dict(r), dict(r), modo) for r in rows]
        total_importe = 0 if modo == "pago_previo" else sum(r["monto_total"] for r in rows)
        total_registros = len(detalles) + 2  # cabecera + trailer
        trailer = _linea_trailer(total_registros, total_importe)
        contenido = "\n".join([header, *detalles, trailer]) + "\n"

        ids = [r["id"] for r in rows]
        marca = _utc_now()
        conn.executemany(
            "UPDATE depositos_caja SET archivo_recaudacion_en = ? WHERE id = ?",
            [(marca, dep_id) for dep_id in ids],
        )

    nombre = f"DeudaPubBancoMacro_{ahora.strftime('%Y%m%d')}.txt"
    return contenido, nombre, ids


def _extraer_monto_rendicion(linea: str) -> float | None:
    # EM590: importe 1er vencimiento posición 73, largo 15
    candidato = linea[72:87]
    if candidato.isdigit():
        monto = int(candidato) / 100
        if 0 < monto < 500_000_000:
            return monto

    match = re.search(r"N(\d{15,30})", linea)
    if match:
        monto = int(match.group(1)[:15]) / 100
        if 0 < monto < 500_000_000:
            return monto
    return None


def _extraer_documento_rendicion(linea: str) -> str:
    bloque = linea[43:56].strip() or linea[5:23].strip()
    return _solo_digitos(bloque, 11)


def _extraer_codigo_deudor_rendicion(linea: str) -> str:
    return linea[5:23].strip()


def _extraer_nombre_rendicion(linea: str) -> str:
    return linea[141:171].strip()


def _extraer_referencia_rendicion(linea: str) -> str:
    match = re.search(r"(N\d{15,30})", linea)
    return match.group(1) if match else ""


def _extraer_forma_pago(linea: str) -> str:
    if len(linea) < 642:
        return ""
    codigo = linea[641:642].strip()
    formas = {
        "1": "Efectivo",
        "2": "Cheque propia plaza",
        "7": "Débito en cuenta / transferencia",
    }
    return formas.get(codigo, codigo or "—")


def parsear_archivo_rendicion(contenido: str) -> dict:
    lineas = [ln.rstrip("\r\n") for ln in contenido.splitlines() if ln.strip()]
    if not lineas:
        raise ValueError("El archivo de rendición está vacío")

    header = lineas[0]
    if not header.startswith("H"):
        raise ValueError("Encabezado inválido: se esperaba registro H (HMUNISAL)")

    detalles = [ln for ln in lineas[1:-1] if ln.startswith("D")]
    trailer = lineas[-1]
    if not trailer.startswith("T"):
        raise ValueError("Trailer inválido: se esperaba registro T")

    pagos = []
    for idx, linea in enumerate(detalles, start=1):
        monto = _extraer_monto_rendicion(linea)
        if monto is None:
            continue
        pagos.append(
            {
                "linea": idx,
                "codigo_deudor": _extraer_codigo_deudor_rendicion(linea),
                "documento": _extraer_documento_rendicion(linea),
                "nombre": _extraer_nombre_rendicion(linea),
                "monto": monto,
                "forma_pago": _extraer_forma_pago(linea),
                "cuenta_recaudadora": linea[237:250].strip() or BANCO_MACRO.get("cuenta_recaudadora", ""),
                "referencia_macro": _extraer_referencia_rendicion(linea),
                "raw": linea,
            }
        )

    return {
        "header": header,
        "trailer": trailer,
        "cantidad_registros": int(trailer[1:6]),
        "monto_total_archivo": int(trailer[6:]) / 100 if trailer[6:].isdigit() else 0,
        "pagos": pagos,
    }


def conciliar_rendicion(contenido: str, confirmar_automatico: bool = False) -> dict:
    """Cruza pagos del archivo .lis con depósitos pendientes del IPS."""
    parsed = parsear_archivo_rendicion(contenido)
    resultados = []
    confirmados = 0

    with get_db() as conn:
        pendientes = conn.execute(
            """
            SELECT d.*, f.codigo_ips, f.nombre AS farmacia_nombre, f.localidad, f.cuit
            FROM depositos_caja d
            JOIN farmacias f ON f.id = d.farmacia_id
            WHERE d.estado = 'pendiente'
            ORDER BY d.creado_en ASC
            """
        ).fetchall()
        pendientes = [dict(p) for p in pendientes]

        for pago in parsed["pagos"]:
            match = _buscar_deposito(pendientes, pago)
            item = {
                "pago": pago,
                "deposito": match,
                "estado": "sin_coincidencia",
            }
            if match:
                item["estado"] = "coincidencia"
                if confirmar_automatico:
                    conn.execute(
                        """
                        UPDATE depositos_caja
                        SET estado = 'confirmado',
                            confirmado_en = ?,
                            referencia_macro = ?,
                            conciliado_en = ?
                        WHERE id = ? AND estado = 'pendiente'
                        """,
                        (
                            _utc_now(),
                            pago["referencia_macro"] or pago["documento"],
                            _utc_now(),
                            match["id"],
                        ),
                    )
                    match["estado"] = "confirmado"
                    confirmados += 1
                    item["estado"] = "confirmado"
            resultados.append(item)

    return {
        "resumen": parsed,
        "resultados": resultados,
        "coincidencias": sum(1 for r in resultados if r["estado"] in ("coincidencia", "confirmado")),
        "confirmados": confirmados,
        "sin_coincidencia": sum(1 for r in resultados if r["estado"] == "sin_coincidencia"),
    }


def _buscar_deposito(pendientes: list[dict], pago: dict) -> dict | None:
    doc = pago.get("documento", "")
    codigo_deudor = (pago.get("codigo_deudor") or "").strip().upper()
    monto = round(pago["monto"], 2)
    nombre = (pago.get("nombre") or "").upper()

    for dep in pendientes:
        if dep.get("estado") != "pendiente":
            continue
        codigo_ips = (dep.get("codigo_ips") or "").upper()
        if codigo_deudor and codigo_ips and codigo_deudor.endswith(codigo_ips.replace("-", "")):
            if round(dep["monto_total"], 2) == monto:
                return dep

    for dep in pendientes:
        if dep.get("estado") != "pendiente":
            continue
        cuit = _solo_digitos(dep.get("cuit"), 11)
        if doc and cuit and doc == cuit and round(dep["monto_total"], 2) == monto:
            return dep

    for dep in pendientes:
        if dep.get("estado") != "pendiente":
            continue
        if round(dep["monto_total"], 2) != monto:
            continue
        farmacia = (dep.get("farmacia_nombre") or "").upper()
        if nombre and farmacia and (nombre in farmacia or farmacia in nombre):
            return dep

    for dep in pendientes:
        if dep.get("estado") != "pendiente":
            continue
        if round(dep["monto_total"], 2) == monto:
            return dep

    return None
