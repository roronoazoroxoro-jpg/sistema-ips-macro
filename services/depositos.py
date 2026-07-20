import io
import json
import csv
from datetime import datetime

import qrcode

from config import BANCO_MACRO, MAX_MONTO_DEPOSITO, METODOS_DEPOSITO
from database import get_db, _utc_now


def generar_codigo_deposito(farmacia_codigo: str) -> str:
    """Código único legible en ventanilla / home banking Macro."""
    ts = datetime.now().strftime("%y%m%d%H%M")
    sufijo = farmacia_codigo.replace("F-", "").zfill(3)[-3:]
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM depositos_caja").fetchone()[0] + 1
    return f"IPS-MACRO-{ts}-{sufijo}-{n:04d}"


def crear_deposito(data: dict) -> dict:
    _validar_deposito(data)
    with get_db() as conn:
        farmacia = conn.execute(
            "SELECT * FROM farmacias WHERE id = ? AND activa = 1", (data["farmacia_id"],)
        ).fetchone()
        if not farmacia:
            raise ValueError("Farmacia no encontrada o inactiva")

        codigo = generar_codigo_deposito(farmacia["codigo_ips"])
        referencia = f"{farmacia['codigo_ips']}|{codigo}"

        conn.execute(
            """
            INSERT INTO depositos_caja (
                codigo_deposito, farmacia_id, periodo_desde, periodo_hasta,
                cantidad_recetas, monto_total, monto_efectivo, monto_transferencia,
                metodo_deposito, estado, referencia_banco, observaciones, creado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?, ?)
            """,
            (
                codigo,
                data["farmacia_id"],
                data["periodo_desde"],
                data["periodo_hasta"],
                data.get("cantidad_recetas", 0),
                data["monto_total"],
                data.get("monto_efectivo", data["monto_total"]),
                data.get("monto_transferencia", 0),
                data.get("metodo_deposito", "ventanilla_macro"),
                referencia,
                data.get("observaciones", ""),
                _utc_now(),
            ),
        )
        dep_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return obtener_deposito(dep_id)


def _normalizar_montos(data: dict) -> None:
    """Ajusta efectivo/transferencia según el canal si no cuadran con el total."""
    metodo = data.get("metodo_deposito", "tas_macro")
    monto_total = float(data["monto_total"])
    monto_efectivo = float(data.get("monto_efectivo", 0) or 0)
    monto_transferencia = float(data.get("monto_transferencia", 0) or 0)

    if round(monto_efectivo + monto_transferencia, 2) == round(monto_total, 2):
        return

    if metodo in ("tas_macro", "ventanilla_macro"):
        data["monto_efectivo"] = monto_total
        data["monto_transferencia"] = 0
    elif metodo in ("transferencia_macro", "home_banking"):
        data["monto_efectivo"] = 0
        data["monto_transferencia"] = monto_total


def _validar_deposito(data: dict):
    _normalizar_montos(data)
    try:
        monto_total = float(data["monto_total"])
    except Exception as e:
        raise ValueError("Monto total inválido") from e
    if monto_total <= 0:
        raise ValueError("El monto total debe ser mayor a cero")
    if monto_total > MAX_MONTO_DEPOSITO:
        raise ValueError(f"El monto total supera el límite permitido (${MAX_MONTO_DEPOSITO:,.2f})")

    monto_efectivo = float(data.get("monto_efectivo", monto_total) or 0)
    monto_transferencia = float(data.get("monto_transferencia", 0) or 0)
    if monto_efectivo < 0 or monto_transferencia < 0:
        raise ValueError("Los montos no pueden ser negativos")
    if round(monto_efectivo + monto_transferencia, 2) != round(monto_total, 2):
        raise ValueError("La suma de efectivo y transferencia debe coincidir con el monto total")

    try:
        d_desde = datetime.strptime(data["periodo_desde"], "%Y-%m-%d")
        d_hasta = datetime.strptime(data["periodo_hasta"], "%Y-%m-%d")
    except Exception as e:
        raise ValueError("Formato de periodo inválido (usar YYYY-MM-DD)") from e
    if d_hasta < d_desde:
        raise ValueError("La fecha 'hasta' no puede ser menor a 'desde'")
    if (d_hasta - d_desde).days > 62:
        raise ValueError("El periodo máximo permitido es de 62 días")

    recetas = int(data.get("cantidad_recetas", 0) or 0)
    if recetas < 0:
        raise ValueError("La cantidad de recetas no puede ser negativa")
    if data.get("metodo_deposito") not in METODOS_DEPOSITO:
        raise ValueError("Método de depósito inválido")


