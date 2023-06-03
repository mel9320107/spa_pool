# spa_pool

This code runs a barebones Home Assistant integration with a Balboa Spa and a Elfin-EW11A-0 from Hi-Flying Technology WiFi-Serial adapter installed according to the instructions here:

https://github.com/jshank/bwalink

To expand the code and add more features, this site is very useful.

https://github.com/ccutrer/balboa_worldwide_app/wiki

I wrote this code, because I couldn't find an integration to run on Home Assistant that has been installed on a Raspberry Pi with the standard install. Other repositories seem to need separate docker containers or Ruby and I couldn't figure out how to run these with my installation. Some of the integrations I tried wouldn't initialise properly (perhaps because I wasn't using the Balboa branded WiFi adapter). I could control the spa through the command line, but ran into issues automating piped commands in Home Assistant. When ChatGPT came out I wondered if I could use it to write an integration in Python. I have no Python training so it has been a steep learning curve, but I'm amazed ChatGPT 4.0 has helped me get something that works for me.

The integration creates a platform that has attributes for all the fields in the Spa Status Message. This gets updated every 30 seconds, so is a bit laggy. It also provides the ability to make service calls to change the temperature of the spa and update the time.

## Installation Instructions 

* Make a directory called spa_pool in custom_components

* Copy all the files as named into the spa_pool directory

* Restart Home Assistant (If you don't do this before changing your configuration.yaml, home assistant will throw an error).

* Find IP address of WiFi adapter from your router and port it is broadcasting from by logging into serial adapter from a browser window.

* In configuration.yaml (replace with your IP and port)
<pre>
spa_pool:
  ip: 192.168.0.100
  port: 4257

automation: !include automations.yaml
sensor: !include sensor.yaml
input_number: !include input_number.yaml
</pre>

* In sensor.yaml
<pre>
- platform: spa_pool
</pre>

Restart Home Assistant to see if an entity called sensor.spa_pool_rs_485_sensor is created.

* In automations.yaml
<pre>
- id: 'any_unique_number'
  alias: Spa_set_temp
  description: ''
  trigger:
  - platform: state
    entity_id:
    - input_number.spa_set_temp
    for:
      hours: 0
      minutes: 0
      seconds: 2
  condition: []
  action:
  - service: spa_pool.send_set_temp_command
    data:
      set_temp: '{{ states(''input_number.spa_set_temp'') }}'
  mode: single
- id: 'any_unique_number'
  alias: Initialise Spa Set Temp
  description: ''
  trigger:
  - platform: state
    entity_id:
    - sensor.spa_pool_rs_485_sensor
    attribute: set_temperature
    for:
      hours: 0
      minutes: 1
      seconds: 0
  condition: []
  action:
  - service: automation.turn_off
    data:
      stop_actions: true
    target:
      entity_id: automation.spa_set_temp
  - service: input_number.set_value
    data:
      value: '{{ state_attr(''sensor.spa_pool_rs_485_sensor'', ''set_temperature'')
        }}'
    target:
      entity_id: input_number.spa_set_temp
  - service: automation.turn_on
    data: {}
    target:
      entity_id: automation.spa_set_temp
  mode: single
</pre>

* In input_number.yaml

<pre>
spa_set_temp:
  name: Spa Set Temp Control
  min: 26.5
  max: 40
  step: 0.5
</pre>

*Restart Home Assistant if needed to load in all the new yaml

* In Lovelace make a manual card with the following yaml 
<pre>
type: vertical-stack
cards:
  - square: false
    type: grid
    title: Spa Sensors
    cards:
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        name: State
        state_color: false
        unit: ' '
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        attribute: set_temperature
        name: Set
        unit: oC
        state_color: false
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        attribute: spa_time
        name: Time
        state_color: false
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        attribute: heating_state
        name: Heating
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        attribute: current_temperature
        name: Current
        unit: oC
        state_color: false
      - type: entity
        entity: sensor.spa_pool_rs_485_sensor
        attribute: reminder_type
        state_color: false
        name: Reminder
  - type: entities
    entities:
      - entity: input_number.spa_set_temp
    title: Set Spa Temp - ~30s to update
</pre>

<img width="370" alt="Screen Shot 2023-06-03 at 4 55 02 pm" src="https://github.com/mel9320107/spa_pool/assets/54464040/fb1afcac-95e8-4ba5-9f2c-6922bbcbe065">

Good luck!
