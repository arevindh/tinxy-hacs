from __future__ import annotations
import voluptuous as vol

from homeassistant.components.fan import FanEntity
from homeassistant.components.fan import PLATFORM_SCHEMA
from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

from homeassistant.components.fan import FanEntity, SUPPORT_SET_SPEED,  SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH, SPEED_OFF

from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle
import requests
import json
import homeassistant.helpers.config_validation as cv
import logging


from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)


from homeassistant import config_entries
# from .const import DOMAIN
# _LOGGER = logging.getLogger(__name__)


SPEED_RANGE = (1, 100)

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
    entities = read_devices_fan(api_key)
    add_entities(entities)


_LOGGER = logging.getLogger(__name__)


def read_devices_fan(api_key):
    list = []
    try:
        url = BASE_URL+"v2/devices/"
        headers = {"Authorization": "Bearer "+api_key}
        response = requests.request("GET", url, data="", headers=headers)
        jdata = json.loads(response.text)
        traitList = [['action.devices.traits.OnOff']]
        switches = [d for d in jdata if d['typeId']['traits'] in traitList]

        for switch in switches:
            device = {
                "identifiers": {
                    (DOMAIN, switch["_id"])
                },
                "name": switch["name"],
                "manufacturer": "Tinxy",
                "model": switch['typeId']['name'],
                "sw_version": switch['firmwareVersion']
            }

            for index, relay in enumerate(switch['devices']):
                if switch["typeId"]["name"] == "WIFI_3SWITCH_1FAN" and index == 0:
                    _LOGGER.warning("add FAN %s with device id %s relay_no %s",
                                    switch["name"]+" "+relay, switch["_id"], str(index))

                    list.append(TinxyFan(api_key,
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


class TinxyFan(FanEntity):
    def __init__(self, api_key, device_id, device_name, relay_no, device_type, device_info):
        self.is_available = True
        self.device_name = device_name
        self.relay_no = relay_no
        self.device_id = device_id
        self.type = device_type
        self._is_on = False
        self.current_speed = 0
        self.d_device_info = device_info
        self.url = BASE_URL+"v2/devices/"+self.device_id+"/toggle"
        self.token = "Bearer "+api_key
        self.read_status()
        _LOGGER.warning("Fan Connected")

    # @property
    # def device_info(self):
    #     return self.d_device_info

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
        return "mdi:fan"

    @property
    def name(self):
        """Name of the entity."""
        return self.device_name

    # @property
    # def should_poll(self):
    #     return True

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        # self.read_status()
        return self._is_on

    @property
    def speed(self):
        return self.current_speed

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        return ranged_value_to_percentage(SPEED_RANGE, self.current_speed)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return int_states_in_range(SPEED_RANGE)

    @property
    def supported_features(self):
        return SUPPORT_SET_SPEED

    def set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self.current_speed = percentage
        self.switch_api()

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._is_on = True
        self.switch_api()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._is_on = False
        self.switch_api()

    def read_status(self):

        _LOGGER.warning("fan read_status called device_id %s relay_no %s",
                        self.device_id, self.relay_no)
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
            if data["brightness"]:
                if data["state"] == "OFF":
                    self.current_speed = 0
                else:
                    self.current_speed = int(data["brightness"])

            if data["state"] and data["state"] == "ON":
                self._is_on = True
            elif data["state"] and data["state"] == "OFF":
                self._is_on = False
            _LOGGER.warning("read_status called device_id %s relay_no %s response state %s and status %s",
                            self.device_id, self.relay_no, data["state"], data["status"])
        except Exception as e:
            self.is_available = False
            _LOGGER.error("fan read_status exception")

    def switch_api(self):
        """ Switch Device on and off"""
        _LOGGER.warning("switch_api called device_id %s relay_no %s speed %s , status %s",
                        self.device_id, self.relay_no, self.current_speed, self.is_on)
        current_speed = 100
        # try:
        if self.current_speed > 1 and self.current_speed <= 33:
            current_speed = 33
        elif self.current_speed > 33 and self.current_speed <= 66:
            current_speed = 66
        elif self.current_speed > 66:
            current_speed = 100

        payload = {
            "request": {
                "state": 1 if self._is_on == True and self.current_speed > 0 else 0
            },
            "deviceNumber": int(self.relay_no)
        }

        if self.is_on != False:
            payload["request"]["brightness"] = current_speed

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.token
        }

        response = requests.request(
            "POST", self.url, data=json.dumps(payload), headers=headers)

            # _LOGGER.warning("switch_api result",response.text)
        # except Exception as e:
        #     self.is_available = False
        #     _LOGGER.error("Exception on switch_api")
