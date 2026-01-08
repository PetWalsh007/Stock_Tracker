
# version 1 07/01/2026




from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LotRow:
    lot_id: str              
    date: datetime
    original_qty: float     
    split_factor: float     
    price_usd: Optional[float] 
    fx: Optional[float]         
    total_cost_eur: float    

    # to update
    adjusted_qty: float     
    adjusted_price_eur: float  
    qty_sold: float = 0.0    # 
    qty_left: float = 0.0    # 
    cost_left_eur: float = 0.0  

    def __post_init__(self):

        if self.total_cost_eur is None:
            if self.price_usd is None or self.fx is None:
                raise ValueError(
                    f"Lot {self.lot_id}: either provide total_cost_eur OR price_usd + fx"
                )
    
            self.total_cost_eur = (self.price_usd * self.original_qty) / self.fx

 
        self.adjusted_qty = self.original_qty * self.split_factor
        self.qty_left = self.adjusted_qty
        self.adjusted_price_eur = (
            self.total_cost_eur / self.adjusted_qty if self.adjusted_qty else 0.0
        )
        self.cost_left_eur = self.total_cost_eur

    def apply_split(self, factor: float):
        """
        Apply a stock split to THIS lot.
        E.g. factor=4.0 means each share becomes 4 shares.
        """
        self.split_factor *= factor
        self.adjusted_qty *= factor
        self.qty_left *= factor

        self.adjusted_price_eur = (
            self.total_cost_eur / self.adjusted_qty if self.adjusted_qty else 0.0
        )

    def consume_for_sale(self, qty_to_use: float, sale_price_eur: float):
        """
        Use up qty_to_use shares from this lot for a sale.

        Returns:
            cost_used_eur, proceeds_eur, gain_eur
        """
        qty_from_lot = min(qty_to_use, self.qty_left)
        if qty_from_lot <= 0:
            return 0.0, 0.0, 0.0


        cost_per_share = self.cost_left_eur / self.qty_left
        cost_used = cost_per_share * qty_from_lot
        proceeds = sale_price_eur * qty_from_lot
        gain = proceeds - cost_used

        # update this row
        self.qty_left -= qty_from_lot
        self.qty_sold += qty_from_lot
        self.cost_left_eur -= cost_used

        return cost_used, proceeds, gain
