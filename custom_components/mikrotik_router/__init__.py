"""Mikrotik Router integration."""

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import ConfigEntryNotReady

from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
)

from .const import (
    PLATFORMS,
    DOMAIN,
    DATA_CLIENT,
    RUN_SCRIPT_COMMAND,
)
from .mikrotik_controller import MikrotikControllerData

_LOGGER = logging.getLogger(__name__)

SCRIPT_SCHEMA = vol.Schema(
    {vol.Required("router"): cv.string, vol.Required("script"): cv.string}
)


# ---------------------------
#   async_setup
# ---------------------------
async def async_setup(hass, _config):
    """Set up configured Mikrotik Controller."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CLIENT] = {}
    return True


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(hass, config_entry):
    """Set up Mikrotik Router as config entry."""
    controller = MikrotikControllerData(hass, config_entry)
    await controller.async_hwinfo_update()
    if not controller.connected():
        raise ConfigEntryNotReady(f"Cannot connect to host")

    await controller.async_update()

    if not controller.data:
        raise ConfigEntryNotReady()

    await controller.async_init()
    hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id] = controller

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "binary_sensor")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "device_tracker")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "switch")
    )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "button")
    )

    hass.services.async_register(
        DOMAIN, RUN_SCRIPT_COMMAND, controller.run_script, schema=SCRIPT_SCHEMA
    )

    device_registry = await hass.helpers.device_registry.async_get_registry()
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(DOMAIN, f"{controller.data['routerboard']['serial-number']}")},
        manufacturer=controller.data["resource"]["platform"],
        model=controller.data["routerboard"]["model"],
        name=f"{config_entry.data[CONF_NAME]} {controller.data['routerboard']['model']}",
        sw_version=controller.data["resource"]["version"],
        configuration_url=f"http://{config_entry.data[CONF_HOST]}",
        identifiers={
            DOMAIN,
            "serial-number",
            f"{controller.data['routerboard']['serial-number']}",
            "sensor",
            f"{config_entry.data[CONF_NAME]} {controller.data['routerboard']['model']}",
        },
    )

    return True


# ---------------------------
#   async_unload_entry
# ---------------------------
async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    controller = hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id]
    await controller.async_reset()
    hass.services.async_remove(DOMAIN, RUN_SCRIPT_COMMAND)
    hass.data[DOMAIN][DATA_CLIENT].pop(config_entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    return unload_ok
