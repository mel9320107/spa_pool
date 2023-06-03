import asyncio
import datetime
from .checksum import calculate_checksum
import logging
from homeassistant.core import HomeAssistant, ServiceCall


_LOGGER = logging.getLogger(__name__)

async def send_time_command(call: ServiceCall, ip, port):
    try:
        # Connect to the spa
        reader, writer = await asyncio.open_connection(ip, port)

        # Get the current time
        now = datetime.datetime.now()

        # Prepare the time command message (without checksum)
        command = bytearray([0x7E, 0x07, 0x0A, 0xBF, 0x21, now.hour, now.minute])

        # Calculate and append the checksum
        checksum = calculate_checksum(command[1:], len(command) - 1)
        command.append(checksum)

        # Append the delimiter
        command.append(0x7E)

        # Send the time command message
        writer.write(command)
        await writer.drain()

        # Send the time command message
        writer.close()
        await writer.wait_closed()

    except Exception as e:
        _LOGGER.error(f"Error sending time command: {e}")

ATTR_NAME = "set_temp"
async def send_set_temp_command(call: ServiceCall, ip, port):

    set_temp = call.data.get(ATTR_NAME, 0)

    try:
        # Connect to the spa
        reader, writer = await asyncio.open_connection(ip, port)

        # Prepare the set_temp command message (without checksum)
        command = bytearray([0x7E, 0x06, 0x0A, 0xBF, 0x20, round(set_temp * 2)])

        # Calculate and append the checksum
        checksum = calculate_checksum(command[1:], len(command) - 1)
        command.append(checksum)

        # Append the delimiter
        command.append(0x7E)

        # Send the set_temp command message
        writer.write(command)
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    except Exception as e:
        _LOGGER.error(f"Error sending time command: {e}")
