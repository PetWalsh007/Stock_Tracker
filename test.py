"""
Simple Trading212 CSV Viewer (Tkinter) for testing purposes.


"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime



from file_import import ingest_trading212_csv as ingest_trading212_csv



# =========================
# 2) TKINTER UI
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
        self.title("Trading212 CSV Viewer (Buys/Sells only)")
        self.geometry("1200x650")

        self.csv_path = tk.StringVar(value="")
        self.status = tk.StringVar(value="Pick a CSV to begin.")
        self.loaded_rows: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        # Top controls
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="CSV File:").pack(side="left")
        ttk.Entry(top, textvariable=self.csv_path, width=80).pack(side="left", padx=8)
        ttk.Button(top, text="Browse…", command=self.browse_file).pack(side="left")
        ttk.Button(top, text="Load", command=self.load_file).pack(side="left", padx=8)

        # Filters + stats
        mid = ttk.Frame(self, padding=(10, 0, 10, 10))
        mid.pack(fill="x")

        self.ticker_filter = tk.StringVar(value="")  # empty = all
        ttk.Label(mid, text="Ticker filter (optional):").pack(side="left")
        ttk.Entry(mid, textvariable=self.ticker_filter, width=12).pack(side="left", padx=8)
        ttk.Button(mid, text="Apply Filter", command=self.apply_filter).pack(side="left")

        self.stats_label = ttk.Label(mid, text="")
        self.stats_label.pack(side="left", padx=16)

        # Table (Treeview)
        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=[k for k, _ in COLUMNS],
            show="headings",
            height=20
        )

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Setup headings and default column widths
        for key, title in COLUMNS:
            self.tree.heading(key, text=title)
            # rough widths
            if key in {"time"}:
                self.tree.column(key, width=160, anchor="w")
            elif key in {"id"}:
                self.tree.column(key, width=140, anchor="w")
            elif key in {"ticker", "action_type", "order_type", "price_currency", "total_currency"}:
                self.tree.column(key, width=80, anchor="center")
            else:
                self.tree.column(key, width=100, anchor="e")

        # Status bar
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Trading212 CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.csv_path.set(path)

    def load_file(self):
        path = self.csv_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Please select a CSV file first.")
            return

        try:
            rows = ingest_trading212_csv(path)
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return

        self.loaded_rows = rows
        self.status.set(f"Loaded {len(rows)} trade rows (Market/Limit buys & sells).")
        self._update_stats(rows)
        self._populate_table(rows[:5000])  # preview first 500 to keep UI snappy

    def apply_filter(self):
        if not self.loaded_rows:
            return

        t = self.ticker_filter.get().strip().upper()
        if not t:
            filtered = self.loaded_rows
        else:
            filtered = [r for r in self.loaded_rows if (r.get("ticker") or "").upper() == t]

        self._update_stats(filtered)
        self._populate_table(filtered[:500])
        self.status.set(
            f"Showing {min(500, len(filtered))} of {len(filtered)} rows"
            + (f" (filtered: {t})" if t else "")
        )

    def _populate_table(self, rows: list[dict]):
        # clear
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
