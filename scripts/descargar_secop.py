"""
Descarga SECOP II - Contratos Electrónicos (datos.gov.co, dataset jbjy-vk9h)
Filtro: tipo_de_contrato = 'Prestación de servicios' y proveedor persona natural (cédula de ciudadanía).
Periodo: fecha_de_firma desde ANIO_INI hasta hoy. Descarga mes a mes (reanudable).

Privacidad: la cédula se reemplaza por un hash SHA-256 con sal secreta (id_persona).
Se eliminan nombres, cuentas bancarias y documentos de supervisores/ordenadores.

Uso:  python descargar_secop.py            -> descarga lo que falte
      python descargar_secop.py --unir     -> une los meses en data/processed/
"""
import os, sys, time, secrets, hashlib, logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
PROC = os.path.join(BASE, "data", "processed")
LOG = os.path.join(BASE, "logs", "descarga.log")
SAL_PATH = os.path.join(BASE, ".sal_NO_COMPARTIR.txt")

URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN")  # opcional
ANIO_INI = 2020
PAGINA = 50_000
HILOS = 3

COLUMNAS = [
    "id_contrato", "proceso_de_compra", "documento_proveedor",
    "g_nero_representante_legal", "nacionalidad_representante_legal",
    "nombre_entidad", "nit_entidad", "codigo_entidad", "departamento", "ciudad",
    "orden", "sector", "rama", "entidad_centralizada",
    "modalidad_de_contratacion", "justificacion_modalidad_de",
    "codigo_de_categoria_principal", "estado_contrato",
    "fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato",
    "valor_del_contrato", "valor_pagado", "dias_adicionados",
    "el_contrato_puede_ser_prorrogado", "origen_de_los_recursos", "destino_gasto",
    "espostconflicto", "objeto_del_contrato", "ultima_actualizacion",
]
FILTRO = "tipo_de_contrato='Prestación de servicios' AND tipodocproveedor='Cédula de Ciudadanía'"

os.makedirs(RAW, exist_ok=True); os.makedirs(PROC, exist_ok=True)
logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger()


def sal():
    if not os.path.exists(SAL_PATH):
        with open(SAL_PATH, "w") as f:
            f.write(secrets.token_hex(32))
    return open(SAL_PATH).read().strip()


SAL = sal()


def hash_doc(x):
    return hashlib.sha256((SAL + str(x).strip()).encode()).hexdigest()[:16]


def meses():
    hoy = date.today()
    y, m = ANIO_INI, 1
    while (y, m) <= (hoy.year, hoy.month):
        ini = date(y, m, 1)
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        yield ini, date(y2, m2, 1)
        y, m = y2, m2


def pedir(params, intentos=6):
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    for i in range(intentos):
        try:
            r = requests.get(URL, params=params, headers=headers, timeout=300)
            if r.status_code == 200:
                return r.json()
            log.warning("HTTP %s: %s", r.status_code, r.text[:200])
        except Exception as e:
            log.warning("error red: %s", e)
        time.sleep(10 * (i + 1))
    raise RuntimeError("falló tras reintentos")


def bajar_mes(ini, fin):
    out = os.path.join(RAW, f"secop_ps_{ini:%Y-%m}.parquet")
    if os.path.exists(out):
        return ini, "ya existía"
    where = f"{FILTRO} AND fecha_de_firma >= '{ini}' AND fecha_de_firma < '{fin}'"
    filas, off = [], 0
    while True:
        lote = pedir({"$select": ",".join(COLUMNAS), "$where": where,
                      "$order": "id_contrato", "$limit": PAGINA, "$offset": off})
        filas.extend(lote); off += len(lote)
        if len(lote) < PAGINA:
            break
    df = pd.DataFrame(filas, columns=COLUMNAS)
    df.insert(1, "id_persona", df["documento_proveedor"].map(hash_doc))
    df = df.drop(columns="documento_proveedor")
    tmp = out + ".tmp"
    df.to_parquet(tmp, index=False)
    os.replace(tmp, out)
    log.info("%s -> %d filas", f"{ini:%Y-%m}", len(df))
    return ini, len(df)


def descargar():
    pendientes = list(meses())
    log.info("inicio: %d meses", len(pendientes))
    with ThreadPoolExecutor(HILOS) as ex:
        futs = [ex.submit(bajar_mes, a, b) for a, b in pendientes]
        for f in as_completed(futs):
            try:
                ini, n = f.result(); print(f"{ini:%Y-%m}: {n}", flush=True)
            except Exception as e:
                log.error("mes falló: %s", e); print("ERROR", e, flush=True)
    log.info("fin descarga")


def limpiar_tipos(df):
    for c in ["fecha_de_firma", "fecha_de_inicio_del_contrato", "fecha_de_fin_del_contrato", "ultima_actualizacion"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["valor_del_contrato", "valor_pagado", "dias_adicionados"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def unir():
    """Une los meses en un parquet por año (reanudable, bajo consumo de RAM).
    Para cargar todo:  pd.read_parquet("data/processed")"""
    archivos = sorted(f for f in os.listdir(RAW) if f.endswith(".parquet"))
    anios = sorted({f[9:13] for f in archivos})
    for anio in anios:
        out = os.path.join(PROC, f"secop_ps_{anio}.parquet")
        if os.path.exists(out):
            continue
        df = pd.concat([pd.read_parquet(os.path.join(RAW, f))
                        for f in archivos if f[9:13] == anio], ignore_index=True)
        df = limpiar_tipos(df).drop_duplicates("id_contrato")
        df.to_parquet(out + ".tmp", index=False, compression="zstd")
        os.replace(out + ".tmp", out)
        print(anio, len(df), flush=True)


if __name__ == "__main__":
    unir() if "--unir" in sys.argv else descargar()
