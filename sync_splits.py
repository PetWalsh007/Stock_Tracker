import json
from db_con import connectcls_postgres
from market_data import get_split_data as get_splits_from_yahoo 


def get_instruments_for_yahoo(db):
    """
    Fetch splits using ticker, but store them under instrument_key (ISIN if present else ticker).
    Returns:
      [{"instrument_key": "...", "ticker": "..."}, ...]
    """
    db.cursor.execute("""
        SELECT DISTINCT
          COALESCE(isin, ticker) AS instrument_key,
          ticker
        FROM public.broker_trades
        WHERE ticker IS NOT NULL AND ticker <> ''
        ORDER BY 1;
    """)
    return [{"instrument_key": r[0], "ticker": r[1]} for r in db.cursor.fetchall()]


def insert_split(db, instrument_key: str, effective_date: str, factor: float, source_payload: dict):
    db.cursor.execute(
        """
        INSERT INTO public.corporate_actions
          (instrument_key, action_type, effective_date, factor, source, source_payload)
        VALUES
          (?, 'SPLIT', ?, ?, 'yahoo', ?::jsonb)
        ON CONFLICT (instrument_key, action_type, effective_date, factor)
        DO NOTHING;
        """,
        (instrument_key, effective_date, float(factor), json.dumps(source_payload))
    )


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

    items = get_instruments_for_yahoo(db)
    print(f"Found {len(items)} instruments with tickers")

    ok = 0
    skipped = 0

    for item in items:
        instrument_key = item["instrument_key"]
        ticker = item["ticker"]

        try:
            splits = get_splits_from_yahoo(ticker)  # IMPORTANT: call Yahoo with ticker
            if splits is None:
                splits = []
        except Exception as e:
            print(f"SKIP {instrument_key} ({ticker}): {e}")
            skipped += 1
            continue

        # splits expected: [{"date":"YYYY-MM-DD","factor":float}, ...]
        inserted_count = 0
        for s in splits:
            # Defensive: handle slightly different shapes
            effective_date = s.get("date") if isinstance(s, dict) else None
            factor = s.get("factor") if isinstance(s, dict) else None
            if not effective_date or factor is None:
                print(f"SKIP split row for {instrument_key} ({ticker}): unexpected split format: {s}")
                continue

            payload = {"ticker": ticker, **s}
            insert_split(db, instrument_key, effective_date, factor, source_payload=payload)
            inserted_count += 1

        db.conn.commit()
        print(f"{instrument_key} ({ticker}): inserted/verified {inserted_count} split rows")
        ok += 1

    db.close_connection()
    print(f"Split sync complete. ok={ok}, skipped={skipped}")


if __name__ == "__main__":
    main()
