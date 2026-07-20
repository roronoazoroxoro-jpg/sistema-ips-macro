# Sistema IPS — Depósito de cajas de farmacias en Banco Macro



Aplicación web para registrar el cierre de caja de farmacias adheridas al **IPS Misiones**, generar el **archivo de recaudación** (`DeudaPubBancoMacro`) para Banco Macro, importar el **archivo de rendición** (`DPPPdat_*.lis`) y conciliar pagos con comprobante digital (código único, referencia y QR).



## Nueva forma de depósito (sin boletas manuales)



| Antes (típico) | Con este sistema |

|----------------|------------------|

| Boletas y depósitos manuales en ventanilla | Archivo **DeudaPub** enviado al banco |

| Sin trazabilidad por farmacia | CUIT + monto por registro `D5170` |

| Conciliación manual | Importación de **DPPPdat** y cruce automático |

| Sin seguimiento centralizado | Panel IPS con pendientes / confirmados |



## Flujo operativo



1. **Farmacia** — Registra cierre de caja en `/farmacia` (periodo, recetas, monto).

2. **IPS** — Genera archivo de recaudación desde el panel (`DeudaPubBancoMacro_YYYYMMDD.txt`).

3. **Banco Macro** — Recibe el archivo y habilita el cobro por módulo de recaudación / transferencia.

4. **Farmacia** — Realiza el pago en Macro (según comprobante con QR y referencia).

5. **IPS** — Importa el archivo de rendición `.lis` y concilia por CUIT + monto.

6. **IPS** — Confirma depósitos (automático o manual desde el panel).



## Documentación de referencia (6 archivos en el proyecto)

| # | Archivo | Contenido |
|---|---------|-----------|
| 1 | `DeudaPubBancoMacro_*.txt` | Ejemplo real de archivo de **recaudación** enviado al banco |
| 2 | `DPPPdat_*.lis` | Ejemplo real de archivo de **rendición** devuelto por Macro |
| 3 | `Diseño de Registro Deuda Publicada...EM590 (2).xls` | Especificación oficial de campos y posiciones (775 caracteres) |
| 4 | `Archivo de recaudacion de Ejemplo.xlsm` | Herramienta Excel de Macro para generar y recibir archivos |
| 5 | `BM50464 - ...Recaudaciones.pdf` | Ficha de producto: beneficios, modalidades, WinSCP/SFTP |
| 6 | `Instructivo TAI.pdf` | Depósito en terminal TAS (convenio + selección de registro) |

El sistema genera recaudación según diseño EM590 y concilia rendiciones `DPPPdat`.



## Requisitos



- Python 3.10+

- Windows / Linux



## Instalación



```powershell

cd "c:\Users\mcneumaticos\Desktop\sistema ips"

python -m venv venv

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

```



## Configuración (producción)



Variables de entorno opcionales:



| Variable | Descripción |

|----------|-------------|

| `IPS_MACRO_CBU` | CBU real de la cuenta IPS en Macro |

| `IPS_MACRO_ALIAS` | Alias de la cuenta |

| `IPS_MACRO_TITULAR` | Titular de la cuenta |

| `IPS_MACRO_CUIT` | CUIT del IPS |

| `IPS_MACRO_CUENTA` | Cuenta recaudadora Macro (ej. `8030585583533`) |

| `FLASK_SECRET_KEY` | Clave secreta Flask |



Los valores por defecto en `config.py` son de **demostración** — reemplazarlos con los datos del convenio oficial.



## Ejecución (desarrollo)



```powershell

python app.py

```



Abrir en el navegador: **http://localhost:5000**



## Ejecución (producción básica)



```powershell

python wsgi.py

```



Usa Waitress en lugar del servidor de desarrollo de Flask.



- **/** — Inicio y explicación del flujo  

- **/farmacia** — Alta de depósito por la farmacia  

- **/ips** — Panel interno: recaudación, rendición y confirmación  

- **/comprobante/&lt;id&gt;** — Comprobante imprimible con QR  

- **/login** — Acceso autenticado por rol  



## API REST



| Método | Ruta | Descripción |

|--------|------|-------------|

| GET | `/api/farmacias` | Listado de farmacias |

| GET/POST | `/api/depositos` | Listar / crear depósito |

| GET | `/api/depositos/<id>` | Detalle |

| POST | `/api/depositos/<id>/confirmar` | Confirmar (IPS) |

| POST | `/api/depositos/<id>/cancelar` | Cancelar pendiente |

| GET | `/api/depositos/<id>/qr.png` | Imagen QR |

| GET | `/api/depositos/export.csv` | Exportación CSV (admin) |

| GET | `/api/depositos/export.recaudacion` | Archivo DeudaPub (admin) |

| POST | `/api/conciliacion/rendicion` | Importar DPPPdat y conciliar (admin) |

| GET | `/health` | Health check |



## Seguridad y perfiles



- Sesiones con timeout configurable (`IPS_SESSION_TIMEOUT_MINUTES`)

- Acceso por rol:

  - `admin`: panel IPS, exportar recaudación, importar rendición, confirmar/cancelar

  - `farmacia`: crear y consultar solo sus propios depósitos

- Auditoría de eventos: login, logout, creación, exportación, conciliación y confirmación



Usuarios demo iniciales:



- `admin` / `admin1234`

- farmacias: `f001`, `f002`, etc. / `farmacia1234`



## Datos



SQLite en `data/ips_depositos.db`. Incluye 5 farmacias de ejemplo con CUIT; en producción cargar el padrón real desde Farmacias Contratadas (Junín 177, Posadas).



## Pendientes recomendados (fase 2)



- Validación de formato con especificación oficial actualizada de Macro

- Carga masiva de farmacias desde padrón IPS

- Firma digital del comprobante y sellado de tiempo

