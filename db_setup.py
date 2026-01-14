import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple

from db_con import connectcls_postgres  


# ----------------------------
# CONFIG

IMPORT_DIR = Path("./t212_exports")              # folder of CSV exports
STATE_JSON_PATH = Path("credentials/t212_import_state.json")
BROKER = "T212"

# known headers
H_ACTION = "Action"
H_TIME = "Time"
H_ISIN = "ISIN"
H_TICKER = "Ticker"
H_NAME = "Name"
H_NOTES = "Notes"
H_ID = "ID"

H_SHARES = "No. of shares"
H_PRICE = "Price / share"
H_PRICE_CCY = "Currency (Price / share)"
H_FX = "Exchange rate"
H_RESULT = "Result"
H_RESULT_CCY = "Currency (Result)"
H_TOTAL = "Total"
H_TOTAL_CCY = "Currency (Total)"
H_WHT = "Withholding tax"
H_WHT_CCY = "Currency (Withholding tax)"

# Optional fees/taxes depending on export type
H_CHARGE = "Charge amount"
H_CHARGE_CCY = "Currency (Charge amount)"
H_DEPFEE = "Deposit fee"
H_DEPFEE_CCY = "Currency (Deposit fee)"

H_SDRT = "Stamp duty reserve tax"
H_SDRT_CCY = "Currency (Stamp duty reserve tax)"

H_CCFEE = "Currency conversion fee"
H_CCFEE_CCY = "Currency (Currency conversion fee)"

H_FTT = "French transaction tax"
H_FTT_CCY = "Currency (French transaction tax)"


# ----------------------------

def parse_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_time(s: str) -> datetime:
    """
    Adjust formats if your CSV differs.
    """
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unrecognised Time format: {s!r}")


def g(row: Dict[str, Any], key: str) -> Optional[str]:
    v = row.get(key, None)
    if v is None:
        return None
    v = str(v).strip()
    return v if v != "" else None


def make_synth_key(action: str, trade_time: datetime, isin: Optional[str], ticker: Optional[str],
                   qty: Optional[float], total: Optional[float]) -> str:
    """
    Stable synthetic key when T212 ID is missing.
    """
    base = f"{action}|{trade_time.isoformat()}|{isin or ''}|{ticker or ''}|{qty or ''}|{total or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()



def ensure_schema(db):
    db.cursor.execute("""
    CREATE TABLE IF NOT EXISTS public.broker_trades (
      trade_id BIGSERIAL PRIMARY KEY,
      broker TEXT NOT NULL,
      trade_key TEXT NOT NULL,
      broker_trade_id TEXT,
      action TEXT NOT NULL,
      trade_time TIMESTAMP NOT NULL,
      isin TEXT,
      ticker TEXT,
      name TEXT,
      notes TEXT,
      quantity DOUBLE PRECISION,
      price_per_share DOUBLE PRECISION,
      price_currency TEXT,
      fx_rate DOUBLE PRECISION,
      result_value DOUBLE PRECISION,
      result_currency TEXT,
      total_value DOUBLE PRECISION,
      total_currency TEXT,
      withholding_tax_value DOUBLE PRECISION,
      withholding_tax_currency TEXT,
      charge_amount_value DOUBLE PRECISION,
      charge_amount_currency TEXT,
      deposit_fee_value DOUBLE PRECISION,
      deposit_fee_currency TEXT,
      stamp_duty_reserve_tax_value DOUBLE PRECISION,
      stamp_duty_reserve_tax_currency TEXT,
      currency_conversion_fee_value DOUBLE PRECISION,
      currency_conversion_fee_currency TEXT,
      french_transaction_tax_value DOUBLE PRECISION,
      french_transaction_tax_currency TEXT,
      raw_row JSONB,
      inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (broker, trade_key)
    );
    """)

   
    db.cursor.execute("""
    ALTER TABLE public.broker_trades
    ADD COLUMN IF NOT EXISTS source_file TEXT;
    """)  

    db.cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_broker_trades_ticker_time
    ON public.broker_trades (ticker, trade_time);
    """)
    db.cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_broker_trades_isin_time
    ON public.broker_trades (isin, trade_time);
    """)

    db.conn.commit()



