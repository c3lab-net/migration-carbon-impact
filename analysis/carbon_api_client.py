#!/usr/bin/env python3

import arrow
import requests
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
from typing import Any
import sys

override_renewable_ratio_over_carbon_intensity = False

@dataclass
class TimestampdValue:
    timestamp: datetime
    value: float

    def __str__(self) -> str:
        return '(%s, %.3f)' % (
            self.timestamp.isoformat(),
            self.value
        )

    def __lt__(self, other):
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        else:
            return self.value < other.value

@dataclass
class CarbonIntensityData:
    cloud_vendor: str
    region: str
    iso: str
    timeseries: list[TimestampdValue]
    timeseries_pd: pd.Series

    def __str__(self) -> str:
        if len(self.timeseries) == 0:
            timeseries_str = 'timeseries (len=0)'
        else:
            timeseries_str = f'timeseries ([%s, %s], len={len(self.timeseries)})' % (
                self.timeseries[0].timestamp,
                self.timeseries[-1].timestamp
            )
        return f'CarbonIntensityData {self.cloud_vendor}:{self.region} ({self.iso}), {timeseries_str}'

    def set_timeseries_interval(self, freq: str = '5min'):
        pd_index = self.timeseries_pd.index
        print('pd min: ', pd_index.min(), pd_index.min().tzname())
        new_index = pd.date_range(self.timeseries_pd.index.min(), self.timeseries_pd.index.max(), freq=freq, inclusive='both', tz=pd_index.min().tzname())
        self.timeseries_pd = self.timeseries_pd.reindex(new_index, method='ffill')
        self.reset_timeseries_from_pd()

    def reset_timeseries_from_pd(self):
        self.timeseries = self.create_timeseries_from_pd(self.timeseries_pd)

    @classmethod
    def create_timeseries_from_pd(cls, timeseries_pd: pd.Series) -> list[TimestampdValue]:
        return list(map(
            lambda ts, ci: TimestampdValue(ts.to_pydatetime(), ci),
            timeseries_pd.index.tolist(),
            timeseries_pd.values.tolist()
        ))

    def merge_with(self, other, dedup=True):
        if not isinstance(other, CarbonIntensityData):
            raise TypeError("Cannot compare with a different type")
        if self.cloud_vendor != other.cloud_vendor or \
                self.region != other.region or \
                self.iso != other.iso:
            raise ValueError("Cannot merge with a different cloud vendor/region or iso")
        combined = pd.concat([self.timeseries_pd, other.timeseries_pd])
        if dedup:
            self.timeseries_pd = combined[~combined.index.duplicated(keep='first')].sort_index()
        self.reset_timeseries_from_pd()

    @classmethod
    def merge(cls, l):
        if not isinstance(l, list) or len(l) == 0:
            raise TypeError("l must be a non-empty list")
        for element in l:
            if not isinstance(element, CarbonIntensityData):
                raise TypeError("Cannot merge elements of a different type")
        it = iter(l)
        first = next(it)
        for element in it:
            if first.cloud_vendor != element.cloud_vendor or \
                    first.region != element.region or \
                    first.iso != element.iso:
                raise ValueError("Cannot merge with a different cloud vendor/region or iso")
        combined_pd = pd.concat([x.timeseries_pd for x in l])
        combined_pd = combined_pd[~combined_pd.index.duplicated(keep='first')].sort_index()
        timeseries = cls.create_timeseries_from_pd(combined_pd)
        return CarbonIntensityData(first.cloud_vendor, first.region, first.iso, timeseries, combined_pd)

def get_carbon_intensity_interval(timestamps: list[datetime]) -> timedelta:
    """Deduce the interval from a series of timestamps returned from the database."""
    if len(timestamps) == 0:
        raise ValueError("Invalid argument: empty list.")
    if len(timestamps) == 1:
        return timedelta(hours=1)
    timestamp_deltas = np.diff(timestamps)
    values, counts = np.unique(timestamp_deltas, return_counts=True)
    return values[np.argmax(counts)]


def create_pd_series(timestamps: list[datetime], values: list[Any]) -> pd.Series:
    def to_utc(ts: datetime):
        """Add/Convert datetime to UTC timezone."""
        tz_utc = timezone.utc
        if ts.tzinfo:
            return ts.astimezone(tz_utc)
        else:
            return ts.replace(tzinfo=tz_utc)

    utc_timestamps = [ to_utc(ts) for ts in timestamps ]
    pd_index = pd.DatetimeIndex(utc_timestamps)
    pd_values = values
    ds = pd.Series(pd_values, index=pd_index)
    ds.sort_index()
    return ds


def call_sysnet_carbon_intensity_api(latitude: float, longitude: float, start: arrow.Arrow, end: arrow.Arrow,
                                     desired_renewable_ratio: float = None) -> CarbonIntensityData:
    url_get_carbon_intensity = 'http://yeti-09.sysnet.ucsd.edu/carbon-intensity/'
    response = requests.get(url_get_carbon_intensity, params={
        'latitude': latitude,
        'longitude': longitude,
        'start': start,
        'end': end,
        'desired_renewable_ratio': desired_renewable_ratio
    })
    global override_renewable_ratio_over_carbon_intensity
    try:
        assert response.ok, "Carbon intensity lookup failed (%d): %s" % (response.status_code, response.text)
        response_json = response.json()
        iso = response_json['region']
        carbon_intensities = response_json['carbon_intensities']
        timeseries = []
        for element in carbon_intensities:
            timestamp = arrow.get(element['timestamp']).datetime
            carbon_intensity = float(element['carbon_intensity'] or -1)
            renewable_ratio = float(element['renewable_ratio'] or -1)
            if carbon_intensity == -1:
                continue
            if override_renewable_ratio_over_carbon_intensity:
                timeseries.append((timestamp, renewable_ratio))
            else:
                timeseries.append((timestamp, carbon_intensity))
        timeseries = sorted(timeseries)
        ds = create_pd_series([e[0] for e in timeseries], [e[1] for e in timeseries])
        return CarbonIntensityData(None, None, iso, timeseries, ds)
    except AssertionError as e:
        print(e, file=sys.stderr)
        return None
        # return CarbonIntensityData(None, None, None, [], pd.Series([]))

def call_sysnet_energy_mixture_api(latitude: float, longitude: float, start: arrow.Arrow, end: arrow.Arrow):
    url_get_energy_mixture = 'http://yeti-09.sysnet.ucsd.edu/energy-mixture/'
    response = requests.get(url_get_energy_mixture, params={
        'latitude': latitude,
        'longitude': longitude,
        'start': start,
        'end': end,
    })
    assert response.ok, "Energy mixture lookup failed (%d): %s" % (response.status_code, response.text)
    response_json = response.json()
    electricity_region = response_json['region']
    l_power_by_fuel_type = response_json['power_by_fuel_type']
    data_timeseries = []
    for entry in l_power_by_fuel_type:
        timestamp = arrow.get(entry['timestamp']).datetime
        d_power_by_fuel_type = {}
        for d in entry['values']:
            fuel_type = d['type']
            power_mw = d['power_mw']
            d_power_by_fuel_type[fuel_type] = power_mw
        data_timeseries.append({
            'timestamp': timestamp,
            'power_by_fuel_type': d_power_by_fuel_type,
        })
    return data_timeseries
