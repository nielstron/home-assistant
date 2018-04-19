"""
Connect to a BL-NET via it's web interface and read and write data
TODO: as component
"""
import logging

import voluptuous as vol
from homeassistant.helpers.discovery import load_platform

from homeassistant.const import (
    CONF_RESOURCE, CONF_PASSWORD, CONF_SCAN_INTERVAL)
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from datetime import datetime
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = [
    'pyblnet==0.4.1'
    ]

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'blnet'

CONF_NODE = 'can_node'
# means don't change the current setting
# for example if there is only one UVR1611 connected
DEFAULT_NODE = 10000
# scan every 6 minutes per default
DEFAULT_SCAN_INTERVAL = 360

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_RESOURCE): cv.url,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NODE, default=DEFAULT_NODE): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL,
                     default=DEFAULT_SCAN_INTERVAL): cv.positive_int
        })
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the BLNET component"""

    from pyblnet import BLNET, test_blnet

    config = config[DOMAIN]
    resource = config.get(CONF_RESOURCE)
    password = config.get(CONF_PASSWORD)
    can_node = config.get(CONF_NODE)
    scan_interval = config.get(CONF_SCAN_INTERVAL)

    if test_blnet(resource) is False:
        _LOGGER.error("No BL-Net reached at %", resource)
        return False

    # Initialize the BL-NET sensor
    blnet = BLNET(resource, password)
    # Can-Bus node
    node = can_node

    # set the communication entity
    # TODO
    hass.data[DOMAIN + '_data'] = BLNETComm(blnet, node)

    # make sure the communication device gets updated once in a while
    def fetch_data(*arg):
        hass.data[DOMAIN + '_data'].update()

    fetch_data()
    async_track_time_interval(hass,
                              fetch_data,
                              timedelta(seconds=scan_interval))

    # Get the latest data from REST API and load
    # sensors and switches accordingly
    blnet.log_in()
    # only change active node if this is desired
    if node != DEFAULT_NODE:
        blnet.set_node(node)

    # digital data comes from switches => create switches
    digital_data = blnet.read_digital_values()
    # analog data comes from sensors => create sensors
    analog_data = blnet.read_analog_values()

    # iterate through the list and create a sensor for every value
    for sensor in analog_data:
        disc_info = {
            'ent_id': '{}_analog_{}'.format(DOMAIN, sensor['id']),
            'id': sensor['id']
            }
        load_platform(hass, 'sensor', DOMAIN, disc_info)

    # iterate through the list and create a sensor for every value
    for sensor in digital_data:
        disc_info = {
            'ent_id': '{}_digital_{}'.format(DOMAIN, sensor['id']),
            'id': sensor['id']
            }
        load_platform(hass, 'switch', DOMAIN, disc_info)

    return True


class BLNETComm(object):
    """Implementation of a BL-NET - UVR1611 communication component"""

    def __init__(self, blnet, node):
        self.blnet = blnet
        self.node = node
        # Map id -> attributes
        self.data = dict()
        self._last_updated = None

    def _node_check(self):
        if self.node != DEFAULT_NODE:
            return self.blnet.set_node(self.node)
        return True

    def turn_on(self, switch_id):
        if self.blnet.log_in():
            # only change active node if this is desired
            self._node_check()
            self.blnet.set_digital_value(switch_id, 'EIN')

    def turn_off(self, switch_id):
        if self.blnet.log_in():
            # only change active node if this is desired
            self._node_check()
            self.blnet.set_digital_value(switch_id, 'AUS')

    def turn_auto(self, switch_id):
        if self.blnet.log_in():
            # only change active node if this is desired
            self._node_check()
            self.blnet.set_digital_value(switch_id, 'AUTO')

    def last_updated(self):
        return self._last_updated

    def update(self):
        """Get the latest data from REST API and update the state."""
        if not self.blnet.log_in():
            return None
        # only change active node if this is desired
        self._node_check()

        # digital data comes from switches => create switches
        digital_data = self.blnet.read_digital_values()
        # analog data comes from sensors => create sensors
        analog_data = self.blnet.read_analog_values()

        if analog_data is not None:
            # iterate through the list and create a sensor for every value
            for sensor in analog_data:
                attributes = dict()
                entity_id = '{}_analog_{}'.format(DOMAIN, sensor['id'])
                attributes['value'] = sensor['value']

                attributes.setdefault('unit_of_measurement',
                                      sensor['unit_of_measurement'])
                attributes.setdefault('friendly_name', sensor['name'])
                attributes.setdefault('icon', 'mdi:thermometer')

                self.data[entity_id] = attributes

        if digital_data is not None:
            # iterate through the list and create a sensor for every value
            for sensor in digital_data:
                attributes = dict()
                entity_id = '{}_digital_{}'.format(DOMAIN, sensor['id'])

                attributes.setdefault('friendly_name', sensor['name'])
                attributes['mode'] = sensor['mode']
                attributes['value'] = sensor['value']
                # Change the symbol according to current mode and setting
                # Automated switch => gear symbol
                if sensor['mode'] == 'AUTO':
                    attributes['icon'] = 'mdi:settings'
                # Nonautomated switch, toggled on => switch on
                elif sensor['mode'] == 'EIN':
                    attributes['icon'] = 'mdi:toggle-switch'
                # Nonautomated switch, toggled off => switch off
                else:
                    attributes['icon'] = 'mdi:toggle-switch-off'

                self.data[entity_id] = attributes

        self._last_updated = datetime.now()
