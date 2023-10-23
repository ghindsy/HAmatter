"""Support for ZHA controls using the select platform."""
from __future__ import annotations

from enum import Enum
import functools
import logging
from typing import TYPE_CHECKING, Any, Self

from zigpy import types
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.security import IasWd

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EntityCategory, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import discovery
from .core.const import (
    CLUSTER_HANDLER_HUE_OCCUPANCY,
    CLUSTER_HANDLER_IAS_WD,
    CLUSTER_HANDLER_INOVELLI,
    CLUSTER_HANDLER_ON_OFF,
    CLUSTER_HANDLER_THERMOSTAT,
    SIGNAL_ADD_ENTITIES,
    SIGNAL_ATTR_UPDATED,
    Strobe,
)
from .core.helpers import get_zha_data
from .core.registries import ZHA_ENTITIES
from .entity import ZhaEntity

if TYPE_CHECKING:
    from .core.cluster_handlers import ClusterHandler
    from .core.device import ZHADevice


CONFIG_DIAGNOSTIC_MATCH = functools.partial(
    ZHA_ENTITIES.config_diagnostic_match, Platform.SELECT
)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zigbee Home Automation siren from config entry."""
    zha_data = get_zha_data(hass)
    entities_to_create = zha_data.platforms[Platform.SELECT]

    unsub = async_dispatcher_connect(
        hass,
        SIGNAL_ADD_ENTITIES,
        functools.partial(
            discovery.async_add_entities,
            async_add_entities,
            entities_to_create,
        ),
    )
    config_entry.async_on_unload(unsub)


class ZHAEnumSelectEntity(ZhaEntity, SelectEntity):
    """Representation of a ZHA select entity."""

    _attr_entity_category = EntityCategory.CONFIG
    _attribute_name: str
    _enum: type[Enum]

    def __init__(
        self,
        unique_id: str,
        zha_device: ZHADevice,
        cluster_handlers: list[ClusterHandler],
        **kwargs: Any,
    ) -> None:
        """Init this select entity."""
        self._attribute_name = self._enum.__name__
        self._attr_options = [entry.name.replace("_", " ") for entry in self._enum]
        self._cluster_handler: ClusterHandler = cluster_handlers[0]
        super().__init__(unique_id, zha_device, cluster_handlers, **kwargs)

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        option = self._cluster_handler.data_cache.get(self._attribute_name)
        if option is None:
            return None
        return option.name.replace("_", " ")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._cluster_handler.data_cache[self._attribute_name] = self._enum[
            option.replace(" ", "_")
        ]
        self.async_write_ha_state()

    @callback
    def async_restore_last_state(self, last_state) -> None:
        """Restore previous state."""
        if last_state.state and last_state.state != STATE_UNKNOWN:
            self._cluster_handler.data_cache[self._attribute_name] = self._enum[
                last_state.state.replace(" ", "_")
            ]


class ZHANonZCLSelectEntity(ZHAEnumSelectEntity):
    """Representation of a ZHA select entity with no ZCL interaction."""

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return True


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names=CLUSTER_HANDLER_IAS_WD)
class ZHADefaultToneSelectEntity(ZHANonZCLSelectEntity):
    """Representation of a ZHA default siren tone select entity."""

    _unique_id_suffix = IasWd.Warning.WarningMode.__name__
    _enum = IasWd.Warning.WarningMode
    _attr_translation_key: str = "default_siren_tone"


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names=CLUSTER_HANDLER_IAS_WD)
class ZHADefaultSirenLevelSelectEntity(ZHANonZCLSelectEntity):
    """Representation of a ZHA default siren level select entity."""

    _unique_id_suffix = IasWd.Warning.SirenLevel.__name__
    _enum = IasWd.Warning.SirenLevel
    _attr_translation_key: str = "default_siren_level"


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names=CLUSTER_HANDLER_IAS_WD)
class ZHADefaultStrobeLevelSelectEntity(ZHANonZCLSelectEntity):
    """Representation of a ZHA default siren strobe level select entity."""

    _unique_id_suffix = IasWd.StrobeLevel.__name__
    _enum = IasWd.StrobeLevel
    _attr_translation_key: str = "default_strobe_level"


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names=CLUSTER_HANDLER_IAS_WD)
class ZHADefaultStrobeSelectEntity(ZHANonZCLSelectEntity):
    """Representation of a ZHA default siren strobe select entity."""

    _unique_id_suffix = Strobe.__name__
    _enum = Strobe
    _attr_translation_key: str = "default_strobe"


class ZCLEnumSelectEntity(ZhaEntity, SelectEntity):
    """Representation of a ZHA ZCL enum select entity."""

    _attribute_name: str
    _attr_entity_category = EntityCategory.CONFIG
    _enum: type[Enum]

    @classmethod
    def create_entity(
        cls,
        unique_id: str,
        zha_device: ZHADevice,
        cluster_handlers: list[ClusterHandler],
        **kwargs: Any,
    ) -> Self | None:
        """Entity Factory.

        Return entity if it is a supported configuration, otherwise return None
        """
        cluster_handler = cluster_handlers[0]
        if (
            cls._attribute_name in cluster_handler.cluster.unsupported_attributes
            or cls._attribute_name not in cluster_handler.cluster.attributes_by_name
            or cluster_handler.cluster.get(cls._attribute_name) is None
        ):
            _LOGGER.debug(
                "%s is not supported - skipping %s entity creation",
                cls._attribute_name,
                cls.__name__,
            )
            return None

        return cls(unique_id, zha_device, cluster_handlers, **kwargs)

    def __init__(
        self,
        unique_id: str,
        zha_device: ZHADevice,
        cluster_handlers: list[ClusterHandler],
        **kwargs: Any,
    ) -> None:
        """Init this select entity."""
        self._attr_options = [entry.name.replace("_", " ") for entry in self._enum]
        self._cluster_handler: ClusterHandler = cluster_handlers[0]
        super().__init__(unique_id, zha_device, cluster_handlers, **kwargs)

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        option = self._cluster_handler.cluster.get(self._attribute_name)
        if option is None:
            return None
        option = self._enum(option)
        return option.name.replace("_", " ")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._cluster_handler.write_attributes_safe(
            {self._attribute_name: self._enum[option.replace(" ", "_")]}
        )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when about to be added to hass."""
        await super().async_added_to_hass()
        self.async_accept_signal(
            self._cluster_handler, SIGNAL_ATTR_UPDATED, self.async_set_state
        )

    @callback
    def async_set_state(self, attr_id: int, attr_name: str, value: Any):
        """Handle state update from cluster handler."""
        self.async_write_ha_state()


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names=CLUSTER_HANDLER_ON_OFF)
class ZHAStartupOnOffSelectEntity(ZCLEnumSelectEntity):
    """Representation of a ZHA startup onoff select entity."""

    _unique_id_suffix = OnOff.StartUpOnOff.__name__
    _attribute_name = "start_up_on_off"
    _enum = OnOff.StartUpOnOff
    _attr_translation_key: str = "start_up_on_off"


