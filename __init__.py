import logging
import functools
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from .const import DOMAIN
from .control import send_time_command, send_set_temp_command

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    # Get the IP and port from the configuration
    ip = config[DOMAIN]["ip"]
    port = config[DOMAIN]["port"]

    # Store the latest_message in hass.data
    hass.data[DOMAIN] = {"latest_message": None, "ip": ip, "port": port}

    hass.services.async_register(
        DOMAIN,
        "send_time_command",
        functools.partial(send_time_command, ip=ip, port=port),
    )

    hass.services.async_register(
        DOMAIN,
        "send_set_temp_command",
        functools.partial(send_set_temp_command, ip=ip, port=port),
    )


    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[DOMAIN]["latest_message"] = None
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
