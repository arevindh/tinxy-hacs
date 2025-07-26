"""Tinxy Cloud API integration module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class TinxyException(Exception):
    """Base exception for Tinxy API errors."""

    def __init__(self, message: str = "Failed") -> None:
        """Initialize the exception with a message."""
        self.message = message
        super().__init__(self.message)


class TinxyAuthenticationException(TinxyException):
    """Exception raised for authentication errors."""
    pass


@dataclass
class TinxyHostConfiguration:
    """Configuration for Tinxy host connection."""

    api_token: str
    api_url: str | None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.api_token:
            raise TinxyAuthenticationException("No API token was provided.")
        if not self.api_url:
            raise TinxyException("No API URL was provided.")


class TinxyCloud:
    """Tinxy Cloud API client for Home Assistant integration."""

    DOMAIN: str = "tinxy"
    
    # Device type constants
    DISABLED_DEVICES: List[str] = ["EVA_HUB"]
    ENABLED_DEVICES: List[str] = [
        "Dimmable Light", "EM_DOOR_LOCK", "EVA_BULB", "EVA_BULB_WW", "Fan",
        "WIFI_2SWITCH_V1", "WIFI_2SWITCH_V3", "WIFI_3SWITCH_1FAN", "WIFI_3SWITCH_1FAN_V3",
        "WIFI_4DIMMER", "WIFI_4SWITCH", "WIFI_4SWITCH_V2", "WIFI_4SWITCH_V3",
        "WIFI_6SWITCH_V1", "WIFI_6SWITCH_V3", "WIFI_BULB_WHITE_V1", "WIFI_SWITCH",
        "WIFI_SWITCH_1FAN_V1", "WIFI_SWITCH_V2", "WIFI_SWITCH_V3", "WIRED_DOOR_LOCK",
        "WIRED_DOOR_LOCK_V2", "WIRED_DOOR_LOCK_V3"
    ]
    
    # Google device types
    GTYPE_LIGHT: List[str] = ["action.devices.types.LIGHT"]
    GTYPE_SWITCH: List[str] = ["action.devices.types.SWITCH"]
    GTYPE_LOCK: List[str] = ["action.devices.types.LOCK"]
    
    # Type ID mappings
    TYPE_ID_LOCK: List[str] = ["WIRED_DOOR_LOCK_V3"]
    TYPE_ID_EVA: List[str] = ["EVA_BULB_WW", "EVA_BULB"]
    TYPE_ID_FAN: List[str] = ["WIFI_3SWITCH_1FAN", "Fan", "WIFI_SWITCH_1FAN_V1", "WIFI_3SWITCH_1FAN_V3"]
    
    _logger = logging.getLogger(__name__)

    def __init__(self, host_config: TinxyHostConfiguration, web_session: Any) -> None:
        """Initialize TinxyCloud client.
        
        Args:
            host_config: Configuration for API connection
            web_session: HTTP session for making requests
        """
        self.host_config = host_config
        self.web_session = web_session
        self.devices: List[Dict[str, Any]] = []

    async def tinxy_request(
        self, path: str, payload: Optional[Dict[str, Any]] = None, method: str = "GET"
    ) -> Dict[str, Any]:
        """Make a request to the Tinxy API.
        
        Args:
            path: API endpoint path
            payload: Request payload (optional)
            method: HTTP method (default: GET)
            
        Returns:
            JSON response from the API
            
        Raises:
            TinxyException: If the API call fails
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.host_config.api_token}",
        }
        if payload is not None:
            payload["source"] = "Home Assistant"

        try:
            async with self.web_session.request(
                method=method,
                url=f"{self.host_config.api_url}{path}",
                json=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            self._logger.error("Tinxy API [%s] call failed: %s", method, exc)
            raise TinxyException(f"API [{method}] call failed: {exc}") from exc

    async def sync_devices(self) -> None:
        """Synchronize all devices from the server."""
        result = await self.tinxy_request("v2/devices/")
        device_list = []
        for item in result:
            device_list.extend(self.parse_device(item))
        self.devices = device_list

    def list_switches(self) -> List[Dict[str, Any]]:
        """Return a list of all switch devices."""
        return [device for device in self.devices if device["device_type"] == "Switch"]

    def list_lights(self) -> List[Dict[str, Any]]:
        """Return a list of all light devices."""
        return [device for device in self.devices if device["device_type"] == "Light"]

    def list_all_devices(self) -> List[Dict[str, Any]]:
        """Return a list of all devices."""
        return self.devices

    def list_fans(self) -> List[Dict[str, Any]]:
        """Return a list of all fan devices."""
        return [device for device in self.devices if device["device_type"] == "Fan"]

    def list_locks(self) -> List[Dict[str, Any]]:
        """Return a list of all lock devices."""
        return [device for device in self.devices if device["gtype"] in self.GTYPE_LOCK]

    async def get_device_state(self, device_id: str, device_number: str) -> Dict[str, Any]:
        """Get the current state of a device.
        
        Args:
            device_id: The device ID
            device_number: The device number
            
        Returns:
            Device state information
        """
        return await self.tinxy_request(
            f"v2/devices/{device_id}/state?deviceNumber={device_number}"
        )

    def state_to_val(self, state: str) -> bool:
        """Convert string state to boolean value.
        
        Args:
            state: String state ("ON" or "OFF")
            
        Returns:
            Boolean representation of the state
        """
        return state == "ON"

    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all devices.
        
        Returns:
            Dictionary mapping device IDs to their status information
        """
        status_data = await self.tinxy_request("v2/devices_state")
        device_status = {}
        
        for status in status_data:
            if "state" not in status:
                continue
                
            if isinstance(status["state"], list):
                # Handle multi-device status
                for item in status["state"]:
                    device_id = f"{status['_id']}-{item.get('number', 1)}"
                    single_device = self._extract_device_state(item.get("state", {}))
                    if "number" not in item:
                        single_device["item"] = item
                    device_status[device_id] = single_device
            else:
                # Handle single device status
                device_id = f"{status['_id']}-1"
                single_device = self._extract_device_state(status["state"])
                device_status[device_id] = single_device

        return device_status

    def _extract_device_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract device state information from API response.
        
        Args:
            state_data: Raw state data from API
            
        Returns:
            Processed device state information
        """
        single_device = {}
        
        if "state" in state_data:
            single_device["state"] = self.state_to_val(state_data["state"])
        if "status" in state_data:
            single_device["status"] = state_data["status"]
        if "brightness" in state_data:
            single_device["brightness"] = state_data["brightness"]
        if "door" in state_data:  # For lock devices
            single_device["door"] = state_data["door"]
        if "colorTemperatureInKelvin" in state_data:
            single_device["colorTemperatureInKelvin"] = state_data["colorTemperatureInKelvin"]
            
        return single_device

    async def set_device_state(
        self,
        item_id: str,
        device_number: int,
        state: str,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set device state.
        
        Args:
            item_id: Device identifier
            device_number: Device number
            state: Desired state
            brightness: Optional brightness level
            color_temp: Optional color temperature
            
        Returns:
            API response
        """
        payload = {"request": {"state": state}, "deviceNumber": device_number}
        
        if brightness is not None:
            payload["request"]["brightness"] = brightness
        if color_temp is not None:
            payload["request"]["colorTemperatureInKelvin"] = color_temp

        return await self.tinxy_request(
            f"v2/devices/{item_id}/toggle", payload=payload, method="POST"
        )

    def get_device_info(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Parse device information for Home Assistant device registry.
        
        Args:
            device: Raw device data from API
            
        Returns:
            Device information formatted for Home Assistant
        """
        return {
            "identifiers": {(self.DOMAIN, device["_id"])},
            "name": device["name"],
            "manufacturer": "Tinxy.in",
            "model": device["typeId"]["long_name"],
            "sw_version": device["firmwareVersion"],
        }

    def parse_device(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse device data from API response.
        
        Args:
            data: Raw device data from API
            
        Returns:
            List of parsed device dictionaries
        """
        devices = []
        type_id_name = data["typeId"]["name"]

        # Handle single item devices
        if not data["devices"]:
            if type_id_name in self.ENABLED_DEVICES:
                if type_id_name in self.TYPE_ID_EVA:
                    # Handle EVA bulbs
                    device_type = "Light"
                else:
                    # Handle single node devices
                    device_type = self._get_device_type(type_id_name, 0)
                devices.append(self._create_device_dict(data, device_type, 1))
            elif type_id_name in self.DISABLED_DEVICES:
                # Do not report errors for disabled devices
                pass
            else:
                self._logger.warning(
                    "Unknown device %s, please create GitHub issue.",
                    type_id_name
                )
        # Handle multi-node devices
        elif type_id_name in self.ENABLED_DEVICES:
            for item_id, node_name in enumerate(data["devices"]):
                device_type = self._get_device_type(type_id_name, item_id)
                devices.append(
                    self._create_device_dict(
                        data, device_type, item_id + 1, node_name, data["deviceTypes"][item_id]
                    )
                )
        elif type_id_name in self.DISABLED_DEVICES:
            # Do not report errors for disabled devices
            pass
        else:
            self._logger.warning("Unknown multi-node device: %s", type_id_name)

        return devices

    def _create_device_dict(
        self, 
        data: Dict[str, Any], 
        device_type: str, 
        relay_no: int, 
        node_name: Optional[str] = None,
        user_device_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a device dictionary with common structure.
        
        Args:
            data: Raw device data
            device_type: Determined device type
            relay_no: Relay number
            node_name: Optional node name for multi-node devices
            user_device_type: Optional user-defined device type
            
        Returns:
            Formatted device dictionary
        """
        device_name = data["name"]
        if node_name:
            device_name = f"{device_name} {node_name}"
            
        return {
            "id": f"{data['_id']}-{relay_no}",
            "device_id": data["_id"],
            "name": device_name,
            "relay_no": relay_no,
            "gtype": data["typeId"]["gtype"],
            "traits": data["typeId"]["traits"],
            "device_type": device_type,
            "user_device_type": user_device_type or device_type,
            "device_desc": data["typeId"]["long_name"],
            "tinxy_type": data["typeId"]["name"],
            "icon": self._generate_icon(user_device_type or device_type),
            "device": self.get_device_info(data),
        }

    def _get_device_type(self, tinxy_type: str, item_id: int) -> str:
        """Determine the device type based on Tinxy type and item ID.
        
        Args:
            tinxy_type: Tinxy device type identifier
            item_id: Item index for multi-node devices
            
        Returns:
            Device type string
        """
        light_types = {"Tubelight", "LED Bulb", "EVA_BULB_WW"}
        
        if tinxy_type in self.TYPE_ID_FAN and item_id == 0:
            return "Fan"
        elif tinxy_type in light_types:
            return "Light"
        elif tinxy_type in self.TYPE_ID_LOCK:
            return "Lock"
        else:
            return "Switch"

    def _generate_icon(self, device_type: str) -> str:
        """Generate Material Design icon name for device type.
        
        Args:
            device_type: Type of the device
            
        Returns:
            Material Design icon identifier
        """
        icon_mapping = {
            "Heater": "mdi:radiator",
            "Tubelight": "mdi:lightbulb-fluorescent-tube",
            "LED Bulb": "mdi:lightbulb",
            "Dimmable Light": "mdi:lightbulb",
            "LED Dimmable Bulb": "mdi:lightbulb",
            "Music System": "mdi:music",
            "Fan": "mdi:fan",
            "Socket": "mdi:power-socket-eu",
            "TV": "mdi:television",
            "Lock": "mdi:lock",
        }
        
        # Check EVA bulb types
        if device_type in self.TYPE_ID_EVA:
            return "mdi:lightbulb"
            
        return icon_mapping.get(device_type, "mdi:toggle-switch")
