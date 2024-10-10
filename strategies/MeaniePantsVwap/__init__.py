from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils
import custom_indicators as cta
import numpy as np
from datetime import datetime, timezone, timedelta

class MeaniePantsVwap(Strategy):
    def __init__(self):
        super().__init__()
        self.candle_index = 0
        self.last_day_timestamp = 0
        self.band_position = {
            'first': False,
            'second': False,
            'third': False,
            'fourth': False,
            'fifth': False
        }

    @property
    @cached
    def supertrend(self):
        st = ta.supertrend(self.candles, period=30, factor=10, sequential=False).trend
        if st > self.price:
            return -1
        elif st < self.price:
            return 1
        else:
            return 0


    @property
    @cached
    def vwap_bands(self):
        return cta.vwapbands(self.candles, sequential=True)

    def is_within_first_x_minutes(self):
        return self.candle_index < 60

    def is_within_final_hour(self):
        current_timestamp = self.candles[-1, 0]
        current_datetime_utc = self.convert_timestamp_to_utc(current_timestamp)
        
        # Check if it's the last hour of the day
        if current_datetime_utc.hour == 23:
            return True
        else:
            return False

    def should_long(self) -> bool:
        if self.is_within_first_x_minutes() or self.is_within_final_hour() or self.position.is_open:
            return False
        
        if not self.band_position['second'] and self.price <= self.vwap_bands.lower_bands[1][-1]:
            self.band_position['second'] = True
            print(f"Band 2 at price {self.price} triggered for short, candle_index: {self.candle_index}")
            return True

        return False

    def should_short(self) -> bool:
        if self.is_within_first_x_minutes() or self.is_within_final_hour() or self.position.is_open:
            return False
        
        if not self.band_position['second'] and self.price >= self.vwap_bands.upper_bands[1][-1]:
            self.band_position['second'] = True
            print(f"Band 2 at price {self.price} triggered for short, candle_index: {self.candle_index}")
            return True

        return False

    def should_cancel_entry(self) -> bool:
        return False

    def go_long(self):
        entry_price = self.price
        stop_loss = self.vwap_bands.lower_bands[4][-1]

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=1, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.buy = qty, entry_price
        self.stop_loss = qty, stop_loss
        

    def go_short(self):
        entry_price = self.price
        stop_loss = self.vwap_bands.upper_bands[4][-1]

        qty = utils.risk_to_qty(capital=self.available_margin, risk_per_capital=1, entry_price=entry_price, stop_loss_price=stop_loss, fee_rate=self.fee_rate)

        self.sell = qty, entry_price
        self.stop_loss = qty, stop_loss

    def increase_position_size(self, percentage):
        current_qty = self.position.qty
        additional_qty = abs(current_qty) * percentage
        
        if self.is_long:
            self.buy = additional_qty, self.price
        elif self.is_short:
            self.sell = additional_qty, self.price

    def update_position(self):
        if self.is_short:
            if self.price >= self.vwap_bands.upper_bands[2][-1] and not self.band_position['third']:
                self.band_position['third'] = True
                self.increase_position_size(0.2)  # Increase by 50%
            elif self.price >= self.vwap_bands.upper_bands[3][-1] and not self.band_position['fourth']:
                self.band_position['fourth'] = True
                self.increase_position_size(0.2)  # Increase by 50%

        if self.is_long:
            if self.price <= self.vwap_bands.lower_bands[2][-1] and not self.band_position['third']:
                self.band_position['third'] = True
                self.increase_position_size(0.2)  # Increase by 50%
            elif self.price <= self.vwap_bands.lower_bands[3][-1] and not self.band_position['fourth']:
                self.band_position['fourth'] = True
                self.increase_position_size(0.2)  # Increase by 50%

        if (self.is_long and self.price >= self.vwap_bands.vwap[-1]) or \
            (self.is_short and self.price <= self.vwap_bands.vwap[-1]):
            self.liquidate()
            self.reset_band_positions()

    def reset_band_positions(self):
        self.band_position = {
            'first': False,
            'second': False,
            'third': False,
            'fourth': False,
            'fifth': False
        }

    def should_cancel(self) -> bool:
        return False

    def convert_timestamp_to_utc(self, timestamp_ms):
        timestamp_s = timestamp_ms / 1000.0
        return datetime.fromtimestamp(timestamp_s, tz=timezone.utc)

    def before(self):
        current_timestamp = self.candles[-1, 0]
        current_datetime_utc = self.convert_timestamp_to_utc(current_timestamp)
        
        if self.last_day_timestamp == 0 or current_datetime_utc.date() > self.convert_timestamp_to_utc(self.last_day_timestamp).date():
            self.candle_index = 0
            self.last_day_timestamp = current_timestamp
            self.reset_band_positions()
            print(f"New day started: Timestamp: {current_datetime_utc}, Candle index: {self.candle_index}")
        else:
            self.candle_index += 1  

    def after(self):
        self.add_line_to_candle_chart('VWAP', self.vwap_bands.vwap[-1], color='white')

        band_colors = ['rgba(255,0,0,0.1)', 'rgba(255,0,0,0.2)', 'rgba(255,0,0,0.3)', 'rgba(255,0,0,0.4)', 'rgba(255,0,0,0.5)']

        for i, color in enumerate(band_colors):
            upper = self.vwap_bands.upper_bands[i][-1]
            lower = self.vwap_bands.lower_bands[i][-1]
            
            self.add_line_to_candle_chart(f'Upper Band {i+1}', upper, color='red')
            self.add_line_to_candle_chart(f'Lower Band {i+1}', lower, color='green')

    def terminate(self):
        pass