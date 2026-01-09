# area to control the importing of files in the application



import csv
from datetime import datetime


HEADERS = [
    "Action",
    "Time",
    "ISIN",
    "Ticker",
    "Name",
    "Notes",
    "ID",
    "No. of shares",
    "Price / share",
    "Currency (Price / share)",
    "Exchange rate",
    "Result",
    "Currency (Result)",
    "Total",
    "Currency (Total)",
    "Withholding tax",
    "Currency (Withholding tax)",
]

_TIME_FORMATS = [
    "%d/%m/%Y %H:%M",      # 27/01/2025 19:39
    "%Y-%m-%d %H:%M:%S",   # 2025-01-06 11:57:50
    "%Y/%m/%d %H:%M:%S",   # 2025/01/06 11:57:50
    "%Y-%m-%d %H:%M",     
]

def _to_float(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    # remove thousands separators 
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _to_str(x):
    if x is None:
        return None
    s = str(x).strip()
    return s if s != "" else None


def _parse_time(s: str) -> datetime:
    s = s.strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unrecognised time format: {s}")


def ingest_trading212_csv(path: str) -> list[dict]:
    """
    Reads a Trading212 CSV and returns a list of dict rows with cleaned types,
    filtered to only Market/Limit buys and sells.
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])

        reader = csv.DictReader(f, dialect=dialect)

        missing = [h for h in HEADERS if h not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing headers in CSV: {missing}")

        rows = []
        for raw in reader:
            action_raw = _to_str(raw.get("Action"))
            action_type, order_type = _classify_action(action_raw)

   
            if action_type is None:
                continue

            row = {
                "action": action_raw,         
                "action_type": action_type,   
                "order_type": order_type,     

                "time": _parse_time(raw["Time"]) if raw.get("Time") else None,

                "isin": _to_str(raw.get("ISIN")),
                "ticker": _to_str(raw.get("Ticker")),
                "name": _to_str(raw.get("Name")),
                "notes": _to_str(raw.get("Notes")),
                "id": _to_str(raw.get("ID")),

                "shares": _to_float(raw.get("No. of shares")),
                "price_per_share": _to_float(raw.get("Price / share")),
                "price_currency": _to_str(raw.get("Currency (Price / share)")),

                "exchange_rate": _to_float(raw.get("Exchange rate")),
                "result": _to_float(raw.get("Result")),
                "result_currency": _to_str(raw.get("Currency (Result)")),

                "total": _to_float(raw.get("Total")),
                "total_currency": _to_str(raw.get("Currency (Total)")),

                "withholding_tax": _to_float(raw.get("Withholding tax")),
                "withholding_tax_currency": _to_str(raw.get("Currency (Withholding tax)")),

                "raw": raw,
            }

          
            if row["time"] is None:
                continue

            rows.append(row)

    rows.sort(key=lambda r: r["time"])
    return rows


def _classify_action(action: str):
    """
    Return (action_type, order_type) or (None, None) if not a trade we care about.
    """
    if not action:
        return None, None

    a = action.strip().lower()
    print (a)
    # only accept buy/sell rows
    if a in {"market buy", "limit buy"}:
        return "BUY", "MARKET" if "market" in a else "LIMIT"
    if a in {"market sell", "limit sell"}:
        return "SELL", "MARKET" if "market" in a else "LIMIT"
    if a in {"dividend (dividend)", "dividend (dividend manufactured payment)"}:
        return "Dividend", None if "manufactured" not in a else "Manufactured"
    if a in {"deposit"}:
        return "Deposit", None
    if a in {"withdrawal"}:
        return "Withdrawal", None
    if a in {"interest on cash"}:
        return "Interest", None

    return None, None




def _main():
    path = "T212_2501-2512.csv"  # change if needed
    rows = ingest_trading212_csv(path)

    print(f"Loaded rows: {len(rows)}")
    print("First row:", rows[0])
    print("Last row:", rows[-1])

    
    # print a few IDs and tickers
    for r in rows[:10]:
        print(
            r["time"],
            r["action_type"],
            r["order_type"],
            r["ticker"],
            r["shares"],
            r["price_per_share"],
            r["price_currency"],
            "FX:", r["exchange_rate"],
            r["total"],
            r["total_currency"],
        )



if __name__ == "__main__":
    _main()