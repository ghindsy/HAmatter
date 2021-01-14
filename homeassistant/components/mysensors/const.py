"""MySensors constants."""
from collections import defaultdict
ATTR_DEVICES: str = "devices"
CONF_BAUD_RATE: str = "baud_rate"
CONF_DEVICE: str = "device"
CONF_GATEWAYS: str = "gateways"
CONF_NODES: str = "nodes"
CONF_PERSISTENCE: str = "persistence"
CONF_PERSISTENCE_FILE: str = "persistence_file"
CONF_RETAIN: str = "retain"
CONF_TCP_PORT: str = "tcp_port"
CONF_TOPIC_IN_PREFIX: str = "topic_in_prefix"
CONF_TOPIC_OUT_PREFIX: str = "topic_out_prefix"
CONF_VERSION: str = "version"

DOMAIN: str = "mysensors"
MYSENSORS_GATEWAY_READY: str = "mysensors_gateway_ready_{}"
MYSENSORS_GATEWAYS: str = "mysensors_gateways"
PLATFORM: str = "platform"
SCHEMA: str = "schema"
CHILD_CALLBACK: str = "mysensors_child_callback_{}_{}_{}_{}"
NODE_CALLBACK: str = "mysensors_node_callback_{}_{}"
MYSENSORS_DISCOVERY = "mysensors_discovery_{}_{}"
TYPE: str = "type"
UPDATE_DELAY: float = 0.1

SERVICE_SEND_IR_CODE: str = "send_ir_code"

SensorType = str
"""S_DOOR, S_MOTION, S_SMOKE, ..."""
ValueType = str
"""V_TRIPPED, V_ARMED, V_STATUS, V_PERCENTAGE, ..."""
GatewayId = int
DevId = Tuple[GatewayId, int, int, int]
"""describes the backend of a hass entity. Contents are: GatewayId, node_id, child_id, v_type as int

The string version of v_type can be looked up in the enum gateway.const.SetReq of the appropriate BaseAsyncGateway
Home Assistant Entities are quite limited and only ever do one thing.
MySensors Nodes have multiple child_ids each with a s_type several associated v_types
The MySensors integration brings these together by creating an entity for every v_type of every child_id of every node.
The DevId tuple perfectly captures this.
"""

BINARY_SENSOR_TYPES: Dict[SensorType, Set[ValueType]] = {
    "S_DOOR": {"V_TRIPPED"},
    "S_MOTION": {"V_TRIPPED"},
    "S_SMOKE": {"V_TRIPPED"},
    "S_SPRINKLER": {"V_TRIPPED"},
    "S_WATER_LEAK": {"V_TRIPPED"},
    "S_SOUND": {"V_TRIPPED"},
    "S_VIBRATION": {"V_TRIPPED"},
    "S_MOISTURE": {"V_TRIPPED"},
}

CLIMATE_TYPES: Dict[SensorType, Set[ValueType]] = {"S_HVAC": {"V_HVAC_FLOW_STATE"}}

COVER_TYPES: Dict[SensorType, Set[ValueType]] = {"S_COVER": {"V_DIMMER", "V_PERCENTAGE", "V_LIGHT", "V_STATUS"}}

DEVICE_TRACKER_TYPES: Dict[SensorType, Set[ValueType]] = {"S_GPS": {"V_POSITION"}}

LIGHT_TYPES: Dict[SensorType, Set[ValueType]] = {
    "S_DIMMER": {"V_DIMMER", "V_PERCENTAGE"},
    "S_RGB_LIGHT": {"V_RGB"},
    "S_RGBW_LIGHT": {"V_RGBW"},
}

NOTIFY_TYPES: Dict[SensorType, Set[ValueType]] = {"S_INFO": {"V_TEXT"}}

