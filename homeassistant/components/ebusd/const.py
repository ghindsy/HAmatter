"""Constants for ebus component."""
DOMAIN = 'ebusd'

READ_COMMAND = 'read -m {2} -c {0} {1}\n'
WRITE_COMMAND = 'write -c {0} {1} {2}\n'

"""
  SensorTypes:
  0='decimal', 1='time-schedule', 2='switch', 3='string', 4='value;status'
"""
SENSOR_TYPES = {
    '700': {
        'ActualFlowTemperatureDesired':
            ['Hc1ActualFlowTempDesired', '°C', 'mdi:thermometer', 0],
        'MaxFlowTemperatureDesired':
            ['Hc1MaxFlowTempDesired', '°C', 'mdi:thermometer', 0],
        'MinFlowTemperatureDesired':
            ['Hc1MinFlowTempDesired', '°C', 'mdi:thermometer', 0],
        'PumpStatus':
            ['Hc1PumpStatus', None, 'mdi:toggle-switch', 2],
        'HCSummerTemperatureLimit':
            ['Hc1SummerTempLimit', '°C', 'mdi:weather-sunny', 0],
        'HolidayTemperature':
            ['HolidayTemp', '°C', 'mdi:thermometer', 0],
        'HWTemperatureDesired':
            ['HwcTempDesired', '°C', 'mdi:thermometer', 0],
        'HWTimerMonday':
            ['hwcTimer.Monday', None, 'mdi:timer', 1],
        'HWTimerTuesday':
            ['hwcTimer.Tuesday', None, 'mdi:timer', 1],
        'HWTimerWednesday':
            ['hwcTimer.Wednesday', None, 'mdi:timer', 1],
        'HWTimerThursday':
            ['hwcTimer.Thursday', None, 'mdi:timer', 1],
        'HWTimerFriday':
            ['hwcTimer.Friday', None, 'mdi:timer', 1],
        'HWTimerSaturday':
            ['hwcTimer.Saturday', None, 'mdi:timer', 1],
        'HWTimerSunday':
            ['hwcTimer.Sunday', None, 'mdi:timer', 1],
        'WaterPressure':
            ['WaterPressure', 'bar', 'mdi:water-pump', 0],
        'Zone1RoomZoneMapping':
            ['z1RoomZoneMapping', None, 'mdi:label', 0],
        'Zone1NightTemperature':
            ['z1NightTemp', '°C', 'mdi:weather-night', 0],
        'Zone1DayTemperature':
            ['z1DayTemp', '°C', 'mdi:weather-sunny', 0],
        'Zone1HolidayTemperature':
            ['z1HolidayTemp', '°C', 'mdi:thermometer', 0],
        'Zone1RoomTemperature':
            ['z1RoomTemp', '°C', 'mdi:thermometer', 0],
        'Zone1ActualRoomTemperatureDesired':
            ['z1ActualRoomTempDesired', '°C', 'mdi:thermometer', 0],
        'Zone1TimerMonday':
            ['z1Timer.Monday', None, 'mdi:timer', 1],
        'Zone1TimerTuesday':
            ['z1Timer.Tuesday', None, 'mdi:timer', 1],
        'Zone1TimerWednesday':
            ['z1Timer.Wednesday', None, 'mdi:timer', 1],
        'Zone1TimerThursday':
            ['z1Timer.Thursday', None, 'mdi:timer', 1],
        'Zone1TimerFriday':
            ['z1Timer.Friday', None, 'mdi:timer', 1],
        'Zone1TimerSaturday':
            ['z1Timer.Saturday', None, 'mdi:timer', 1],
        'Zone1TimerSunday':
            ['z1Timer.Sunday', None, 'mdi:timer', 1],
        'Zone1OperativeMode':
            ['z1OpMode', None, 'mdi:math-compass', 3],
        'ContinuosHeating':
            ['ContinuosHeating', '°C', 'mdi:weather-snowy', 0],
        'PowerEnergyConsumptionLastMonth':
            ['PrEnergySumHcLastMonth', 'kWh', 'mdi:flash', 0],
        'PowerEnergyConsumptionThisMonth':
            ['PrEnergySumHcThisMonth', 'kWh', 'mdi:flash', 0]
    },
    'ehp': {
        'HWTemperature':
            ['HwcTemp', '°C', 'mdi:thermometer', 4],
        'OutsideTemp':
            ['OutsideTemp', '°C', 'mdi:thermometer', 4]
    }
}
