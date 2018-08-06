"""
Connect to a BL-NET via it's web interface and read and write data
TODO: as component
"""
import logging

from homeassistant.const import (
    STATE_UNKNOWN)
from homeassistant.components.switch import SwitchDevice

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'blnet'

MODE = 'mode'
FRIENDLY_NAME = 'friendly_name'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the BLNET component"""

    if discovery_info is None:
        _LOGGER.error("No BL-Net communication configured")
        return False

    switch_id = discovery_info['id']
    blnet_id = discovery_info['ent_id']
    comm = hass.data['{}_data'.format(DOMAIN)]

    add_devices([BLNETSwitch(hass, switch_id, blnet_id, comm)], True)
    return True


class BLNETSwitch(SwitchDevice):
    """
    Representation of a switch that toggles a digital output of the UVR1611.
    """

    def __init__(self, switch_id, blnet_id, comm):
        """Initialize the MQTT switch."""
        self._blnet_id = blnet_id
        self._id = switch_id
        self.communication = comm
        self._name = blnet_id
        self._friendly_name = blnet_id
        self._state = False
        self._state = None
        self._icon = None
        self._mode = STATE_UNKNOWN

    def update(self):
        """Get the latest data from communication device """
        sensor_data = self.communication.data.get(self._blnet_id)

        if sensor_data is None:
            return

        self._friendly_name = sensor_data.get('friendly_name')
        if sensor_data.get('value') == 'EIN':
            self._state = 'on'
        # Nonautomated switch, toggled off => switch off
        else:
            self._state = 'off'
        self._icon = sensor_data.get('icon')
        self._mode = sensor_data.get('mode')

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the state of the device."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attrs = {}

        attrs[MODE] = self._mode
        attrs[FRIENDLY_NAME] = self._friendly_name
        return attrs

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self.communication.turn_on(self._id)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.communication.turn_off(self._id)