SENSOR_TYPES: Dict[SensorType, Set[ValueType]] = {
    "S_SOUND": {"V_LEVEL"},
    "S_VIBRATION": {"V_LEVEL"},
    "S_MOISTURE": {"V_LEVEL"},
    "S_INFO": {"V_TEXT"},
    "S_GPS": {"V_POSITION"},
    "S_TEMP": {"V_TEMP"},
    "S_HUM": {"V_HUM"},
    "S_BARO": {"V_PRESSURE", "V_FORECAST"},
    "S_WIND": {"V_WIND", "V_GUST", "V_DIRECTION"},
    "S_RAIN": {"V_RAIN", "V_RAINRATE"},
    "S_UV": {"V_UV"},
    "S_WEIGHT": {"V_WEIGHT", "V_IMPEDANCE"},
    "S_POWER": {"V_WATT", "V_KWH", "V_VAR", "V_VA", "V_POWER_FACTOR"},
    "S_DISTANCE": {"V_DISTANCE"},
    "S_LIGHT_LEVEL": {"V_LIGHT_LEVEL", "V_LEVEL"},
    "S_IR": {"V_IR_RECEIVE"},
    "S_WATER": {"V_FLOW", "V_VOLUME"},
    "S_CUSTOM": {"V_VAR1", "V_VAR2", "V_VAR3", "V_VAR4", "V_VAR5", "V_CUSTOM"},
    "S_SCENE_CONTROLLER": {"V_SCENE_ON", "V_SCENE_OFF"},
    "S_COLOR_SENSOR": {"V_RGB"},
    "S_MULTIMETER": {"V_VOLTAGE", "V_CURRENT", "V_IMPEDANCE"},
    "S_GAS": {"V_FLOW", "V_VOLUME"},
    "S_WATER_QUALITY": {"V_TEMP", "V_PH", "V_ORP", "V_EC"},
    "S_AIR_QUALITY": {"V_DUST_LEVEL", "V_LEVEL"},
    "S_DUST": {"V_DUST_LEVEL", "V_LEVEL"},
}

SWITCH_TYPES: Dict[SensorType, Set[ValueType]] = {
    "S_LIGHT": {"V_LIGHT"},
    "S_BINARY": {"V_STATUS"},
    "S_DOOR": {"V_ARMED"},
    "S_MOTION": {"V_ARMED"},
    "S_SMOKE": {"V_ARMED"},
    "S_SPRINKLER": {"V_STATUS"},
    "S_WATER_LEAK": {"V_ARMED"},
    "S_SOUND": {"V_ARMED"},
    "S_VIBRATION": {"V_ARMED"},
    "S_MOISTURE": {"V_ARMED"},
    "S_IR": {"V_IR_SEND"},
    "S_LOCK": {"V_LOCK_STATUS"},
    "S_WATER_QUALITY": {"V_STATUS"},
}


PLATFORM_TYPES: Dict[str, Dict[SensorType, Set[ValueType]]] = {
    "binary_sensor": BINARY_SENSOR_TYPES,
    "climate": CLIMATE_TYPES,
    "cover": COVER_TYPES,
    "device_tracker": DEVICE_TRACKER_TYPES,
    "light": LIGHT_TYPES,
    "notify": NOTIFY_TYPES,
    "sensor": SENSOR_TYPES,
    "switch": SWITCH_TYPES,
}
"""dict mapping hass platform name to dict that maps mysensors s_type to set of mysensors v_type"""

FLAT_PLATFORM_TYPES: Dict[Tuple[str, SensorType], Set[ValueType]] = {
    (platform, s_type_name): v_type_name
    for platform, platform_types in PLATFORM_TYPES.items()
    for s_type_name, v_type_name in platform_types.items()
}
"""flatter version of PLATFORM_TYPES

dict mapping tuples of hass platform name and mysensors s_type to mysensors v_type 
"""

TYPE_TO_PLATFORMS: Dict[SensorType, List[str]] = defaultdict(list)
"""dict mapping mysensors s_type to list of hass platform name"""
for platform, platform_types in PLATFORM_TYPES.items():
    for s_type_name in platform_types:
        TYPE_TO_PLATFORMS[s_type_name].append(platform)