def obtener_deposito(dep_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT d.*, f.codigo_ips, f.nombre AS farmacia_nombre, f.localidad
            FROM depositos_caja d
            JOIN farmacias f ON f.id = d.farmacia_id
            WHERE d.id = ?
            """,
            (dep_id,),
        ).fetchone()
    if not row:
        raise ValueError("Depósito no encontrado")
    return dict(row)


def listar_depositos(estado: str | None = None, farmacia_id: int | None = None) -> list:
    query = """
        SELECT d.*, f.codigo_ips, f.nombre AS farmacia_nombre, f.localidad
        FROM depositos_caja d
        JOIN farmacias f ON f.id = d.farmacia_id
        WHERE 1=1
    """
    params: list = []
    if estado:
        query += " AND d.estado = ?"
        params.append(estado)
    if farmacia_id:
        query += " AND d.farmacia_id = ?"
        params.append(farmacia_id)
    query += " ORDER BY d.creado_en DESC"
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def confirmar_deposito(dep_id: int) -> dict:
    with get_db() as conn:
        dep = conn.execute(
            "SELECT estado FROM depositos_caja WHERE id = ?", (dep_id,)
        ).fetchone()
        if not dep:
            raise ValueError("Depósito no encontrado")
        if dep["estado"] == "confirmado":
            raise ValueError("El depósito ya fue confirmado")
        conn.execute(
            "UPDATE depositos_caja SET estado = 'confirmado', confirmado_en = ? WHERE id = ?",
            (_utc_now(), dep_id),
        )
    return obtener_deposito(dep_id)


def cancelar_deposito(dep_id: int) -> dict:
    with get_db() as conn:
        updated = conn.execute(
            "UPDATE depositos_caja SET estado = 'cancelado' WHERE id = ? AND estado = 'pendiente'",
            (dep_id,),
        ).rowcount
        if updated == 0:
            dep = conn.execute("SELECT id FROM depositos_caja WHERE id = ?", (dep_id,)).fetchone()
            if not dep:
                raise ValueError("Depósito no encontrado")
            raise ValueError("Solo se pueden cancelar depósitos en estado pendiente")
    return obtener_deposito(dep_id)


def listar_farmacias() -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM farmacias WHERE activa = 1 ORDER BY nombre"
        ).fetchall()
    return [dict(r) for r in rows]


def payload_qr(deposito: dict) -> dict:
    return {
        "tipo": "IPS_DEPOSITO_MACRO",
        "version": 1,
        "codigo": deposito["codigo_deposito"],
        "referencia": deposito["referencia_banco"],
        "cbu": BANCO_MACRO["cbu_destino"],
        "alias": BANCO_MACRO["alias"],
        "monto": deposito["monto_total"],
        "farmacia": deposito["farmacia_nombre"],
        "periodo": f"{deposito['periodo_desde']} / {deposito['periodo_hasta']}",
    }


def generar_qr_png(deposito: dict) -> bytes:
    payload = json.dumps(payload_qr(deposito), ensure_ascii=False)
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def instrucciones_macro(deposito: dict) -> dict:
    metodo = deposito.get("metodo_deposito", "transferencia_macro")
    convenio = BANCO_MACRO.get("numero_convenio", "")
    return {
        "banco": BANCO_MACRO["nombre"],
        "titular": BANCO_MACRO["titular"],
        "cbu": BANCO_MACRO["cbu_destino"],
        "alias": BANCO_MACRO["alias"],
        "cuit": BANCO_MACRO["cuit"],
        "cuenta_recaudadora": BANCO_MACRO.get("cuenta_recaudadora", ""),
        "convenio": convenio,
        "grupo_deudas": BANCO_MACRO.get("grupo_deudas", "MUNISAL"),
        "codigo_servicio": BANCO_MACRO.get("codigo_servicio", "5170"),
        "concepto": f"{BANCO_MACRO['concepto_default']} — {deposito['codigo_deposito']}",
        "referencia_obligatoria": deposito["referencia_banco"],
        "monto": deposito["monto_total"],
        "metodo": metodo,
        "metodo_etiqueta": METODOS_DEPOSITO.get(metodo, metodo),
        "metodos": _metodos_por_tipo(metodo),
        "tas": _instrucciones_tas(convenio),
        "mesa_ayuda": BANCO_MACRO.get("mesa_ayuda", ""),
        "email_recaudaciones": BANCO_MACRO.get("email_recaudaciones", ""),
    }


def _instrucciones_tas(convenio: str) -> list:
    return [
        "En la terminal TAS, seleccionar la opción «Pagá».",
        "Ingresar en «Servicio integral de recaudaciones».",
        f"Informar el número de convenio: {convenio or '—'}.",
        "Validar el convenio y seleccionar el registro de la farmacia.",
        "Ingresar billetes y confirmar el pago.",
    ]


def _metodos_por_tipo(metodo: str) -> list:
    convenio = BANCO_MACRO.get("numero_convenio", "")
    base = [
        "El IPS publica la deuda en Banco Macro mediante archivo DeudaPub (formato EM590).",
        f"Número de convenio Macro: {convenio or 'consultar con Farmacias Contratadas'}.",
        "Utilizar la referencia bancaria exacta indicada en este comprobante.",
    ]
    if metodo == "tas_macro":
        return base + _instrucciones_tas(convenio)
    if metodo == "transferencia_macro":
        return base + [
            "Realizar transferencia desde cuenta Macro al CBU o alias del IPS.",
            "Indicar la referencia completa en observaciones antes de confirmar.",
            "Verificar que el monto coincida con el comprobante.",
        ]
    if metodo == "home_banking":
        return base + [
            "Ingresar a Home Banking Macro → Transferencias.",
            "Pegar CBU/alias y referencia obligatoria antes de confirmar.",
            "Conservar el comprobante digital de la operación.",
        ]
    if metodo == "ventanilla_macro":
        return base + [
            "Presentar este comprobante impreso con código QR en ventanilla Macro.",
            "Informar número de convenio y referencia al operador.",
            "El operador registrará el depósito en el módulo de recaudación.",
        ]
    return base


def exportar_depositos_csv(estado: str | None = None, farmacia_id: int | None = None) -> str:
    rows = listar_depositos(estado=estado, farmacia_id=farmacia_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "codigo_deposito",
            "farmacia",
            "codigo_ips",
            "localidad",
            "estado",
            "metodo_deposito",
            "periodo_desde",
            "periodo_hasta",
            "cantidad_recetas",
            "monto_total",
            "referencia_banco",
            "creado_en",
            "confirmado_en",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["codigo_deposito"],
                r["farmacia_nombre"],
                r["codigo_ips"],
                r["localidad"],
                r["estado"],
                r["metodo_deposito"],
                r["periodo_desde"],
                r["periodo_hasta"],
                r["cantidad_recetas"],
                f"{r['monto_total']:.2f}",
                r["referencia_banco"],
                r["creado_en"],
                r["confirmado_en"] or "",
            ]
        )
    return output.getvalue()
