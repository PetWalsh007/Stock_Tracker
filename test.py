"""
Simple Trading212 Postgres Viewer (Tkinter) for testing purposes.
- Connects to Postgres
- Runs a SELECT with optional ticker filter and limit
- Shows results in a Treeview

Requires:
  pip install psycopg[binary]
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import psycopg
from psycopg.rows import dict_row


# =========================
# 1) TABLE CONFIG
# =========================
COLUMNS = [
    ("time", "Time"),
    ("action_type", "Type"),
    ("order_type", "Order"),
    ("ticker", "Ticker"),
    ("shares", "Shares"),
    ("price_per_share", "Price"),
    ("price_currency", "Px Ccy"),
    ("exchange_rate", "FX"),
    ("total", "Total"),
    ("total_currency", "Tot Ccy"),
    ("id", "ID"),
]

# If your DB column names differ, map UI keys -> DB column names here.
# Example: if db column is "price" but UI expects "price_per_share": {"price_per_share": "price"}
DB_COLUMNS_MAP = {k: k for k, _ in COLUMNS}


def fmt_dt(x):
    if isinstance(x, datetime):
        return x.strftime("%Y-%m-%d %H:%M:%S")
    return "" if x is None else str(x)

def fmt_num(x, dp=6):
    if x is None:
        return ""
    try:
        return f"{float(x):.{dp}f}"
    except Exception:
        return str(x)

def safe_str(x):
    return "" if x is None else str(x)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trading212 Postgres Viewer (Buys/Sells only)")
        self.geometry("1280x720")

        self.status = tk.StringVar(value="Enter DB details and click Connect + Load.")
        self.loaded_rows: list[dict] = []

        # Connection fields
        self.pg_host = tk.StringVar(value="localhost")
        self.pg_port = tk.StringVar(value="5432")
        self.pg_db   = tk.StringVar(value="postgres")
        self.pg_user = tk.StringVar(value="postgres")
        self.pg_pass = tk.StringVar(value="")

        # Source table fields
        self.pg_schema = tk.StringVar(value="public")
        self.pg_table  = tk.StringVar(value="trading212_trades")

        # Filters
        self.ticker_filter = tk.StringVar(value="")  # empty = all
        self.row_limit = tk.IntVar(value=500)

        self._build_ui()

    def _build_ui(self):
        # --- Connection row
        conn = ttk.LabelFrame(self, text="Postgres Connection", padding=10)
        conn.pack(fill="x", padx=10, pady=(10, 6))

        def add_labeled(entry_parent, label, var, width=16, show=None):
            ttk.Label(entry_parent, text=label).pack(side="left", padx=(0, 6))
            ttk.Entry(entry_parent, textvariable=var, width=width, show=show).pack(side="left", padx=(0, 12))

        add_labeled(conn, "Host", self.pg_host, width=16)
        add_labeled(conn, "Port", self.pg_port, width=6)
        add_labeled(conn, "DB", self.pg_db, width=16)
        add_labeled(conn, "User", self.pg_user, width=14)
        add_labeled(conn, "Password", self.pg_pass, width=14, show="*")

        ttk.Button(conn, text="Connect + Load", command=self.load_from_db).pack(side="left", padx=8)

        # --- Query options
        opts = ttk.LabelFrame(self, text="Query Options", padding=10)
        opts.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(opts, text="Schema").pack(side="left")
        ttk.Entry(opts, textvariable=self.pg_schema, width=12).pack(side="left", padx=8)

        ttk.Label(opts, text="Table").pack(side="left")
        ttk.Entry(opts, textvariable=self.pg_table, width=22).pack(side="left", padx=8)

        ttk.Label(opts, text="Ticker filter (optional)").pack(side="left", padx=(18, 0))
        ttk.Entry(opts, textvariable=self.ticker_filter, width=12).pack(side="left", padx=8)

        ttk.Label(opts, text="Limit").pack(side="left", padx=(18, 0))
        ttk.Entry(opts, textvariable=self.row_limit, width=8).pack(side="left", padx=8)

        ttk.Button(opts, text="Reload", command=self.load_from_db).pack(side="left", padx=8)

        self.stats_label = ttk.Label(opts, text="")
        self.stats_label.pack(side="left", padx=16)

        # --- Table
        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=[k for k, _ in COLUMNS],
            show="headings",
            height=20
        )

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        for key, title in COLUMNS:
            self.tree.heading(key, text=title)
            if key in {"time"}:
                self.tree.column(key, width=160, anchor="w")
            elif key in {"id"}:
                self.tree.column(key, width=140, anchor="w")
            elif key in {"ticker", "action_type", "order_type", "price_currency", "total_currency"}:
                self.tree.column(key, width=90, anchor="center")
            else:
                self.tree.column(key, width=110, anchor="e")

        # --- Status
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")

    def _dsn(self) -> str:
        # psycopg supports a conninfo string; keep it simple.
        # If password is empty, it will still try (peer/trust/etc. depending on your setup).
        return (
            f"host={self.pg_host.get().strip()} "
            f"port={self.pg_port.get().strip()} "
            f"dbname={self.pg_db.get().strip()} "
            f"user={self.pg_user.get().strip()} "
            f"password={self.pg_pass.get()}"
        )

    def load_from_db(self):
        schema = self.pg_schema.get().strip() or "public"
        table = self.pg_table.get().strip()
        if not table:
            messagebox.showwarning("Missing table", "Please enter a table name.")
            return

        try:
            limit = int(self.row_limit.get())
            if limit <= 0:
                raise ValueError()
        except Exception:
            messagebox.showwarning("Bad limit", "Limit must be a positive integer.")
            return

        ticker = self.ticker_filter.get().strip().upper()

        # Build SELECT list safely (identifiers must be composed, not parametrized).
        # We'll keep it simple: validate identifiers are basic [a-zA-Z0-9_].
        def is_safe_ident(s: str) -> bool:
            return s.replace("_", "").isalnum()

        if not is_safe_ident(schema) or not is_safe_ident(table):
            messagebox.showerror("Unsafe identifier", "Schema/table must be alphanumeric/underscore only.")
            return

        db_cols = [DB_COLUMNS_MAP[k] for k, _ in COLUMNS]
        for c in db_cols:
            if not is_safe_ident(c):
                messagebox.showerror("Unsafe column", f"Column name not safe: {c}")
                return

        select_cols_sql = ", ".join([f'"{c}"' for c in db_cols])
        from_sql = f'"{schema}"."{table}"'

        where_sql = ""
        params = {}

        # Optional ticker filter
        if ticker:
            where_sql = 'WHERE UPPER("ticker") = %(ticker)s'
            params["ticker"] = ticker

        # Optional: only buys/sells (matches your original)
        # If you want *everything*, delete this block.
        if where_sql:
            where_sql += ' AND "action_type" IN (\'BUY\', \'SELL\')'
        else:
            where_sql = 'WHERE "action_type" IN (\'BUY\', \'SELL\')'

        sql = f"""
            SELECT {select_cols_sql}
            FROM {from_sql}
            {where_sql}
            ORDER BY "time" DESC
            LIMIT %(limit)s
        """
        params["limit"] = limit

        try:
            with psycopg.connect(self._dsn(), row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
        except Exception as e:
            messagebox.showerror("DB load failed", str(e))
            return

        # Normalize keys to your UI keys (in case DB_COLUMNS_MAP changes)
        normalized = []
        for r in rows:
            item = {}
            for ui_key, _ in COLUMNS:
                db_key = DB_COLUMNS_MAP[ui_key]
                item[ui_key] = r.get(db_key)
            normalized.append(item)

        self.loaded_rows = normalized
        self._update_stats(normalized)
        self._populate_table(normalized)
        self.status.set(f"Loaded {len(normalized)} rows from {schema}.{table} (limit {limit}).")

    def _populate_table(self, rows: list[dict]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in rows:
            vals = []
            for key, _ in COLUMNS:
                v = r.get(key)
                if key == "time":
                    vals.append(fmt_dt(v))
                elif key in {"shares"}:
                    vals.append(fmt_num(v, dp=8))
                elif key in {"price_per_share"}:
                    vals.append(fmt_num(v, dp=4))
                elif key in {"exchange_rate"}:
                    vals.append(fmt_num(v, dp=8))
                elif key in {"total"}:
                    vals.append(fmt_num(v, dp=2))
                else:
                    vals.append(safe_str(v))
            self.tree.insert("", "end", values=vals)

    def _update_stats(self, rows: list[dict]):
        buys = sum(1 for r in rows if r.get("action_type") == "BUY")
        sells = sum(1 for r in rows if r.get("action_type") == "SELL")
        tickers = sorted({(r.get("ticker") or "").upper() for r in rows if r.get("ticker")})
        self.stats_label.config(
            text=f"Rows: {len(rows)} | Buys: {buys} | Sells: {sells} | Tickers: {len(tickers)}"
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
