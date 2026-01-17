from __future__ import annotations

import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from db_con import connectcls_postgres


BUY_ACTIONS = ("Market buy", "Limit buy")
SELL_ACTIONS = ("Market sell", "Limit sell")


def coalesce_instrument_key(isin: Optional[str], ticker: Optional[str]) -> str:
    isin = (isin or "").strip()
    ticker = (ticker or "").strip()
    return isin if isin else ticker


def fetch_trades_for_lots(db) -> List[Dict[str, Any]]:
    """
    Pull all BUY rows that should create lots.
    """
    db.cursor.execute(
        """
        SELECT trade_id, trade_time, isin, ticker, quantity, total_value, total_currency, action
        FROM public.broker_trades
        WHERE action IN (?, ?)
          AND total_currency = 'EUR'
          AND quantity IS NOT NULL
          AND quantity <> 0
        ORDER BY trade_time ASC, trade_id ASC;
        """,
        BUY_ACTIONS
    )
    rows = db.cursor.fetchall()
    out = []
    for r in rows:
        out.append({
            "trade_id": int(r[0]),
            "trade_time": r[1],
            "isin": r[2],
            "ticker": r[3],
            "quantity": float(r[4]),
            "total_value": float(r[5]),
            "total_currency": r[6],
            "action": r[7],
        })
    return out


def fetch_trades_for_sales(db) -> List[Dict[str, Any]]:
    """
    Pull all SELL rows that should create sales.
    """
    db.cursor.execute(
        """
        SELECT trade_id, trade_time, isin, ticker, quantity, total_value, total_currency, action
        FROM public.broker_trades
        WHERE action IN (?, ?)
          AND total_currency = 'EUR'
          AND quantity IS NOT NULL
          AND quantity <> 0
        ORDER BY trade_time ASC, trade_id ASC;
        """,
        SELL_ACTIONS
    )
    rows = db.cursor.fetchall()
    out = []
    for r in rows:
        out.append({
            "trade_id": int(r[0]),
            "trade_time": r[1],
            "isin": r[2],
            "ticker": r[3],
            "quantity": float(r[4]),
            "total_value": float(r[5]),
            "total_currency": r[6],
            "action": r[7],
        })
    return out


def insert_lot_from_trade(db, t: Dict[str, Any]) -> bool:
    """
    Inserts one lot row. Returns True if inserted, False if already existed.
    Requires unique constraint/index on lots.buy_trade_id.
    """
    instrument_key = coalesce_instrument_key(t["isin"], t["ticker"])
    qty = t["quantity"]
    total_cost = t["total_value"]
    cost_per_share = (total_cost / qty) if qty else 0.0

    db.cursor.execute(
        """
        INSERT INTO public.lots (
          instrument_key,
          buy_trade_id,
          buy_time,
          original_qty,
          total_cost_eur,
          split_factor,
          adjusted_qty,
          qty_sold,
          qty_left,
          cost_left_eur,
          adjusted_cost_per_share_eur,
          fully_sold,
          lot_source,
          created_at
        )
        VALUES (?, ?, ?, ?, ?, 1.0, ?, 0.0, ?, ?, ?, FALSE, 'BUY', NOW())
        ON CONFLICT (buy_trade_id) DO NOTHING;
        """,
        (
            instrument_key,
            t["trade_id"],
            t["trade_time"],
            qty,
            total_cost,
            qty,
            qty,
            total_cost,
            cost_per_share,
        )
    )

   
    return (db.cursor.rowcount or 0) > 0


def insert_sale_from_trade(db, t: Dict[str, Any]) -> bool:
    """
    Inserts one sale row. Returns True if inserted, False if already existed.
    Requires unique constraint/index on sales.sell_trade_id.
    """
    instrument_key = coalesce_instrument_key(t["isin"], t["ticker"])
    qty = t["quantity"]
    proceeds = t["total_value"]

    db.cursor.execute(
        """
        INSERT INTO public.sales (
          instrument_key,
          sell_trade_id,
          sell_time,
          quantity_sold,
          proceeds_eur,
          processed,
          created_at
        )
        VALUES (?, ?, ?, ?, ?, FALSE, NOW())
        ON CONFLICT (sell_trade_id) DO NOTHING;
        """,
        (
            instrument_key,
            t["trade_id"],
            t["trade_time"],
            qty,
            proceeds,
        )
    )

    return (db.cursor.rowcount or 0) > 0


def populate_lots(db) -> Dict[str, int]:
    trades = fetch_trades_for_lots(db)
    inserted = 0
    seen = 0

    for t in trades:
        seen += 1
        if insert_lot_from_trade(db, t):
            inserted += 1

    return {"lots_seen": seen, "lots_inserted": inserted}


def populate_sales(db) -> Dict[str, int]:
    trades = fetch_trades_for_sales(db)
    inserted = 0
    seen = 0

    for t in trades:
        seen += 1
        if insert_sale_from_trade(db, t):
            inserted += 1

    return {"sales_seen": seen, "sales_inserted": inserted}


def main():
    with open("credentials/db_config.json", "r", encoding="utf-8") as f:
        db_config = json.load(f)

    db = connectcls_postgres(
        driver_name=db_config.get("driver_name", "PostgreSQL Unicode"),
        server_name=db_config["server_name"],
        db_name=db_config["db_name"],
        connection_username=db_config["connection_username"],
        connection_password=db_config["connection_password"],
        port=db_config.get("port", 5432),
    )
    if db.con_err:
        print("DB connection error:", db.con_err)
        return

    db.conn.autocommit = False
    try:
        lots_stats = populate_lots(db)
        sales_stats = populate_sales(db)
        db.conn.commit()
    except Exception:
        db.conn.rollback()
        raise
    finally:
        db.conn.autocommit = True
        db.close_connection()

    print("Populate complete:", {**lots_stats, **sales_stats})


if __name__ == "__main__":
    main()
