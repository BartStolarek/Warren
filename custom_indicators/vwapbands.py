from collections import namedtuple
import numpy as np
from typing import Union
from jesse.helpers import get_candle_source, slice_candles

VWAPBands = namedtuple('VWAPBands', ['vwap', 'upper_bands', 'lower_bands'])

def vwapbands(candles: np.ndarray, dev_multipliers: list = [1, 2, 3, 4, 5], source_type: str = "ohlc4", sequential: bool = False) -> Union[VWAPBands, float]:
    """
    VWAP with Standard Deviation Bands, resetting daily
    :param candles: np.ndarray
    :param dev_multipliers: list of deviation multipliers for bands
    :param source_type: str - default: ohlc4
    :param sequential: bool - default: False
    :return: Union[VWAPBands, float]
    """
    candles = slice_candles(candles, sequential)

    source = get_candle_source(candles, source_type)
    volume = candles[:, 5]
    
    # Get timestamps and convert to days
    timestamps = candles[:, 0]
    days = np.array([ts // (24 * 60 * 60 * 1000) for ts in timestamps])
    
    # Initialize arrays
    vwap = np.zeros_like(source)
    dev = np.zeros_like(source)
    
    # Calculate VWAP and deviation for each day
    for day in np.unique(days):
        mask = days == day
        daily_source = source[mask]
        daily_volume = volume[mask]
        
        cumulative_pv = np.cumsum(daily_source * daily_volume)
        cumulative_volume = np.cumsum(daily_volume)
        
        daily_vwap = cumulative_pv / cumulative_volume
        daily_v2sum = np.cumsum(daily_volume * daily_source ** 2)
        daily_dev = np.sqrt(np.maximum(daily_v2sum / cumulative_volume - daily_vwap ** 2, 0))
        
        vwap[mask] = daily_vwap
        dev[mask] = daily_dev

    upper_bands = [vwap + multiplier * dev for multiplier in dev_multipliers]
    lower_bands = [vwap - multiplier * dev for multiplier in dev_multipliers]

    if sequential:
        return VWAPBands(vwap, upper_bands, lower_bands)
    else:
        return VWAPBands(vwap[-1], [ub[-1] for ub in upper_bands], [lb[-1] for lb in lower_bands])