def normalise_row(row: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    action = g(row, H_ACTION) or ""
    t = parse_time(row[H_TIME])

    isin = g(row, H_ISIN)
    ticker = g(row, H_TICKER)

    qty = parse_float(row.get(H_SHARES))
    total = parse_float(row.get(H_TOTAL))

    broker_trade_id = g(row, H_ID)  # T212 ID
    if broker_trade_id:
        trade_key = broker_trade_id
    else:
        trade_key = make_synth_key(action, t, isin, ticker, qty, total)

    return {
        "broker": BROKER,
        "trade_key": trade_key,
        "broker_trade_id": broker_trade_id,
        "action": action,
        "trade_time": t,

        "isin": isin,
        "ticker": ticker,
        "name": g(row, H_NAME),
        "notes": g(row, H_NOTES),

        "quantity": qty,
        "price_per_share": parse_float(row.get(H_PRICE)),
        "price_currency": g(row, H_PRICE_CCY),

        "fx_rate": parse_float(row.get(H_FX)),

        "result_value": parse_float(row.get(H_RESULT)),
        "result_currency": g(row, H_RESULT_CCY),

        "total_value": total,
        "total_currency": g(row, H_TOTAL_CCY),

        "withholding_tax_value": parse_float(row.get(H_WHT)),
        "withholding_tax_currency": g(row, H_WHT_CCY),

        "charge_amount_value": parse_float(row.get(H_CHARGE)),
        "charge_amount_currency": g(row, H_CHARGE_CCY),

        "deposit_fee_value": parse_float(row.get(H_DEPFEE)),
        "deposit_fee_currency": g(row, H_DEPFEE_CCY),

        "stamp_duty_reserve_tax_value": parse_float(row.get(H_SDRT)),
        "stamp_duty_reserve_tax_currency": g(row, H_SDRT_CCY),

        "currency_conversion_fee_value": parse_float(row.get(H_CCFEE)),
        "currency_conversion_fee_currency": g(row, H_CCFEE_CCY),

        "french_transaction_tax_value": parse_float(row.get(H_FTT)),
        "french_transaction_tax_currency": g(row, H_FTT_CCY),

        "raw_row": row,
        "source_file": source_file,   # <-- THIS fixes your KeyError
    }


# ----------------------------
# INSERT (DEDUPED)
# ----------------------------
def insert_batch(db, batch):
    sql = """
    INSERT INTO broker_trades (
      broker, trade_key, broker_trade_id,
      action, trade_time,
      isin, ticker, name, notes,
      quantity, price_per_share, price_currency,
      fx_rate,
      result_value, result_currency,
      total_value, total_currency,
      withholding_tax_value, withholding_tax_currency,
      charge_amount_value, charge_amount_currency,
      deposit_fee_value, deposit_fee_currency,
      stamp_duty_reserve_tax_value, stamp_duty_reserve_tax_currency,
      currency_conversion_fee_value, currency_conversion_fee_currency,
      french_transaction_tax_value, french_transaction_tax_currency,
      raw_row, source_file
    )
    VALUES (
      ?, ?, ?,
      ?, ?,
      ?, ?, ?, ?,
      ?, ?, ?,
      ?,
      ?, ?,
      ?, ?,
      ?, ?,
      ?, ?,
      ?, ?,
      ?, ?,
      ?, ?,
      ?, ?,
      CAST(? AS TEXT)::jsonb, ?
    )
    ON CONFLICT (broker, trade_key) DO NOTHING;
    """

    inserted_est = 0

    for r in batch:
        raw_json = json.dumps(r["raw_row"], ensure_ascii=False)

        params = (
            r["broker"], r["trade_key"], r["broker_trade_id"],
            r["action"], r["trade_time"],
            r["isin"], r["ticker"], r["name"], r["notes"],
            r["quantity"], r["price_per_share"], r["price_currency"],
            r["fx_rate"],
            r["result_value"], r["result_currency"],
            r["total_value"], r["total_currency"],
            r["withholding_tax_value"], r["withholding_tax_currency"],
            r["charge_amount_value"], r["charge_amount_currency"],
            r["deposit_fee_value"], r["deposit_fee_currency"],
            r["stamp_duty_reserve_tax_value"], r["stamp_duty_reserve_tax_currency"],
            r["currency_conversion_fee_value"], r["currency_conversion_fee_currency"],
            r["french_transaction_tax_value"], r["french_transaction_tax_currency"],
            raw_json, r["source_file"],
        )

        db.cursor.execute(sql, params)
        if db.cursor.rowcount and db.cursor.rowcount > 0:
            inserted_est += db.cursor.rowcount

    db.conn.commit()
    return len(batch), inserted_est




def load_state() -> Dict[str, Any]:
    if STATE_JSON_PATH.exists():
        return json.loads(STATE_JSON_PATH.read_text(encoding="utf-8"))
    return {
        "files_processed": [],
        "max_trade_time_seen": None,
        "total_rows_seen": 0,
        "total_rows_inserted_est": 0
    }


def save_state(state: Dict[str, Any]) -> None:
    STATE_JSON_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# MAIN

def main():
    # pull db vars from file 
    with open("credentials/db_config.json", "r", encoding="utf-8") as f:
        db_config = json.load(f)

    db = connectcls_postgres(
        driver_name="PostgreSQL Unicode",  # adjust if needed
        server_name=db_config["server_name"],
        db_name=db_config["db_name"],
        connection_username=db_config["connection_username"],
        connection_password=db_config["connection_password"],
        port=5432,
    )

    if db.con_err:
        print("DB connection error:", db.con_err)
        return

    ensure_schema(db)



    state = load_state()
    files = sorted(IMPORT_DIR.glob("*.csv"))
    if not files:
        print(f"No CSV files found in: {IMPORT_DIR.resolve()}")
        return

    max_time_seen: Optional[datetime] = None

    for fp in files:
        
        if fp.name in state.get("files_processed", []):
            continue

        try:
            with fp.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)

                batch = []
                for row in reader:
                    nr = normalise_row(row, source_file=fp.name)  # <-- nr exists again
                    batch.append(nr)

                    t = nr["trade_time"]
                    if max_time_seen is None or t > max_time_seen:
                        max_time_seen = t

            attempted, inserted_est = insert_batch(db, batch)

            state["total_rows_seen"] = int(state.get("total_rows_seen", 0)) + attempted
            state["total_rows_inserted_est"] = int(state.get("total_rows_inserted_est", 0)) + inserted_est
            state.setdefault("files_processed", []).append(fp.name)

            print(f"{fp.name}: attempted={attempted}, inserted_est={inserted_est}")

        except Exception as e:
            print(f"FAILED {fp.name}: {e}")

    if max_time_seen:
        state["max_trade_time_seen"] = max_time_seen.strftime("%Y-%m-%d %H:%M:%S")

    save_state(state)
    print("DONE. State:", state)

    db.close_connection()


if __name__ == "__main__":

    main()
