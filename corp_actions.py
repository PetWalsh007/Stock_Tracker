from db_con import connectcls_postgres  
import json

DDL_STATEMENTS = [
    # corporate_actions (splits from Yahoo)
    """
    CREATE TABLE IF NOT EXISTS public.corporate_actions (
      action_id BIGSERIAL PRIMARY KEY,
      instrument_key TEXT NOT NULL,
      action_type TEXT NOT NULL,          -- 'SPLIT'
      effective_date DATE NOT NULL,
      factor DOUBLE PRECISION NOT NULL,   -- 4.0, 10.0, etc
      source TEXT,                        -- 'yahoo'
      source_payload JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (instrument_key, action_type, effective_date, factor)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_corp_actions_instr_date
      ON public.corporate_actions (instrument_key, effective_date);
    """,

    # sale_lot_usage unique constraint
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_sale_lot_usage_sale_lot
      ON public.sale_lot_usage (sale_id, lot_id);
    """,

    # (re)create normalized 
    """
    CREATE OR REPLACE VIEW public.v_trades_norm AS
    SELECT
      trade_id,
      broker,
      trade_key,
      broker_trade_id,
      trade_time,
      action,
      COALESCE(isin, ticker) AS instrument_key,
      isin,
      ticker,
      name,
      notes,
      quantity,
      total_value,
      total_currency,
      fx_rate,
      (action IN ('Market buy','Limit buy')) AS is_buy,
      (action IN ('Market sell','Limit sell')) AS is_sell,
      CASE WHEN action IN ('Market buy','Limit buy') THEN total_value ELSE NULL END AS buy_cost_eur,
      CASE WHEN action IN ('Market sell','Limit sell') THEN total_value ELSE NULL END AS sell_proceeds_eur
    FROM public.broker_trades
    WHERE total_currency = 'EUR';
    """
]


def main():
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

    for stmt in DDL_STATEMENTS:
        db.cursor.execute(stmt)

    db.conn.commit()
    print("DB setup complete (corporate_actions + view ensured).")
    db.close_connection()


if __name__ == "__main__":
    main()
