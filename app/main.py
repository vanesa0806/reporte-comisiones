#!/usr/bin/env python3
"""
Cálculo de comisiones - Python 3.11
-----------------------------------
Flujo:
1.  Determina el mes actual            → “periodo” (p. ej. 202505)
2.  Busca el CSV de ese periodo        → ComisionEmpleados_V1_<periodo>.csv
3.  Lee empleados desde PostgreSQL
4.  Une CSV + BD por «empleado_id»
5.  Calcula la comisión de cada fila
6.  Añade la columna «periodo» y exporta a Excel
7.  Envía el Excel por e-mail
"""

from datetime import date            # Para obtener el mes actual
from pathlib import Path             # Manipulación de rutas
from decimal import Decimal          # Evita errores de redondeo monetario
import json, os, sys, smtplib        # Varios módulos estándar
import pandas as pd                  # Librería de análisis de datos
import psycopg2                      # Conector PostgreSQL
from typing import Union

from email.mime.multipart import MIMEMultipart  # Piezas para armar un correo
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from email.header         import Header

# ─────────────────────────  1. Cargar configuración  ───────────────────────── #
# Lee credenciales y rutas desde «config.json» (pasa la ruta por $CONFIG_FILE
# o deja que busque un config.json junto al script).

def load_config(path: Union[str, Path, None] = None) -> dict:
    path = Path(path) if path else Path(__file__).with_name("config.json")
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} no encontrado.")
    return json.loads(path.read_text(encoding="utf-8"))

CFG       = load_config(os.getenv("CONFIG_FILE"))
DB_CFG    = CFG["db"]         # host, user, password…
SMTP_CFG  = CFG["smtp"]       # servidor de correo
PATHS     = CFG["paths"]      # carpetas y nombres de archivos
REPORT    = CFG["report"]     # asunto, destinatario, cuerpo

# ────────────────────────  2. Función para enviar correo  ──────────────────── #
def send_mail(to: str, subj: str, html: str, attachment: Path) -> None:
    msg = MIMEMultipart()
    msg["From"], msg["To"] = SMTP_CFG["sender_email"], to
    msg["Subject"] = str(Header(subj, "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with open(attachment, "rb") as fh:          # Adjuntar archivo
        part = MIMEBase("application", "octet-stream")
        part.set_payload(fh.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f'attachment; filename="{attachment.name}"')
    msg.attach(part)
    
    with smtplib.SMTP(SMTP_CFG["server"], SMTP_CFG["port"]) as smtp:
        if SMTP_CFG.get("use_tls") or (SMTP_CFG.get("port") == 587):
            smtp.starttls()
        user = SMTP_CFG.get("user")
        password = SMTP_CFG.get("password")
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)

# ─────────────────────────── 3. Script principal  ──────────────────────────── #
def main() -> None:
    # 3.1  Calcular el período actual en formato AAAAMM
    periodo = date.today().strftime("%Y%m")
    csv_dir = Path(PATHS.get("csv_dir", "."))             # carpeta de CSV
    csv_file = csv_dir / f"ComisionEmpleados_V1_{periodo}.csv"

    # 3.2  Si no hay CSV para el mes, abortar sin error
    if not csv_file.exists():
        print(f"> No hay comisiones para {periodo}. Fin.")
        sys.exit(0)

    # 3.3  Leer CSV en un DataFrame
    csv_df = pd.read_csv(csv_file, sep=";")

    # 3.4  Leer tabla «rrhh.empleado» desde PostgreSQL
    with psycopg2.connect(**DB_CFG) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM rrhh.empleado;")
        db_df = pd.DataFrame(cur.fetchall(),
                             columns=[c[0] for c in cur.description])

    # 3.5  Unir CSV + BD (solo filas que coinciden en empleado_id)
    merged = csv_df.merge(db_df, on="empleado_id")

    # 3.6  Asegurarse de que salario/comisiones son numéricos
    num_cols = ["mnt_salario", "Comisión", "mnt_tope_comision"]
    merged[num_cols] = (merged[num_cols]
                        .apply(pd.to_numeric, errors="coerce")
                        .fillna(0))

    # 3.7  Calcular comisión (10 % del salario + comisión_csv, sin pasar tope)
    merged["comision_calculada"] = merged.apply(
        lambda r: min(
            Decimal(r.mnt_salario) * Decimal("0.10") + Decimal(r.Comisión),
            Decimal(r.mnt_tope_comision)
        ),
        axis=1
    )
   
    # 3.8  Guardar resultado en Excel
    excel_out = Path(PATHS["excel"])
    merged.to_excel(excel_out, index=False, engine="openpyxl")

    # 3.9  Enviar el Excel por correo
    send_mail(REPORT["to"], REPORT["subject"], REPORT["body_html"], excel_out)

if __name__ == "__main__":
    main()
