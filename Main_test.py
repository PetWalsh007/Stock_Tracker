from datetime import datetime

from positions import Position
from market_data import get_price, get_currency, get_fx_rate

from file_import import ingest_trading212_csv, _main as import_main

def d(s: str):
    return datetime.strptime(s, "%d/%m/%Y")

def dev_build_pos():

    positions = {}

    # testing  NVIDIA

    nvda = Position("NVDA")

    # ====== BUYS ======


    nvda.add_buy("B1", d("12/05/2021"), 0.0053888, 560.19, 1.2075, 2.50)
    nvda.add_buy("B2", d("13/05/2021"), 0.0047093, 553.69, 1.2072, 2.16)
    nvda.add_buy("B3", d("19/05/2021"), 0.0072518, 546.08, 1.2222, 3.24)
    nvda.add_buy("B4", d("24/05/2021"), 0.0023421, 625.74, 1.2213, 1.20)
    nvda.add_buy("B5", d("24/06/2021"), 0.0059209, 769.72, 1.1930, 3.83)
    nvda.add_buy("B6", d("24/06/2021"), 0.0056581, 769.67, 1.1931, 3.66)
    nvda.add_buy("B7", d("01/07/2021"), 0.0042630, 811.30, 1.1844, 2.92)
    nvda.add_buy("B8", d("21/09/2021"), 0.0141109, 214.50, 1.1732, 2.58)
    nvda.add_buy("B9", d("30/12/2021"), 0.0275152, 303.97, 1.1318, 7.40)
    nvda.add_buy("B10", d("18/01/2022"), 0.0108447, 261.97, 1.1364, 2.50)
    nvda.add_buy("B11", d("17/07/2023"), 0.0387216, 463.09, 1.1221, 16.00)
    nvda.add_buy("B12", d("23/05/2024"), 0.00384179, 1033.50, 1.0819, 3.68)
    nvda.add_buy("B13", d("27/01/2025"), 0.1064839, 118.03, 1.0491, 12.00)
    nvda.add_buy("B14", d("03/02/2025"), 0.1500000, 114.50, 1.0229, 16.82)
    

    # ====== SPLITS ======

    nvda.apply_split(4.0, d("20/07/2021"))
    nvda.apply_split(10.0, d("07/06/2024"))

    # ====== SALES ======

    nvda_sale_1 = nvda.sell(d("26/01/2026"), qty=1.5, proceeds_eur=244.58)

    positions["NVDA"] = nvda



    return positions


def print_sale_details(position: Position):
    """
    Print all sales for a given Position in the column layout you like.
    """
    headers = [
        "Lot", "Date", "Original qty", "Split", "Adjusted qty (new)",
        "Price USD", "FX", "Total Cost €", "Adjusted € / share",
        "Qty SOLD", "Qty LEFT", "Cost USED €", "Cost LEFT €",
        "Proceeds €", "Gain €",
    ]
    for sale in position.sales:
        print(f"\n=== SALE {sale.date.date()} {position.symbol} ===")
        print(f"Total qty: {sale.quantity}")
        print(f"Proceeds €: {sale.proceeds_eur:.2f}")
        print(f"Cost €:     {sale.total_cost_eur:.2f}")
        print(f"Gain €:     {sale.gain_eur:.2f}\n")

        print("\t".join(headers))
        for row in sale.per_lot:
            print("\t".join(str(row[h]) for h in headers))

        print("\nAfter this sale:")
        print(f"  Qty left: {position.total_qty_left():.6f}")
        print(f"  Cost left €: {position.total_cost_left():.2f}")


def dev_test():
    positions = dev_build_pos()

    # Print NVDA sale breakdown
    nvda = positions["NVDA"]
    print_sale_details(nvda)

    
  # after your sell
    current_price = get_price("NVDA")
    print(f"\nCurrent NVDA price: ${current_price:.2f}")

    currency = get_currency("NVDA")
    print(f"NVDA trades in: {currency}")

    get_fx = get_fx_rate(currency, "EUR")
    print(f"Current EUR/{currency} FX rate: {get_fx:.5f}")
   
    current_price_usd = current_price     
    current_fx = get_fx            

    value = nvda.unrealised_value(current_price_usd, current_fx)
    profit = nvda.unrealised_profit(current_price_usd, current_fx)
    roi = nvda.unrealised_roi_pct(current_price_usd, current_fx)

    print("\n--- CURRENT POSITION ---")
    print(f"Shares left: {nvda.total_qty_left():.6f}")
    print(f"Cost basis left: €{nvda.total_cost_left():.2f}")
    print(f"Market value: €{value:.2f}")
    print(f"Unrealised profit: €{profit:.2f}")
    print(f"ROI: {roi:.2f}%")





def main():
    

    dev_test()

    

    pass
if __name__ == "__main__":
    main()