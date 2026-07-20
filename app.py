from io import BytesIO
from datetime import datetime
from flask import Flask, abort, g, jsonify, redirect, render_template, request, send_file, session, url_for

from config import BANCO_MACRO, FLASK_ENV, METODOS_DEPOSITO, SECRET_KEY
from database import init_db
from services import auth
from services import depositos as svc
from services import macro_archivos as macro

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = FLASK_ENV == "production"


@app.before_request
def setup():
    if not getattr(app, "_db_ready", False):
        init_db()
        app._db_ready = True
    g.user = auth.current_user()


@app.context_processor
def inject_template_globals():
    user_obj = getattr(g, "user", None)
    pendientes = 0
    if user_obj and user_obj.get("role") == "admin":
        try:
            pendientes = len(svc.listar_depositos(estado="pendiente"))
        except Exception:
            pendientes = 0
    return {
        "macro": BANCO_MACRO,
        "convenio": BANCO_MACRO.get("numero_convenio", ""),
        "metodos_deposito": METODOS_DEPOSITO,
        "pendientes_admin": pendientes,
    }


@app.route("/")
def index():
    if not g.user:
        return redirect(url_for("login"))
    return render_template("index.html", user=g.user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        if auth.authenticate(username, password, request.remote_addr):
            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))
        error = "Usuario o contraseña inválidos"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    auth.logout(request.remote_addr)
    return redirect(url_for("login"))


@app.route("/farmacia")
@auth.login_required()
def farmacia():
    if g.user["role"] == "farmacia":
        farmacias = [f for f in svc.listar_farmacias() if f["id"] == g.user["farmacia_id"]]
    else:
        farmacias = svc.listar_farmacias()
    return render_template(
        "farmacia.html", farmacias=farmacias, user=g.user
    )


@app.route("/ips")
@auth.login_required(role="admin")
def panel_ips():
    pendientes = svc.listar_depositos(estado="pendiente")
    confirmados = svc.listar_depositos(estado="confirmado")[:20]
    total_pendiente = sum(d["monto_total"] for d in pendientes)
    sin_enviar = sum(1 for d in pendientes if not d.get("archivo_recaudacion_en"))
    return render_template(
        "ips.html",
        pendientes=pendientes,
        confirmados=confirmados,
        total_pendiente=total_pendiente,
        sin_enviar=sin_enviar,
        user=g.user,
    )


@app.route("/comprobante/<int:dep_id>")
@auth.login_required()
def comprobante(dep_id):
    dep = _get_allowed_deposito(dep_id)
    instrucciones = svc.instrucciones_macro(dep)
    return render_template(
        "comprobante.html", deposito=dep, instrucciones=instrucciones, user=g.user
    )


@app.route("/api/farmacias")
@auth.api_login_required()
def api_farmacias():
    if g.user["role"] == "farmacia":
        return jsonify([f for f in svc.listar_farmacias() if f["id"] == g.user["farmacia_id"]])
    return jsonify(svc.listar_farmacias())


@app.route("/api/depositos", methods=["GET", "POST"])
@auth.api_login_required()
def api_depositos():
    if request.method == "GET":
        estado = request.args.get("estado")
        farmacia_id = request.args.get("farmacia_id", type=int)
        if g.user["role"] == "farmacia":
            farmacia_id = g.user["farmacia_id"]
        return jsonify(svc.listar_depositos(estado, farmacia_id))

    data = request.get_json() or {}
    if g.user["role"] == "farmacia":
        data["farmacia_id"] = g.user["farmacia_id"]
    required = ["periodo_desde", "periodo_hasta", "monto_total"]
    if g.user["role"] != "farmacia":
        required.insert(0, "farmacia_id")
    missing = [k for k in required if k not in data or data[k] in (None, "")]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400
    try:
        dep = svc.crear_deposito(data)
        auth.log_event(
            actor=g.user["username"],
            role=g.user["role"],
            accion="crear_deposito",
            entidad="depositos_caja",
            entidad_id=str(dep["id"]),
            detalle=f"{dep['codigo_deposito']} ${dep['monto_total']:.2f}",
            ip_origen=request.remote_addr,
        )
        return jsonify(dep), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/depositos/<int:dep_id>")
