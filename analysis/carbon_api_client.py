#!/usr/bin/env python3

import arrow
import requests

def call_sysnet_carbon_intensity_api(latitude: float, longitude: float, start: arrow.Arrow, end: arrow.Arrow):
    url_get_carbon_intensity = 'http://yeti-09.sysnet.ucsd.edu/carbon-intensity/'
    response = requests.get(url_get_carbon_intensity, params={
        'latitude': latitude,
        'longitude': longitude,
        'start': start,
        'end': end,
    })
    assert response.ok, "Carbon intensity lookup failed (%d): %s" % (response.status_code, response.text)
    response_json = response.json()
    electricity_region = response_json['region']
    print('region:', electricity_region)
    carbon_intensities = response_json['carbon_intensities']
    data_timeseries = []
    for element in carbon_intensities:
        timestamp = arrow.get(element['timestamp']).datetime
        carbon_intensity = float(element['carbon_intensity'])
        data_timeseries.append({
            'timestamp': timestamp,
            'carbon_intensity': carbon_intensity,
        })
    return {
        'iso': electricity_region,
        'data': data_timeseries,
    }

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
    print('region:', electricity_region)
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
