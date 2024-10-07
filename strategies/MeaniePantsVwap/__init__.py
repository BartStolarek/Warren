from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
import custom_indicators as cta
import numpy as np
from datetime import datetime, timezone, timedelta

class MeaniePantsVwap(Strategy):
    def __init__(self):
        super().__init__()
        self.vwap_band_level = 2  # Use the 3rd band for entry signals (index 2 in 0-based list)
        self.candle_index = 0
        self.last_day_timestamp = 0

    @property
    @cached
    def atr(self):
        return ta.atr(self.candles, period=14, sequential=True)

    @property
    @cached
    def vwap_bands(self):
        return cta.vwapbands(self.candles, sequential=True)

    def is_within_first_30_minutes(self):
        # Assuming 1-minute candles, check if we're within the first 30 candles of the day
        return self.candle_index < 30

    def should_long(self) -> bool:
        return self.price < self.vwap_bands.lower_bands[self.vwap_band_level][-1] and not self.is_within_first_30_minutes()

    def should_short(self) -> bool:
        return self.price > self.vwap_bands.upper_bands[self.vwap_band_level][-1] and not self.is_within_first_30_minutes()

    def should_cancel_entry(self) -> bool:
        return False

    def go_long(self):
        entry_price = self.price
        stop_loss = self.price - self.atr[-1] * 2.5
        take_profit = self.vwap_bands.vwap[-1]

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=3, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def go_short(self):
        entry_price = self.price
        stop_loss = self.price + self.atr[-1] * 2.5
        take_profit = self.vwap_bands.vwap[-1]

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=3, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss
        self.take_profit = qty, take_profit

    def update_position(self):
        
        # Get current timestamp
        current_timestamp = self.candles[-1, 0]
        current_datetime_utc = self.convert_timestamp_to_utc(current_timestamp)
        
        # Check if its last hour of the day
        if current_datetime_utc.hour == 23:
            self.liquidate()
        if self.is_long and (self.price >= self.vwap_bands.vwap[-1] or current_datetime_utc.hour == 23):
            self.liquidate()
        elif self.is_short and (self.price <= self.vwap_bands.vwap[-1] or current_datetime_utc.hour == 23):
            self.liquidate()

    def should_cancel(self) -> bool:
        return False

    def convert_timestamp_to_utc(self, timestamp_ms):
        # Convert milliseconds to seconds
        timestamp_s = timestamp_ms / 1000.0
        
        # Create a datetime object in UTC
        return datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
        

    def after(self) -> None:

        current_timestamp = self.candles[-1, 0]
        current_datetime_utc = self.convert_timestamp_to_utc(current_timestamp)
        previous_timestamp = self.candles[-2, 0]
        previous_datetime_utc = self.convert_timestamp_to_utc(previous_timestamp)


        # Check if it's a new day
        if (current_datetime_utc.date() - previous_datetime_utc.date()) == timedelta(days=1):
            self.candle_index = 0
        else:
            self.candle_index += 1

        # Add VWAP line
        self.add_line_to_candle_chart('VWAP', self.vwap_bands.vwap[-1], color='white')

        # Define colors for bands
        band_colors = ['rgba(255,0,0,0.1)', 'rgba(255,0,0,0.2)', 'rgba(255,0,0,0.3)', 'rgba(255,0,0,0.4)', 'rgba(255,0,0,0.5)']

        # Add bands
        for i, color in enumerate(band_colors):
            upper = self.vwap_bands.upper_bands[i][-1]
            lower = self.vwap_bands.lower_bands[i][-1]
            
            # Add upper and lower band lines
            self.add_line_to_candle_chart(f'Upper Band {i+1}', upper, color='red')
            self.add_line_to_candle_chart(f'Lower Band {i+1}', lower, color='green')
            

    def terminate(self):
        pass