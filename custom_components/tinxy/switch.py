from __future__ import annotations
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.switch import PLATFORM_SCHEMA

from datetime import timedelta, datetime

from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle
import requests
import json
import homeassistant.helpers.config_validation as cv
import logging

from homeassistant import config_entries
# from .const import DOMAIN
# _LOGGER = logging.getLogger(__name__)


BASE_URL = "https://backend.tinxy.in/"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

SWITCH_PREFIX = 'Tinxy '
CONF_API_KEY = "api_key"

DOMAIN = "tinxy"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the sensor platform."""
    # add_entities([TinxySwitch()])
    api_key = config.get(CONF_API_KEY)
    entities = read_devices(api_key)
    add_entities(entities)


_LOGGER = logging.getLogger(__name__)


def read_devices(api_key):
    list = []
    try:
        url = BASE_URL+"v2/devices/"
        headers = {"Authorization": "Bearer "+api_key}
        response = requests.request("GET", url, data="", headers=headers)
        jdata = json.loads(response.text)
        traitList = [['action.devices.traits.OnOff']]
        switches = [d for d in jdata if d['typeId']['traits'] in traitList]
        for switch in switches:
            for index, relay in enumerate(switch['devices']):
                _LOGGER.warning("add %s with device id %s relay_no %s",
                                switch["name"]+" "+relay, switch["_id"], str(index))
                device = {
                    "identifiers": {
                        (DOMAIN, switch["_id"])
                    },
                    "name": switch["name"],
                    "manufacturer": "Tinxy",
                    "model": switch['typeId']['name'],
                    "sw_version": switch['firmwareVersion']
                }
                list.append(TinxySwitch(api_key,
                                        switch["_id"], switch["name"]+" "+relay, str(index+1), switch['deviceTypes'][index], device))
        return list

    except requests.ConnectionError as e:
        print("OOPS!! Connection Error. Make sure you are connected to Internet. Technical Details given below.\n")
        print(str(e))
    except requests.Timeout as e:
        print("OOPS!! Timeout Error")
        print(str(e))
    except requests.RequestException as e:
        print("OOPS!! General Error")
        print(str(e))
    except KeyboardInterrupt:
        print("Someone closed the program")


class TinxyData(object):
    def __init__(self, api_key, device_id, relay_no=1):
        pass

    def update():
        pass


class TinxySwitch(SwitchEntity):

    def __init__(self, api_key, device_id, device_name, relay_no, device_type, device_info):
        self.is_available = True
        self.device_name = device_name
        self.relay_no = relay_no
        self.device_id = device_id
        self.type = device_type
        self._is_on = False
        self.d_device_info = device_info
        self.url = BASE_URL+"v2/devices/"+self.device_id+"/toggle"
        self.token = "Bearer "+api_key
        self.read_status()

    @property
    def device_info(self):
        return self.d_device_info

    @property
    def available(self):
        return self.is_available

    @property
    def unique_id(self):
        return self.device_id+'-'+self.relay_no

    def update(self):
        # self._is_on = not self._is_on
        self.read_status()

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""

        if self.type == "Heater":
            return "mdi:radiator"
        elif self.type == "Tubelight":
            return "mdi:lightbulb-fluorescent-tube"
        elif self.type == "LED Bulb" or self.type == "Dimmable Light" or self.type == "LED Dimmable Bulb":
            return "mdi:lightbulb"
        elif self.type == "Music System":
            return "mdi:music"
        elif self.type == "Fan":
            return "mdi:fan"
        elif self.type == "Socket":
            return "mdi:power-socket-eu"
        elif self.type == "TV":
            return "mdi:television"
        else:
            return "mdi:toggle-switch"

    @property
    def name(self):
        """Name of the entity."""
        return self.device_name

    @property
    def should_poll(self):
        return True

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        # self.read_status()
        return self._is_on

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._is_on = True
        self.switch_api()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._is_on = False
        self.switch_api()

    def read_status(self):

        # _LOGGER.warning("read_status called device_id %s relay_no %s",
        #                 self.device_id, self.relay_no)
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.token
        }
        try:
            response = requests.request(
                "GET", BASE_URL+"v2/devices/"+self.device_id+"/state?deviceNumber="+self.relay_no, data="", headers=headers)
            data = response.json()

            if data["status"] and data["status"] == 1:
                self.is_available = True
            else:
                self.is_available = False

            if data["state"] and data["state"] == "ON":
                self._is_on = True
            elif data["state"] and data["state"] == "OFF":
                self._is_on = False
            _LOGGER.warning("read_status called device_id %s relay_no %s response state %s and status %s",
                            self.device_id, self.relay_no, data["state"], data["status"])
        except Exception as e:
            self.is_available = False
            _LOGGER.error("read_status exception")

    def switch_api(self):
        """ Switch Device on and off"""
        _LOGGER.warning("switch_api called device_id %s relay_no %s",
                        self.device_id, int(self.relay_no)+1)
        try:
            payload = {
                "request": {
                    "state": 1 if self._is_on == True else 0
                },
                "deviceNumber": int(self.relay_no)
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": self.token
            }

            response = requests.request(
                "POST", self.url, data=json.dumps(payload), headers=headers)

            # _LOGGER.warning("switch_api result",response.text)
        except Exception as e:
            self.is_available = False
            _LOGGER.error("Exception on switch_api")