class TuyaPowerOnState(types.enum8):
    """Tuya power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_ON_OFF,
    models={"TS011F", "TS0121", "TS0001", "TS0002", "TS0003", "TS0004"},
)
@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="tuya_manufacturer",
    manufacturers={
        "_TZE200_7tdtqgwv",
        "_TZE200_amp6tsvy",
        "_TZE200_oisqyl4o",
        "_TZE200_vhy3iakz",
        "_TZ3000_uim07oem",
        "_TZE200_wfxuhoea",
        "_TZE200_tviaymwx",
        "_TZE200_g1ib5ldv",
        "_TZE200_wunufsil",
        "_TZE200_7deq70b8",
        "_TZE200_tz32mtza",
        "_TZE200_2hf7x9n3",
        "_TZE200_aqnazj70",
        "_TZE200_1ozguk6x",
        "_TZE200_k6jhsr0q",
        "_TZE200_9mahtqtg",
    },
)
class TuyaPowerOnStateSelectEntity(ZCLEnumSelectEntity):
    """Representation of a ZHA power on state select entity."""

    _unique_id_suffix = "power_on_state"
    _attribute_name = "power_on_state"
    _enum = TuyaPowerOnState
    _attr_translation_key: str = "power_on_state"


class TuyaBacklightMode(types.enum8):
    """Tuya switch backlight mode enum."""

    Off = 0x00
    LightWhenOn = 0x01
    LightWhenOff = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_ON_OFF,
    models={"TS011F", "TS0121", "TS0001", "TS0002", "TS0003", "TS0004"},
)
class TuyaBacklightModeSelectEntity(ZCLEnumSelectEntity):
    """Representation of a ZHA backlight mode select entity."""

    _unique_id_suffix = "backlight_mode"
    _attribute_name = "backlight_mode"
    _enum = TuyaBacklightMode
    _attr_translation_key: str = "backlight_mode"


class MoesBacklightMode(types.enum8):
    """MOES switch backlight mode enum."""

    Off = 0x00
    LightWhenOn = 0x01
    LightWhenOff = 0x02
    Freeze = 0x03


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="tuya_manufacturer",
    manufacturers={
        "_TZE200_7tdtqgwv",
        "_TZE200_amp6tsvy",
        "_TZE200_oisqyl4o",
        "_TZE200_vhy3iakz",
        "_TZ3000_uim07oem",
        "_TZE200_wfxuhoea",
        "_TZE200_tviaymwx",
        "_TZE200_g1ib5ldv",
        "_TZE200_wunufsil",
        "_TZE200_7deq70b8",
        "_TZE200_tz32mtza",
        "_TZE200_2hf7x9n3",
        "_TZE200_aqnazj70",
        "_TZE200_1ozguk6x",
        "_TZE200_k6jhsr0q",
        "_TZE200_9mahtqtg",
    },
)
class MoesBacklightModeSelectEntity(ZCLEnumSelectEntity):
    """Moes devices have a different backlight mode select options."""

    _unique_id_suffix = "backlight_mode"
    _attribute_name = "backlight_mode"
    _enum = MoesBacklightMode
    _attr_translation_key: str = "backlight_mode"


class AqaraMotionSensitivities(types.enum8):
    """Aqara motion sensitivities."""

    Low = 0x01
    Medium = 0x02
    High = 0x03


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="opple_cluster",
    models={"lumi.motion.ac01", "lumi.motion.ac02", "lumi.motion.agl04"},
)
class AqaraMotionSensitivity(ZCLEnumSelectEntity):
    """Representation of a ZHA motion sensitivity configuration entity."""

    _unique_id_suffix = "motion_sensitivity"
    _attribute_name = "motion_sensitivity"
    _enum = AqaraMotionSensitivities
    _attr_translation_key: str = "motion_sensitivity"


class HueV1MotionSensitivities(types.enum8):
    """Hue v1 motion sensitivities."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_HUE_OCCUPANCY,
    manufacturers={"Philips", "Signify Netherlands B.V."},
    models={"SML001"},
)
class HueV1MotionSensitivity(ZCLEnumSelectEntity):
    """Representation of a ZHA motion sensitivity configuration entity."""

    _unique_id_suffix = "motion_sensitivity"
    _attribute_name = "sensitivity"
    _enum = HueV1MotionSensitivities
    _attr_translation_key: str = "motion_sensitivity"


