import asyncio
import logging
import re
import binascii
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN
from .checksum import calculate_checksum

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([SpaPoolSensor(hass)])

class SpaPoolSensor(SensorEntity):
    def __init__(self, hass):
        self._hass = hass
        self._state = None
        self._name = "Spa Pool RS-485 Sensor"
        self._unit_of_measurement = "Message"
        self._attributes = {}

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def _async_handle_event(self, event):
        """Handle the custom event."""
        await self.async_update()

    async def async_read_latest_message(self):
        try:
            # Get the IP and port from hass.data[DOMAIN]
            ip = self.hass.data[DOMAIN]["ip"]
            port = self.hass.data[DOMAIN]["port"]

            # Connect to the RS-485 WiFi module
            reader, writer = await asyncio.open_connection(ip, port)

            # Read the data stream
            data_stream = await reader.read(1024)

            # Close the connection
            writer.close()

        except Exception as e:
            _LOGGER.error(f"Failed to read latest message due to: {e}")
            await asyncio.sleep(30)  # delay before trying to reconnect
            return await self.async_read_latest_message()  # Recursive call

        # Split the data stream using the '7e' delimiter
        messages = data_stream.split(b'\x7e')

        # Filter the messages based on the specified hexadecimal sequence
        target_messages = [msg for msg in messages if msg.startswith(b'\x1d\xff\xaf\x13')]

        # Calculate the checksum of a message and compare it with the checksum in the message
        def is_valid_checksum(message):
            if len(message) < 4:  # Check if the message has at least 4 bytes (3 bytes for data and 1 byte for checksum)
                return False
            data = message[:-1]  # Extract the data bytes (all bytes except the last one)
            checksum = message[-1]  # Extract the checksum byte (the last byte)
            calculated_checksum = calculate_checksum(data, len(data))  # Calculate the checksum using the checksum.py function
            return calculated_checksum == checksum

        # Remove messages with invalid checksums from the list
        valid_target_messages = [msg for msg in target_messages if is_valid_checksum(msg)]

        # Get the first message (if there are any)
        target_message = valid_target_messages[0] if valid_target_messages else b''

        return target_message

    def decode_message(self, message):
        message_bytearray = bytearray(message)

        # Position 13 (Flags Byte):
        flags_byte_13 = message_bytearray[13]
        temp_scale = "°F" if (flags_byte_13 & 0x01) == 0 else "°C"
        temp_conversion_factor = 1 if temp_scale == "°F" else 0.5
        filter_mode = (flags_byte_13 >> 3) & 0x03
        filter_mode_str = ["OFF", "Cycle 1", "Cycle 2", "Cycle 1 and 2"][filter_mode]
        panel_locked = "No" if (flags_byte_13 & 0x20) == 0 else "Yes"

        # Position 4:
        spa_state_code = message_bytearray[4]
        if spa_state_code == 0x00:
            spa_state = "Running"
        elif spa_state_code == 0x01:
            spa_state = "Initializing"
        elif spa_state_code == 0x05:
            spa_state = "Hold Mode"
        elif spa_state_code == 0x14:
            spa_state = "A/B Temps ON"
        elif spa_state_code == 0x17:
            spa_state = "Test Mode"
        else:
            spa_state = "Unknown"

        # Position 5:
        init_mode_code = message_bytearray[5]
        if init_mode_code == 0x00:
            init_mode = "Idle"
        elif init_mode_code == 0x01:
            init_mode = "Priming Mode"
        elif init_mode_code == 0x02:
            init_mode = "Post-Settings Reset"
        elif init_mode_code == 0x03:
            init_mode = "Reminder"
        elif init_mode_code == 0x04:
            init_mode = "Stage 1"
        elif init_mode_code == 0x05:
            init_mode = "Stage 3"
        elif init_mode_code == 0x42:
            init_mode = "Stage 2"
        else:
            init_mode = "Unknown"

        # Position 6 and 9:
        spa_status_code = message_bytearray[9]
        if spa_status_code == 0:
            spa_status = "Ready"
            current_temperature = int(message_bytearray[6]) * temp_conversion_factor
        elif spa_status_code == 1:
            spa_status = "Rest"
            current_temperature = "~"
        elif spa_status_code == 3:
            spa_status = "Ready-In-Rest"
            current_temperature = int(message_bytearray[6]) * temp_conversion_factor
        else:
            spa_status = "Unknown"
            current_temperature = int(message_bytearray[6]) * temp_conversion_factor

        # Position 7, 8 and 13 (clock mode):
        clock_mode = (message_bytearray[13] >> 1) & 0x01
        hours = message_bytearray[7]
        minutes = message_bytearray[8]

        if clock_mode == 0:  # 12-hour mode
            am_pm = "AM" if hours < 12 else "PM"
            hours = hours % 12
            if hours == 0:
                hours = 12
            spa_time = f"{hours:02d}:{minutes:02d} {am_pm}"
        else:  # 24-hour mode
            spa_time = f"{hours:02d}:{minutes:02d}"

        # Position 10:
        reminder_type_code = message_bytearray[10]

        # Convert the reminder type code to a human-readable string
        if reminder_type_code == 0x00:
            reminder_type = "None"
        elif reminder_type_code == 0x04:
            reminder_type = "Clean filter"
        elif reminder_type_code == 0x0A:
            reminder_type = "Check the pH"
        elif reminder_type_code == 0x09:
            reminder_type = "Check the sanitizer"
        else:
            reminder_type = "Unknown"

        # Decode Position 11
        position_11 = message_bytearray[11]
        sensor_ab_temperatures = (message_bytearray[25] >> 1) & 0x1
        hold_mode = message_bytearray[4] == 0x05
        test_mode = message_bytearray[4] == 0x17
        
        if sensor_ab_temperatures:
            sensor_a_temperature = position_11 * temp_conversion_factor
        elif hold_mode:
            hold_timer = position_11
        elif test_mode:
            test_mode =position_11
        else:
            sensor_a_temperature = position_11
        
        # Decode Position 12
        position_12 = message_bytearray[12]

        if sensor_ab_temperatures:
            sensor_b_temperature = position_12 * temp_conversion_factor
        else:
            sensor_b_temperature = "~"

        # Position 14 (Flags Byte):
        flags_byte_14 = message_bytearray[14]
        temp_range = "Low" if (flags_byte_14 & 0x04) == 0 else "High"
        heating_state = (flags_byte_14 >> 4) & 0x03
        heating_state_str = ["OFF", "Heating", "Heat Waiting"][heating_state]

        # Position 15 and 16 (Flags Bytes):
        flags_byte_15 = message_bytearray[15]
        flags_byte_16 = message_bytearray[16]

        # Calculate pump statuses for all pumps
        pump_statuses = [(flags_byte_15 >> (2 * i)) & 0x03 for i in range(4)] + [(flags_byte_16 >> (2 * i)) & 0x03 for i in range(2)]

        pump_status_strs = ["OFF", "Low", "High"]

        # Position 17:
        position_17 = message_bytearray[17]
        circulation_pump_status = (position_17 & 0x01)  # 0=OFF, 1=ON
        blower_status = (position_17 & 0x0C) >> 2  # 0=OFF, 3=ON

        # Position 18:
        light1_status = (message_bytearray[18] >> 0) & 0x3
        light2_status = (message_bytearray[18] >> 2) & 0x3

        # Position 19:
        mister_status = message_bytearray[19]
        if mister_status == 0:
            mister = "OFF"
        elif mister_status == 1:
            mister = "ON"
        else:
            mister = "Unknown"

        # Position 24:
        set_temperature = int(message_bytearray[24]) * temp_conversion_factor

        # Position 25:
        sensor_ab_temperatures = (message_bytearray[25] >> 1) & 0x1
        timeouts = (message_bytearray[25] >> 2) & 0x1
        settings_locked = (message_bytearray[25] >> 3) & 0x1

        return {
            "current_temperature": current_temperature,
            "set_temperature": set_temperature,
            "spa_time": spa_time,
            "spa_status": spa_status,
            "spa_state" : spa_state,
            "init_mode": init_mode,
            "reminder_type": reminder_type,
            "mister": mister,
            "temp_scale": temp_scale,
            "clock_mode": "12hr" if clock_mode == 0 else "24hr",
            "filter_mode": filter_mode_str,
            "panel_locked": panel_locked,
            "temp_range": temp_range,
            "heating_state": heating_state_str,
            "pump1_status": pump_status_strs[pump_statuses[0]],
            "pump2_status": pump_status_strs[pump_statuses[1]],
            "pump3_status": pump_status_strs[pump_statuses[2]],
            "pump4_status": pump_status_strs[pump_statuses[3]],
            "pump5_status": pump_status_strs[pump_statuses[4]],
            "pump6_status": pump_status_strs[pump_statuses[5]],
            "circulation_pump_status": "ON" if circulation_pump_status else "OFF",
            "blower_status": "ON" if blower_status == 3 else "OFF",
            "light1_status": "OFF" if light1_status == 0 else "ON",
            "light2_status": "OFF" if light2_status == 0 else "ON",
            "sensor_a_temperature": sensor_a_temperature if sensor_ab_temperatures else (hold_timer if hold_mode else ("Test Mode" if test_mode else "~")),
            "sensor_b_temperature": sensor_b_temperature,

        }

    async def async_update(self):
        message = await self.async_read_latest_message()
        decoded_data = self.decode_message(message)  # Call the decode_message function
        self._state = decoded_data["spa_status"]  # Set the state to spa_status
        self._attributes["raw_message"] = binascii.hexlify(message).decode('utf-8')  # Save the current state as an attribute and convert it to a string
        self._attributes["current_temperature"] = decoded_data["current_temperature"]
        self._attributes["set_temperature"] = decoded_data["set_temperature"]
        self._attributes["spa_time"] = decoded_data["spa_time"]
        self._attributes["spa_state"] = decoded_data["spa_state"]
        self._attributes["init_mode"] = decoded_data["init_mode"]
        self._attributes["reminder_type"] = decoded_data["reminder_type"]  # Add this line to store reminder_type as an attribute
        self._attributes["mister"] = decoded_data["mister"]  # Add this line to store mister as an attribute
        self._attributes["temp_scale"] = decoded_data["temp_scale"]
        self._attributes["clock_mode"] = decoded_data["clock_mode"]
        self._attributes["filter_mode"] = decoded_data["filter_mode"]
        self._attributes["panel_locked"] = decoded_data["panel_locked"]
        self._attributes["temp_range"] = decoded_data["temp_range"]
        self._attributes["heating_state"] = decoded_data["heating_state"]
        self._attributes["pump1_status"] = decoded_data["pump1_status"]
        self._attributes["pump2_status"] = decoded_data["pump2_status"]
        self._attributes["pump3_status"] = decoded_data["pump3_status"]
        self._attributes["pump4_status"] = decoded_data["pump4_status"]
        self._attributes["pump5_status"] = decoded_data["pump5_status"]
        self._attributes["pump6_status"] = decoded_data["pump6_status"]
        self._attributes["circulation_pump_status"] = decoded_data["circulation_pump_status"]  # Add the circulation pump status attribute
        self._attributes["blower_status"] = decoded_data["blower_status"]  # Add the blower status attribute
        self._attributes["light1_status"] = decoded_data["light1_status"]
        self._attributes["light2_status"] = decoded_data["light2_status"]
        self._attributes["sensor_a_temperature"] = decoded_data["sensor_a_temperature"]
        self._attributes["sensor_b_temperature"] = decoded_data["sensor_b_temperature"]

        self._hass.data[DOMAIN]["latest_message"] = message


