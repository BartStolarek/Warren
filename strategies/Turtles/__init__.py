from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils


class Turtles(Strategy):

    @property
    def donchian(self):
        return ta.donchian(self.candles[:-1], period=20)

    def should_long(self) -> bool:
        return self.price > self.donchian.upperband

    def go_long(self):
        entry = self.price
        stop = self.price - ta.atr(self.candles) * 2.5
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry


    def should_short(self) -> bool:
        return self.price < self.donchian.lowerband

    def go_short(self):
        entry = self.price
        stop = self.price + ta.atr(self.candles) * 2.5
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry

    def should_cancel_entry(self) -> bool:
        return True

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - ta.atr(self.candles) * 2.5
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + ta.atr(self.candles) * 2.5

    def update_position(self) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.price - ta.atr(self.candles) * 2.5)
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price - ta.atr(self.candles) * 2.5)

    def after(self) -> None:
        self.add_line_to_candle_chart("Donchian", self.donchian)