class HueV2MotionSensitivities(types.enum8):
    """Hue v2 motion sensitivities."""

    Lowest = 0x00
    Low = 0x01
    Medium = 0x02
    High = 0x03
    Highest = 0x04


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_HUE_OCCUPANCY,
    manufacturers={"Philips", "Signify Netherlands B.V."},
    models={"SML002", "SML003", "SML004"},
)
class HueV2MotionSensitivity(ZCLEnumSelectEntity):
    """Representation of a ZHA motion sensitivity configuration entity."""

    _unique_id_suffix = "motion_sensitivity"
    _attribute_name = "sensitivity"
    _enum = HueV2MotionSensitivities
    _attr_translation_key: str = "motion_sensitivity"


class AqaraMonitoringModess(types.enum8):
    """Aqara monitoring modes."""

    Undirected = 0x00
    Left_Right = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="opple_cluster", models={"lumi.motion.ac01"}
)
class AqaraMonitoringMode(ZCLEnumSelectEntity):
    """Representation of a ZHA monitoring mode configuration entity."""

    _unique_id_suffix = "monitoring_mode"
    _attribute_name = "monitoring_mode"
    _enum = AqaraMonitoringModess
    _attr_translation_key: str = "monitoring_mode"


class AqaraApproachDistances(types.enum8):
    """Aqara approach distances."""

    Far = 0x00
    Medium = 0x01
    Near = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="opple_cluster", models={"lumi.motion.ac01"}
)
class AqaraApproachDistance(ZCLEnumSelectEntity):
    """Representation of a ZHA approach distance configuration entity."""

    _unique_id_suffix = "approach_distance"
    _attribute_name = "approach_distance"
    _enum = AqaraApproachDistances
    _attr_translation_key: str = "approach_distance"


