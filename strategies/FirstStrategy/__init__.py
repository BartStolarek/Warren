from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils


class FirstStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.vars['readyToBuy'] = False
        self.vars['readyToSell'] = False

    @property
    def sma_7(self):
        return ta.sma(self.candles[:], period=7, source_type="close", sequential=False)

    @property
    def sma_25(self):
        return ta.sma(self.candles[:], period=25, source_type="close", sequential=False)

    @property
    def sma_52(self):
        return ta.sma(self.candles[:], period=52, source_type="close", sequential=False)

    @property
    def atr(self):
        return ta.atr(self.candles, period=14)

    def should_long(self) -> bool:
        # BuyCondition1 and BuyCondition2
        self.vars['readyToBuy'] = (self.sma_7 > self.sma_25) and (self.sma_25 > self.sma_52)
        
        # Additional ATR condition (simplified for this example)
        atr_condition = self.close > self.open + self.atr

        return self.vars['readyToBuy'] and atr_condition

    def go_long(self):
        entry_price = self.close
        stop_loss = entry_price - 2 * self.atr
        take_profit = entry_price + 3 * self.atr

        qty = utils.size_to_qty(self.balance * 0.1, entry_price, fee_rate=self.fee_rate)

        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def should_short(self) -> bool:
        # SellCondition1 and SellCondition2
        self.vars['readyToSell'] = (self.sma_7 < self.sma_25) and (self.sma_25 < self.sma_52)
        
        # Additional ATR condition (simplified for this example)
        atr_condition = self.close < self.open - self.atr

        return self.vars['readyToSell'] and atr_condition

    def go_short(self):
        entry_price = self.close
        stop_loss = entry_price + 2 * self.atr
        take_profit = entry_price - 3 * self.atr

        qty = utils.size_to_qty(self.balance * 0.1, entry_price, fee_rate=self.fee_rate)

        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def should_cancel_entry(self) -> bool:
        return False

    def update_position(self):
        # Implement trailing stop if needed
        if self.is_long and self.close < self.sma_25:
            self.liquidate()
        elif self.is_short and self.close > self.sma_25:
            self.liquidate()
