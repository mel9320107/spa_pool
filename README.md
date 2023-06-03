# spa_pool
Balboa Spa - Home Assistant

For use with Home Assistant running on Raspberry Pi - standard install - and Balboa Spa with WiFi serial adapter.

Make a directory called spa_pool in custom_components

Copy all the files as named into the spa_pool directory

Find IP address of WiFi adapter and port it is broadcasting from by logging into serial adapter

In configuration.yaml

spa_pool:
  ip: 192.168.0.101
  port: 4257

In sensor.yaml

- platform: spa_pool

In automations.yaml

- id: '1681800781863'
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
- id: '1681161809824'
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

In input_number.yaml

spa_set_temp:
  name: Spa Set Temp Control
  min: 26.5
  max: 40
  step: 0.5