class AqaraE1ReverseDirection(types.enum8):
    """Aqara curtain reversal."""

    Normal = 0x00
    Inverted = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="window_covering", models={"lumi.curtain.agl001"}
)
class AqaraCurtainMode(ZCLEnumSelectEntity):
    """Representation of a ZHA curtain mode configuration entity."""

    _unique_id_suffix = "window_covering_mode"
    _attribute_name = "window_covering_mode"
    _enum = AqaraE1ReverseDirection
    _attr_translation_key: str = "window_covering_mode"


class InovelliOutputMode(types.enum1):
    """Inovelli output mode."""

    Dimmer = 0x00
    OnOff = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_INOVELLI,
)
class InovelliOutputModeEntity(ZCLEnumSelectEntity):
    """Inovelli output mode control."""

    _unique_id_suffix = "output_mode"
    _attribute_name = "output_mode"
    _enum = InovelliOutputMode
    _attr_translation_key: str = "output_mode"


class InovelliSwitchType(types.enum8):
    """Inovelli output mode."""

    Single_Pole = 0x00
    Three_Way_Dumb = 0x01
    Three_Way_AUX = 0x02
    Single_Pole_Full_Sine = 0x03


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_INOVELLI,
)
class InovelliSwitchTypeEntity(ZCLEnumSelectEntity):
    """Inovelli switch type control."""

    _unique_id_suffix = "switch_type"
    _attribute_name = "switch_type"
    _enum = InovelliSwitchType
    _attr_translation_key: str = "switch_type"


class InovelliLedScalingMode(types.enum1):
    """Inovelli led mode."""

    VZM31SN = 0x00
    LZW31SN = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_INOVELLI,
)
class InovelliLedScalingModeEntity(ZCLEnumSelectEntity):
    """Inovelli led mode control."""

    _unique_id_suffix = "led_scaling_mode"
    _attribute_name = "led_scaling_mode"
    _enum = InovelliLedScalingMode
    _attr_translation_key: str = "led_scaling_mode"


class InovelliNonNeutralOutput(types.enum1):
    """Inovelli non neutral output selection."""

    Low = 0x00
    High = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_INOVELLI,
)
class InovelliNonNeutralOutputEntity(ZCLEnumSelectEntity):
    """Inovelli non neutral output control."""

    _unique_id_suffix = "increased_non_neutral_output"
    _attribute_name = "increased_non_neutral_output"
    _enum = InovelliNonNeutralOutput
    _attr_translation_key: str = "increased_non_neutral_output"


class AqaraFeedingMode(types.enum8):
    """Feeding mode."""

    Manual = 0x00
    Schedule = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="opple_cluster", models={"aqara.feeder.acn001"}
)
class AqaraPetFeederMode(ZCLEnumSelectEntity):
    """Representation of an Aqara pet feeder mode configuration entity."""

    _unique_id_suffix = "feeding_mode"
    _attribute_name = "feeding_mode"
    _enum = AqaraFeedingMode
    _attr_translation_key: str = "feeding_mode"
    _attr_icon: str = "mdi:wrench-clock"


