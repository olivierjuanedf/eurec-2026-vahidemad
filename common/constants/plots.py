from dataclasses import dataclass


@dataclass
class PlotNames:
    prod_stacked: str = 'prod_stacked'
    prod_stacked_with_stock: str = 'prod_stacked_with_stock'
    link_flows: str = 'link_flows'
    marginal_price: str = 'marginal_price'
