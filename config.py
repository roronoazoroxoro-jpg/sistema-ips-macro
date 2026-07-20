import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "ips_depositos.db")

# Datos del convenio IPS — Banco Macro (configurables por variable de entorno)
BANCO_MACRO = {
    "nombre": "Banco Macro S.A.",
    "cbu_destino": os.environ.get("IPS_MACRO_CBU", "2850590940090418135201"),
    "alias": os.environ.get("IPS_MACRO_ALIAS", "IPS.MISIONES.DEP"),
    "titular": os.environ.get("IPS_MACRO_TITULAR", "Instituto de Previsión Social - Misiones"),
    "cuit": os.environ.get("IPS_MACRO_CUIT", "30-99999999-0"),
    "cuenta_recaudadora": os.environ.get("IPS_MACRO_CUENTA", "8030585583533"),
    "grupo_deudas": os.environ.get("IPS_MACRO_GRUPO", "MUNISAL"),
    "codigo_servicio": os.environ.get("IPS_MACRO_SERVICIO", "5170"),
    "codigo_moneda": os.environ.get("IPS_MACRO_MONEDA", "80"),
    "modalidad_publicacion": os.environ.get("IPS_MACRO_MODALIDAD", "deuda_publicada"),
    "numero_convenio": os.environ.get("IPS_MACRO_CONVENIO", "05170000005"),
    "concepto_default": "Depósito caja farmacia IPS",
    "mesa_ayuda": os.environ.get("IPS_MACRO_MESA_AYUDA", "0-810-555-2112 opción 7"),
    "email_recaudaciones": os.environ.get("IPS_MACRO_EMAIL", "recaudacionesmda@macro.com.ar"),
    "sftp_carpeta_envio": os.environ.get("IPS_SFTP_ENVIO", r"C:\Deuda_Publicada\Envio"),
    "sftp_carpeta_recepcion": os.environ.get("IPS_SFTP_RECEPCION", r"C:\Deuda_Publicada\Recepcion"),
}

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "cambiar-en-produccion-ips-2026")
FLASK_ENV = os.environ.get("FLASK_ENV", "production")
DEFAULT_ADMIN_USER = os.environ.get("IPS_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("IPS_ADMIN_PASSWORD", "admin1234")
DEFAULT_FARMACIA_PASSWORD = os.environ.get("IPS_FARMACIA_PASSWORD", "farmacia1234")
MAX_MONTO_DEPOSITO = float(os.environ.get("IPS_MAX_MONTO_DEPOSITO", "50000000"))
SESSION_TIMEOUT_MINUTES = int(os.environ.get("IPS_SESSION_TIMEOUT_MINUTES", "120"))

METODOS_DEPOSITO = {
    "tas_macro": "Terminal TAS (autoservicio)",
    "ventanilla_macro": "Ventanilla sucursal",
    "transferencia_macro": "Transferencia cuenta Macro",
    "home_banking": "Home Banking Macro",
}