@auth.api_login_required()
def api_deposito(dep_id):
    try:
        return jsonify(_get_allowed_deposito(dep_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/depositos/<int:dep_id>/confirmar", methods=["POST"])
@auth.api_login_required(role="admin")
def api_confirmar(dep_id):
    try:
        data = svc.confirmar_deposito(dep_id)
        auth.log_event(
            actor=g.user["username"],
            role=g.user["role"],
            accion="confirmar_deposito",
            entidad="depositos_caja",
            entidad_id=str(dep_id),
            detalle=data["codigo_deposito"],
            ip_origen=request.remote_addr,
        )
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/depositos/<int:dep_id>/cancelar", methods=["POST"])
@auth.api_login_required(role="admin")
def api_cancelar(dep_id):
    try:
        data = svc.cancelar_deposito(dep_id)
        auth.log_event(
            actor=g.user["username"],
            role=g.user["role"],
            accion="cancelar_deposito",
            entidad="depositos_caja",
            entidad_id=str(dep_id),
            detalle=data["codigo_deposito"],
            ip_origen=request.remote_addr,
        )
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/depositos/<int:dep_id>/qr.png")
@auth.api_login_required()
def api_qr(dep_id):
    try:
        dep = _get_allowed_deposito(dep_id)
        png = svc.generar_qr_png(dep)
        return send_file(
            BytesIO(png),
            mimetype="image/png",
            download_name=f"{dep['codigo_deposito']}.png",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/depositos/export.csv")
@auth.api_login_required(role="admin")
def api_export_csv():
    estado = request.args.get("estado")
    csv_content = svc.exportar_depositos_csv(estado=estado)
    filename = f"depositos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(
        BytesIO(csv_content.encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/depositos/export.recaudacion")
@auth.api_login_required(role="admin")
def api_export_recaudacion():
    try:
        contenido, filename, ids = macro.generar_archivo_recaudacion()
        auth.log_event(
            actor=g.user["username"],
            role=g.user["role"],
            accion="exportar_recaudacion",
            entidad="depositos_caja",
            entidad_id=",".join(str(i) for i in ids),
            detalle=filename,
            ip_origen=request.remote_addr,
        )
        return send_file(
            BytesIO(contenido.encode("latin-1")),
            mimetype="text/plain",
            as_attachment=True,
            download_name=filename,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/conciliacion/rendicion", methods=["POST"])
@auth.api_login_required(role="admin")
def api_conciliar_rendicion():
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "Debe adjuntar el archivo de rendición (.lis)"}), 400
    contenido = archivo.read().decode("latin-1", errors="replace")
    confirmar = request.form.get("confirmar") == "1"
    try:
        resultado = macro.conciliar_rendicion(contenido, confirmar_automatico=confirmar)
        auth.log_event(
            actor=g.user["username"],
            role=g.user["role"],
            accion="conciliar_rendicion",
            entidad="macro_rendicion",
            entidad_id=archivo.filename or "",
            detalle=(
                f"coincidencias={resultado['coincidencias']} "
                f"confirmados={resultado['confirmados']}"
            ),
            ip_origen=request.remote_addr,
        )
        return jsonify(resultado)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/health")
def health():
    if not getattr(app, "_db_ready", False):
        init_db()
    return jsonify({"status": "ok", "service": "ips-macro-depositos"})


def _get_allowed_deposito(dep_id: int) -> dict:
    dep = svc.obtener_deposito(dep_id)
    if g.user and g.user["role"] == "farmacia" and dep["farmacia_id"] != g.user["farmacia_id"]:
        raise ValueError("No autorizado para este depósito")
    return dep


@app.errorhandler(403)
def forbidden(_err):
    if request.path.startswith("/api/"):
        return jsonify({"error": "No autorizado"}), 403
    return render_template("403.html", user=g.user), 403


if __name__ == "__main__":
    init_db()
    app.run(debug=FLASK_ENV != "production", host="0.0.0.0", port=5000)
