# position.py
from typing import List, Dict
from dataclasses import dataclass, field
from datetime import datetime

from models import LotRow


@dataclass
class SaleSummary:
    date: datetime
    quantity: float
    proceeds_eur: float
    total_cost_eur: float
    gain_eur: float
    per_lot: List[Dict] = field(default_factory=list)


class Position:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.lots: List[LotRow] = []
        self.sales: List[SaleSummary] = []

    # ---- adding buys as new lots ----

    def add_buy(
        self,
        lot_id: str,
        date: datetime,
        qty: float,
        price_usd: float,
        fx: float,
        total_cost_eur: float,
    ):
        row = LotRow(
            lot_id=lot_id,
            date=date,
            original_qty=qty,
            split_factor=1.0,
            price_usd=price_usd,
            fx=fx,
            total_cost_eur=total_cost_eur,
            adjusted_qty=0.0,         
            adjusted_price_eur=0.0,   
            qty_left=0.0,
            cost_left_eur=0.0,
        )
        self.lots.append(row)

    # ---- stock split 

    def apply_split(self, factor: float, split_date: datetime):
        """
        Apply a stock split only to lots that existed on or before split_date.
        e.g. 4-for-1: factor=4.0
        """
        if factor <= 0:
            raise ValueError("Split factor must be > 0")

        for lot in self.lots:
            
            if lot.date <= split_date:
                lot.apply_split(factor)

    # 

    def sell(self, date: datetime, qty: float, proceeds_eur: float) -> SaleSummary:
        qty_to_sell = qty
        price_per_share = proceeds_eur / qty

        total_cost = 0.0
        per_lot_rows: List[Dict] = []

        # FIFO
        for lot in self.lots:
            if qty_to_sell <= 0:
                break
            if lot.qty_left <= 1e-12:
                continue

            before_left = lot.qty_left
            cost_used, proceeds_used, gain = lot.consume_for_sale(qty_to_sell, price_per_share)
            used_qty = before_left - lot.qty_left

            if used_qty > 0:
                qty_to_sell -= used_qty
                total_cost += cost_used

                per_lot_rows.append({
                    "Lot": lot.lot_id,
                    "Date": lot.date.date(),
                    "Original qty": lot.original_qty,
                    "Split": lot.split_factor,
                    "Adjusted qty (new)": lot.adjusted_qty,
                    "Price USD": lot.price_usd,
                    "FX": lot.fx,
                    "Total Cost €": lot.total_cost_eur,
                    "Adjusted € / share": lot.adjusted_price_eur,
                    "Qty SOLD": used_qty,
                    "Qty LEFT": lot.qty_left,
                    "Cost USED €": cost_used,
                    "Cost LEFT €": lot.cost_left_eur,
                    "Proceeds €": proceeds_used,
                    "Gain €": gain,
                })

        if abs(qty_to_sell) > 1e-9:
            raise ValueError(
                f"Not enough {self.symbol} shares to cover sale, short {qty_to_sell:.6f}"
            )

        summary = SaleSummary(
            date=date,
            quantity=qty,
            proceeds_eur=proceeds_eur,
            total_cost_eur=total_cost,
            gain_eur=proceeds_eur - total_cost,
            per_lot=per_lot_rows,
        )
        self.sales.append(summary)
        return summary

    #  helpers 

    def total_qty_left(self) -> float:
        return sum(lot.qty_left for lot in self.lots)

    def total_cost_left(self) -> float:
        return sum(lot.cost_left_eur for lot in self.lots)
    

    def unrealised_value(self, price_usd: float, fx: float) -> float:
        """
        Current market value of remaining shares in EUR.
        """
        price_eur = price_usd * fx
        return self.total_qty_left() * price_eur


    def unrealised_profit(self, price_usd: float, fx: float) -> float:
        """
        Unrealised profit in EUR.
        """
        return self.unrealised_value(price_usd, fx) - self.total_cost_left()


    def unrealised_roi_pct(self, price_usd: float, fx: float) -> float:
        """
        Unrealised ROI as a percentage.
        """
        cost = self.total_cost_left()
        if cost == 0:
            return 0.0
        return (self.unrealised_profit(price_usd, fx) / cost) * 100

