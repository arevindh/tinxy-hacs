from dataclasses import dataclass
from pprint import pprint


class TinxyException(Exception):
    """Tinxy Exception."""

    def __init__(self, message="Failed") -> None:
        """Init."""
        self.message = message
        super().__init__(self.message)


class TinxyAuthenticationException(TinxyException):
    """Tinxy authentication exception."""


@dataclass
class TinxyHostConfiguration:
    """Tinxy host configuration."""
    api_token: str
    api_url: str | None

    def __post_init__(self):
        if not self.api_token:
            raise TinxyAuthenticationException(
                message="No API token was provided.")
        if not self.api_url:
            raise TinxyException(
                message="No URL, API token to the Tinxy server was provided.")


class TinxyCloud:
    """Tinxy Cloud."""

    DOMAIN = "tinxy"
    devices = []
    disabled_devices = ["EVA_HUB"]
    enabled_list = [
        "WIFI_3SWITCH_1FAN",
        "WIRED_DOOR_LOCK",
        "WIFI_4SWITCH",
        "WIFI_SWITCH",
        "WIRED_DOOR_LOCK_V2",
        "WIFI_4DIMMER",
        "Fan",
        "Dimmable Light",
        "WIFI_SWITCH_V2",
        "WIFI_4SWITCH_V2",
        "WIFI_2SWITCH_V1",
        "WIFI_6SWITCH_V1",
        "WIFI_BULB_WHITE_V1",
        "EVA_BULB",
        "WIFI_SWITCH_1FAN_V1",
    ]

    gtype_light = ["action.devices.types.LIGHT"]
    gtype_switch = ["action.devices.types.SWITCH"]
    gtype_lock = ["action.devices.types.LOCK"]
    typeId_fan = ["WIFI_3SWITCH_1FAN", "Fan", "WIFI_SWITCH_1FAN_V1"]

    def __init__(self, host_config: TinxyHostConfiguration, web_session) -> None:
        """Init."""
        self.host_config = host_config
        self.web_session = web_session

    async def tinxy_request(self, path, payload=None, method="GET"):
        """Execute a request to the Tinxy API.

        Parameters:
            path (str): The API endpoint path.
            payload (dict, optional): The payload for POST requests.
            method (str, optional): The HTTP method to use (default is GET).

        Returns:
            dict: API response as a JSON object.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.host_config.api_token}"
        }

        # Add source info to payload if present
        if payload:
            payload["source"] = "Home Assistant"

        try:
            async with self.web_session.request(
                    method=method,
                    url=f"{self.host_config.api_url}{path}",
                    json=payload,
                    headers=headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    raise TinxyException(
                        f"API call failed with status {resp.status}")
        except Exception as e:
            raise TinxyException(f"API call failed: {str(e)}")

    async def sync_devices(self):
        """Read all devices from server."""
        device_list = []
        result = await self.tinxy_request("v2/devices/")
        for item in result:
            device_list = device_list + (self.parse_device(item))
        self.devices = device_list

    def list_switches(self):
        """List switches."""
        return [d for d in self.devices if d["device_type"] == "Switch"]

    def list_lights(self):
        """List light."""
        return [d for d in self.devices if d["device_type"] == "Light"]

    def list_all_devices(self):
        return self.devices

    def list_fans(self):
        """List fans."""
        return [d for d in self.devices if d["device_type"] == "Fan"]

    def list_locks(self):
        """List lokcs."""
        return [d for d in self.devices if d["gtype"] in self.gtype_lock]

    async def get_device_state(self, id, device_number):
        """Get device state."""
        return await self.tinxy_request(
            "v2/devices/" + id + "/state?deviceNumber=" + device_number
        )

    def state_to_val(self, state):
        """State to value."""
        if state == "ON":
            return True
        return False

    async def get_all_status(self):
        status_data = await self.tinxy_request("v2/devices_state")
        device_status = {}

        for status in status_data:
            device_id_base = status["_id"]
            state_data = status.get("state", {})

            if isinstance(state_data, list):
                for item in state_data:
                    single_device = {}
                    device_number = item.get("number", 1)
                    device_id = f"{device_id_base}-{device_number}"
                    single_device["state"] = self.state_to_val(
                        item.get("state", {}).get("state"))
                    single_device["status"] = item.get(
                        "state", {}).get("status")
                    single_device["brightness"] = item.get(
                        "state", {}).get("brightness")
                    device_status[device_id] = single_device

            elif isinstance(state_data, dict):
                single_device = {}
                device_id = f"{device_id_base}-1"
                single_device["state"] = self.state_to_val(
                    state_data.get("state"))
                single_device["status"] = state_data.get("status")
                single_device["brightness"] = state_data.get("brightness")
                device_status[device_id] = single_device

        return device_status

        return device_status

    async def set_device_state(self, itemid, device_number, state, brightness=None):
        """Set device state."""
        payload = {
            "request": {"state": state},
            "deviceNumber": device_number
        }

        # Add brightness to payload if provided
        if brightness is not None:
            payload["request"]["brightness"] = brightness

        return await self.tinxy_request(
            f"v2/devices/{itemid}/toggle",
            payload=payload,
            method="POST"
        )

    def get_device_info(self, device):
        """Parse device info."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (self.DOMAIN, device["_id"])
            },
            "name": device["name"],
            "manufacturer": "Tinxy.in",
            "model": device["typeId"]["long_name"],
            "sw_version": device["firmwareVersion"],
            # "via_device": (hue.DOMAIN, self.api.bridgeid),
        }

    def parse_device(self, data):
        """Parse device."""

        def create_device(device_id, relay_no, name, tinxy_type, gtype, traits, device_info):
            device_type = self.get_device_type(tinxy_type, relay_no - 1)
            return {
                "id": f"{device_id}-{relay_no}",
                "device_id": device_id,
                "name": name,
                "relay_no": relay_no,
                "gtype": gtype,
                "traits": traits,
                "device_type": device_type,
                "user_device_type": device_type,
                "device_desc": data["typeId"]["long_name"],
                "tinxy_type": tinxy_type,
                "icon": self.icon_generate(device_type),
                "device": device_info,
            }

        devices = []
        device_info = self.get_device_info(data)
        device_id = data["_id"]
        tinxy_type = data["typeId"]["name"]
        name = data["name"]
        gtype = data["typeId"]["gtype"]
        traits = data["typeId"]["traits"]

        if tinxy_type not in self.enabled_list:
            print(f"Unknown type: {tinxy_type}")
            return devices

        if not data["devices"]:
            devices.append(create_device(device_id, 1, name,
                           tinxy_type, gtype, traits, device_info))
        else:
            for relay_no, node_name in enumerate(data["devices"], start=1):
                device_name = f"{name} {node_name}"
                devices.append(create_device(
                    device_id, relay_no, device_name, tinxy_type, gtype, traits, device_info))

        return devices

    def get_device_type(self, tinxy_type, itemid):
        """Generate device type."""
        light_list = ["Tubelight", "LED Bulb"]
        if tinxy_type in self.typeId_fan and itemid == 0:
            return "Fan"
        elif tinxy_type in light_list:
            return "Light"
        elif tinxy_type in self.gtype_lock:
            return "Switch"
        else:
            return "Switch"

    def icon_generate(self, devicetype):
        """Generate icon name."""
        icon_mapping = {
            "Heater": "mdi:radiator",
            "Tubelight": "mdi:lightbulb-fluorescent-tube",
            "LED Bulb": "mdi:lightbulb",
            "Dimmable Light": "mdi:lightbulb",
            "LED Dimmable Bulb": "mdi:lightbulb",
            "EVA_BULB": "mdi:lightbulb",
            "Music System": "mdi:music",
            "Fan": "mdi:fan",
            "Socket": "mdi:power-socket-eu",
            "TV": "mdi:television",
        }
        return icon_mapping.get(devicetype, "mdi:toggle-switch")
