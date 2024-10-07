from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils

class VillianMovingAverages(Strategy):
    last_closed_index = 0

    def hyperparameters(self):
        return [
            {'name': 'supertrend_period', 'type': int, 'min': 4, 'max': 25, 'default': 10},
            {'name': 'supertrend_factor', 'type': int, 'min': 2, 'max': 10, 'default': 3},
            {'name': 'sma_period_7', 'type': int, 'min': 2, 'max': 25, 'default': 7},
            {'name': 'sma_period_25', 'type': int, 'min': 14, 'max': 52, 'default': 25},
            {'name': 'sma_period_52', 'type': int, 'min': 25, 'max': 100, 'default': 52},
        ]

    @property
    def supertrend(self):
        return ta.supertrend(self.candles, period=self.hp['supertrend_period'], factor=self.hp['supertrend_factor'], sequential=False)

    @property
    def supertrend_daily(self):
        daily_candles = self.get_candles(self.exchange, self.symbol, "1D")
        trend = ta.supertrend(daily_candles, period=self.hp['supertrend_period'], factor=self.hp['supertrend_factor'], sequential=False).trend
        if trend < self.price:
            return 1
        elif trend > self.price:
            return -1
        else:
            return 0

    @property
    def sma_7(self):
        return ta.sma(self.candles, period=self.hp['sma_period_7'], source_type="close", sequential=True)

    @property
    def sma_25(self):
        return ta.sma(self.candles, period=self.hp['sma_period_25'], source_type="close", sequential=True)

    @property
    def sma_52(self):
        return ta.sma(self.candles, period=self.hp['sma_period_52'], source_type="close", sequential=True)

    @property
    def atr(self):
        return ta.atr(self.candles, period=14)

    @property
    def volume(self):
        return self.candles[:, 5][-1]

    @property
    def volume_seq(self):
        return self.candles[:, 5]

    @property
    def passed_time(self):
        return self.index - self.last_closed_index > 0

    def cross_over(self, series1, series2):
        return series1[-2] <= series2[-2] and series1[-1] > series2[-1]

    def cross_under(self, series1, series2):
        return series1[-2] >= series2[-2] and series1[-1] < series2[-1]

    def should_long(self) -> bool:
        return (self.sma_25[-1] > self.sma_52[-1]) and \
               self.cross_over(self.sma_7, self.sma_25) and \
               self.passed_time and \
               self.supertrend.trend < self.price and \
               self.supertrend_daily == 1

    def go_long(self):
        entry_price = self.price
        stop_loss = self.price - self.atr * 2.5
        take_profit = entry_price + 10 * self.atr

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=3, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def should_short(self) -> bool:
        return (self.sma_25[-1] < self.sma_52[-1]) and \
               self.cross_under(self.sma_7, self.sma_25) and \
               self.passed_time and \
               self.supertrend.trend > self.price and \
               self.supertrend_daily == -1

    def go_short(self):
        entry_price = self.price
        stop_loss = self.price + self.atr * 2.5
        take_profit = entry_price - 10 * self.atr

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=3, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def should_cancel_entry(self) -> bool:
        return False

    def on_close_position(self, order) -> None:
        last_closed_index = self.index

    def update_position(self):
        if self.is_long and self.close < self.sma_25[-1]:
            self.liquidate()
        elif self.is_short and self.close > self.sma_25[-1]:
            self.liquidate()

    def after(self) -> None:
        self.add_line_to_candle_chart('sma7', self.sma_7[-1], color="red")
        self.add_line_to_candle_chart('sma25', self.sma_25[-1], color="orange")
        self.add_line_to_candle_chart('sma52', self.sma_52[-1], color="yellow")

        # Extract the SuperTrend value
        supertrend_value = self.supertrend.trend
        close_price = self.candles[-1, 2]  # 2 is the index for closing price

        # Determine the color based on whether the SuperTrend is above or below the close price
        if supertrend_value > close_price:
            line_color = "red"
            fill_color = "rgba(255, 0, 0, 0.1)"  # Semi-transparent red
        else:
            line_color = "green"
            fill_color = "rgba(0, 255, 0, 0.1)"  # Semi-transparent green

        # Add the SuperTrend line to the chart
        self.add_line_to_candle_chart('SuperTrend', supertrend_value, color=line_color)

        # Create fill effect
        num_fill_lines = 10
        step = (supertrend_value - close_price) / num_fill_lines

        for i in range(1, num_fill_lines):
            fill_value = close_price + step * i
            self.add_line_to_candle_chart(f'Fill_{i}', fill_value, color=fill_color)

        self.add_extra_line_chart('Daily Supertrend', 'D ST', self.supertrend_daily)

        