from collections import namedtuple
import numpy as np
from typing import Union
from jesse.helpers import get_candle_source, slice_candles
from datetime import datetime, timedelta

VWAPBands = namedtuple('VWAPBands', ['vwap', 'upper_bands', 'lower_bands'])

def vwapbands(candles: np.ndarray, dev_multipliers: list = [1, 2, 3, 4, 5], source_type: str = "ohlc4", sequential: bool = False, interval: str = 'Day') -> Union[VWAPBands, float]:
    """
    VWAP with Standard Deviation Bands, resetting based on specified interval
    :param candles: np.ndarray
    :param dev_multipliers: list of deviation multipliers for bands
    :param source_type: str - default: ohlc4
    :param sequential: bool - default: False
    :param interval: str - 'Day', 'Week', or 'Month' - default: 'Day'
    :return: Union[VWAPBands, float]
    """
    candles = slice_candles(candles, sequential)

    source = get_candle_source(candles, source_type)
    volume = candles[:, 5]
    
    # Get timestamps and convert to datetime
    timestamps = candles[:, 0]
    dates = np.array([datetime.utcfromtimestamp(ts / 1000) for ts in timestamps])
    
    # Initialize arrays
    vwap = np.zeros_like(source)
    dev = np.zeros_like(source)
    
    # Define interval function
    def get_interval_key(date):
        if interval == 'Day':
            return date.date()
        elif interval == 'Week':
            return date.isocalendar()[:2]  # Year and week number
        elif interval == 'Month':
            return (date.year, date.month)
        else:
            raise ValueError("Invalid interval. Choose 'Day', 'Week', or 'Month'.")
    
    # Calculate VWAP and deviation for each interval
    interval_keys = np.array([get_interval_key(date) for date in dates])
    
    for key in np.unique(interval_keys):
        mask = interval_keys == key
        interval_source = source[mask]
        interval_volume = volume[mask]
        
        cumulative_pv = np.cumsum(interval_source * interval_volume)
        cumulative_volume = np.cumsum(interval_volume)
        
        interval_vwap = cumulative_pv / cumulative_volume
        interval_v2sum = np.cumsum(interval_volume * interval_source ** 2)
        interval_dev = np.sqrt(np.maximum(interval_v2sum / cumulative_volume - interval_vwap ** 2, 0))
        
        vwap[mask] = interval_vwap
        dev[mask] = interval_dev

    upper_bands = [vwap + multiplier * dev for multiplier in dev_multipliers]
    lower_bands = [vwap - multiplier * dev for multiplier in dev_multipliers]

    if sequential:
        return VWAPBands(vwap, upper_bands, lower_bands)
    else:
        return VWAPBands(vwap[-1], [ub[-1] for ub in upper_bands], [lb[-1] for lb in lower_bands])