class AqaraThermostatPresetMode(types.enum8):
    """Thermostat preset mode."""

    Manual = 0x00
    Auto = 0x01
    Away = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="opple_cluster", models={"lumi.airrtc.agl001"}
)
class AqaraThermostatPreset(ZCLEnumSelectEntity):
    """Representation of an Aqara thermostat preset configuration entity."""

    _unique_id_suffix = "preset"
    _attribute_name = "preset"
    _enum = AqaraThermostatPresetMode
    _attr_translation_key: str = "preset"


class KeypadLockoutEnum(types.enum8):
    """Often only the first 2 are implemented."""

    Unlock = 0x00
    Lock1 = 0x01
    Lock2 = 0x02
    Lock3 = 0x03
    Lock4 = 0x04


@CONFIG_DIAGNOSTIC_MATCH(cluster_handler_names="thermostat_ui")
class KeypadLockout(ZCLEnumSelectEntity):
    """Mandatory Attribute for this cluster.

    often just a switch, but can be a select if need be.
    """

    _unique_id_suffix = "keypad_lockout"
    _select_attr: str = "keypad_lockout"
    _enum = KeypadLockoutEnum
    _attr_translation_key: str = "keypad_lockout"
    _attr_icon: str = "mdi:lock"


class DanfossExerciseDayOfTheWeekEnum(types.enum8):
    """Day of the Week."""

    Sunday = 0
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_THERMOSTAT,
    quirk_classes={"thermostat.DanfossThermostat"},
)
class DanfossExerciseDayOfTheWeek(ZCLEnumSelectEntity):
    """Danfoss Proprietary attribute for setting the day of the week for exercising."""

    _unique_id_suffix = "exercise_day_of_week"
    _select_attr = "exercise_day_of_week"
    _attr_translation_key: str = "exercise_day_of_week"
    _enum = DanfossExerciseDayOfTheWeekEnum
    _attr_icon: str = "mdi:wrench-clock"


class DanfossOrientationEnum(types.enum8):
    """Vertical or horizontal."""

    Horizontal = 0x00
    Vertical = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_THERMOSTAT,
    quirk_classes={"thermostat.DanfossThermostat"},
)
class DanfossOrientation(ZCLEnumSelectEntity):
    """Danfoss Proprietary attribute for setting the orientation of the valve.

    needed for biasing the internal temperature sensor.
    """

    _unique_id_suffix = "orientation"
    _select_attr = "orientation"
    _attr_translation_key: str = "valve_orientation"
    _enum = DanfossOrientationEnum


class DanfossAdaptationRunControlEnum(types.enum8):
    """Initiate or Cancel Adaptation Run."""

    Nothing = 0x00
    Initiate = 0x01
    Cancel = 0x02


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names=CLUSTER_HANDLER_THERMOSTAT,
    quirk_classes={"thermostat.DanfossThermostat"},
)
class DanfossAdaptationRunControl(ZCLEnumSelectEntity):
    """Danfoss Proprietary attribute for controlling the current adaptation run."""

    _unique_id_suffix = "adaptation_run_control"
    _select_attr = "adaptation_run_control"
    _attr_translation_key: str = "adaptation_run_command"
    _enum = DanfossAdaptationRunControlEnum


class DanfossViewingDirectionEnum(types.enum8):
    """Default (button above screen when looking at it) or Inverted (button below screen when looking at it)."""

    Default = 0x00
    Inverted = 0x01


@CONFIG_DIAGNOSTIC_MATCH(
    cluster_handler_names="thermostat_ui",
    quirk_classes={"thermostat.DanfossThermostat"},
)
class DanfossViewingDirection(ZCLEnumSelectEntity):
    """Danfoss Proprietary attribute for setting the viewing direction of the screen."""

    _unique_id_suffix = "viewing_direction"
    _select_attr = "viewing_direction"
    _attr_translation_key: str = "viewing_direction"
    _enum = DanfossViewingDirectionEnum
