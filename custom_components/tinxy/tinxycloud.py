from pickle import FALSE, TRUE
import requests
import json
import asyncio
import aiohttp
import time
from datetime import datetime


class TinxyCloud:
    token = ""
    base_url = "https://backend.tinxy.in/"
    devices = []
    disabled_devices = [
        'EVA_HUB'
    ]
    enabled_list = [
        'WIFI_3SWITCH_1FAN',
        'WIRED_DOOR_LOCK',
        'WIFI_4SWITCH',
        'WIFI_SWITCH',
        'WIRED_DOOR_LOCK_V2',
        'WIFI_4DIMMER',
        'Fan',
        'Dimmable Light'
        'WIFI_SWITCH_V2',
        'WIFI_4SWITCH_V2',
        'WIFI_2SWITCH_V1',
        'WIFI_6SWITCH_V1',
        'WIFI_BULB_WHITE_V1',
        'EVA_BULB',
    ]

    gtype_light = ['action.devices.types.LIGHT']
    gtype_switch = ['action.devices.types.SWITCH']
    gtype_lock = ['action.devices.types.LOCK']
    typeId_fan = ['WIFI_3SWITCH_1FAN', 'Fan']

    def __init__(self, token):
        self.token = token

    async def tinxy_request(self, path, payload={}, method="GET"):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+self.token
        }
        if payload:
            payload['source'] = "API"

        print(payload)
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(self.base_url+path, json=payload, headers=headers) as resp:
                    return await resp.json()
            elif method == "POST":
                async with session.post(self.base_url+path, json=payload, headers=headers) as resp:
                    return await resp.json()

    async def sync_devices(self):
        device_list = []
        result = await self.tinxy_request('v2/devices/')
        for item in result:
            device_list = device_list + (self.parse_device(item))
        self.devices = device_list

    def list_all_devices(self):
        return self.devices

    def list_switches(self):
        return [d for d in self.devices if d['device_type'] == 'Switch']

    def list_lights(self):
        return [d for d in self.devices if d['device_type'] == 'Light']

    def list_fans(self):
        return [d for d in self.devices if d['device_type'] == 'Fan']

    def list_locks(self):
        return [d for d in self.devices if d['gtype'] in self.gtype_lock]

    async def get_device_state(self, id, device_number):
        return await self.tinxy_request(
            'v2/devices/'+id+'/state?deviceNumber='+device_number)

    async def set_device_state(self, id, device_number, state, brightness=None):
        payload = {
            "request": {
                "state": state
            },
            "deviceNumber": device_number
        }
        # check if brightness is provided
        if brightness != None:
            payload['request']['brightness'] = brightness
        return await self.tinxy_request(
            'v2/devices/'+id+'/toggle', payload=payload, method="POST")

    def parse_device(self, data):
        devices = []

        # Handle single item devices
        if not data['devices']:
            if data['typeId']['name'] in self.enabled_list:
                device_type = 'Light' if data['typeId']['name'] == 'EVA_BULB' else 'Switch'
                devices.append({
                    'id': data['_id']+'-1',
                    'device_id': data['_id'],
                    "name": data['name'],
                    'relay_no': 1,
                    'gtype': data['typeId']['gtype'],
                    'traits': data['typeId']['traits'],
                    'device_type': device_type,
                    'user_device_type': device_type,
                    'device_desc': data['typeId']['long_name'],
                    'tinxy_type': data['typeId']['name'],
                    'icon': self.icon_generate(data['typeId']['name']),
                })
        # Handle multinode_devices
        elif data['typeId']['name'] in self.enabled_list:
            for id, nodes in enumerate(data['devices']):
                devices.append({
                    'id': data['_id']+'-'+str(id+1),
                    'device_id': data['_id'],
                    "name": nodes,
                    'relay_no': id+1,
                    'gtype': data['typeId']['gtype'],
                    'traits': data['typeId']['traits'],
                    'device_type': self.get_device_type(data['typeId']['name'], id),
                    'user_device_type': data['deviceTypes'][id],
                    'device_desc': data['typeId']['long_name'],
                    'tinxy_type': data['typeId']['name'],
                    'icon': self.icon_generate(data['deviceTypes'][id]),
                })
        else:
            print('unknown  ='+data['typeId']['name'])
            print(self.enabled_list)
        return devices

    def get_device_type(self, tinxy_type, id):
        light_list = ['Tubelight', 'LED Bulb']
        if tinxy_type in self.typeId_fan and id == 0:
            return 'Fan'
        elif tinxy_type in light_list:
            return 'Light'
        elif tinxy_type in self.gtype_lock:
            return 'Switch'
        else:
            return 'Switch'

    def icon_generate(self, devicetype):
        if devicetype == "Heater":
            return "mdi:radiator"
        elif devicetype == "Tubelight":
            return "mdi:lightbulb-fluorescent-tube"
        elif devicetype == "LED Bulb" or devicetype == "Dimmable Light" or devicetype == "LED Dimmable Bulb" or devicetype == "EVA_BULB":
            return "mdi:lightbulb"
        elif devicetype == "Music System":
            return "mdi:music"
        elif devicetype == "Fan":
            return "mdi:fan"
        elif devicetype == "Socket":
            return "mdi:power-socket-eu"
        elif devicetype == "TV":
            return "mdi:television"
        else:
            return "mdi:toggle-switch"
