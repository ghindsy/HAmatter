"""Constants used be the HomeKit component."""
MANUFACTURER = 'HomeAssistant'

# Services
SERV_ACCESSORY_INFO = 'AccessoryInformation'
SERV_BRIDGING_STATE = 'BridgingState'
SERV_TEMPERATURE_SENSOR = 'TemperatureSensor'
SERV_WINDOW_COVERING = 'WindowCovering'

# Characteristics
CHAR_ACC_IDENTIFIER = 'AccessoryIdentifier'
CHAR_CATEGORY = 'Category'
CHAR_CURRENT_POSITION = 'CurrentPosition'
CHAR_CURRENT_TEMPERATURE = 'CurrentTemperature'
CHAR_LINK_QUALITY = 'LinkQuality'
CHAR_MANUFACTURER = 'Manufacturer'
CHAR_MODEL = 'Model'
CHAR_POSITION_STATE = 'PositionState'
CHAR_REACHABLE = 'Reachable'
CHAR_SERIAL_NUMBER = 'SerialNumber'
CHAR_TARGET_POSITION = 'TargetPosition'

# Service: SecuritySystem
SERV_SECURITY_SYSTEM = 'SecuritySystem'
CHAR_CURRENT_SECURITY_STATE = 'SecuritySystemCurrentState'
CHAR_TARGET_SECURITY_STATE = 'SecuritySystemTargetState'

# Service: Thermostat
SERV_THERMOSTAT = 'Thermostat'
CHAR_CURRENT_HEATING_COOLING = 'CurrentHeatingCoolingState'
CHAR_TARGET_HEATING_COOLING = 'TargetHeatingCoolingState'
# CHAR_CURRENT_TEMPERATURE is already defined
CHAR_TARGET_TEMPERATURE = 'TargetTemperature'
CHAR_TEMP_DISPLAY_UNITS = 'TemperatureDisplayUnits'

# Service: Switch
SERV_SWITCH = 'Switch'
CHAR_ON = 'On'

# Properties
PROP_CELSIUS = {'minValue': -273, 'maxValue': 999}
