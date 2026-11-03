# -*- coding: utf-8 -*-
"""传感器: 制水量/用水量/流量/硬度/再生次数/阀位/状态等, 2026-11-03 按润莱智联实测接口定制."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RunlaiCoordinator
from .const import (
    DOMAIN,
    STD_CURRENT_TIME,
    STD_DAILY,
    STD_FLOW_RATE,
    STD_HARDNESS,
    STD_LAST_EVENT,
    STD_MONTH_LAST,
    STD_MONTH_THIS,
    STD_PERIODIC,
    STD_REGEN_TIMES,
    STD_RESIDUAL,
    STD_RESIN,
    STD_SALT_ADD,
    STD_STATION,
    STD_STATUS,
    STD_UPDATED,
    STD_WEEKLY_AVG,
)

STATION_LABELS = {
    0: "运行",
    1: "反洗",
    2: "吸盐慢洗",
    3: "盐箱注水",
    4: "正洗",
}


@dataclass(frozen=True)
class SoftenerSensorDescription(SensorEntityDescription):
    std_field: str = ""


SENSOR_DESCRIPTIONS: tuple[SoftenerSensorDescription, ...] = (
    SoftenerSensorDescription(
        key="residual_water_production", std_field=STD_RESIDUAL,
        name="剩余制水量", icon="mdi:water-check",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="daily_water_consumption", std_field=STD_DAILY,
        name="今日用水", icon="mdi:water",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="month_water", std_field=STD_MONTH_THIS,
        name="本月用水", icon="mdi:calendar-month",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="last_month_water", std_field=STD_MONTH_LAST,
        name="上月用水", icon="mdi:calendar-month-outline",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="average_weekly_water_consumption", std_field=STD_WEEKLY_AVG,
        name="周均用水", icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="periodic_water_production", std_field=STD_PERIODIC,
        name="周期制水量", icon="mdi:reload",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="m³",
    ),
    SoftenerSensorDescription(
        key="flow_rate", std_field=STD_FLOW_RATE,
        name="瞬时流量", icon="mdi:pump",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="m³/h",
    ),
    SoftenerSensorDescription(
        key="raw_water_hardness", std_field=STD_HARDNESS,
        name="原水硬度", icon="mdi:water-opacity",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="mg/L",
    ),
    SoftenerSensorDescription(
        key="resin_volume", std_field=STD_RESIN,
        name="树脂体积", icon="mdi:cube-outline",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="L",
    ),
    SoftenerSensorDescription(
        key="salt_addition", std_field=STD_SALT_ADD,
        name="单次加盐量", icon="mdi:shaker",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="kg",
    ),
    SoftenerSensorDescription(
        key="regeneration_times", std_field=STD_REGEN_TIMES,
        name="再生次数", icon="mdi:autorenew",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SoftenerSensorDescription(
        key="station", std_field=STD_STATION,
        name="阀位状态", icon="mdi:tune-vertical",
    ),
    SoftenerSensorDescription(
        key="device_current_time", std_field=STD_CURRENT_TIME,
        name="设备时间", icon="mdi:clock-outline",
    ),
    SoftenerSensorDescription(
        key="last_event_time", std_field=STD_LAST_EVENT,
        name="设备最后上报", icon="mdi:cloud-upload-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SoftenerSensorDescription(
        key="status", std_field=STD_STATUS,
        name="接口状态", icon="mdi:cloud-check",
    ),
    SoftenerSensorDescription(
        key="updated", std_field=STD_UPDATED,
        name="最后更新", icon="mdi:clock-check-outline",
    ),
)


class RunlaiSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: RunlaiCoordinator, desc: SoftenerSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._attr_unique_id = "%s_%s" % (coordinator.entry.entry_id, desc.key)
        self._attr_name = "%s %s" % (coordinator.device_name, desc.name)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, coordinator_unique_id(self.coordinator))},
            name=self.coordinator.device_name,
            manufacturer="润莱 RunLucky",
            model="中央软水机",
            sw_version="RunLuckyIot 云端",
        )

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get(self.entity_description.std_field)
        if val is None or val == "":
            return None
        # 阀位转中文
        if self.entity_description.std_field == STD_STATION:
            return STATION_LABELS.get(val, "位置%s" % val)
        # 时间戳类: 云端返回 ISO 字符串, 需转 datetime
        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            try:
                from datetime import datetime
                return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            except ValueError:
                return None
        return val

    @property
    def available(self) -> bool:
        if self.entity_description.std_field in ("status", "updated"):
            return self.coordinator.last_update_success
        return self.coordinator.last_update_success and self.native_value is not None


def coordinator_unique_id(coordinator: RunlaiCoordinator) -> str:
    return coordinator.entry.data.get("device_mac") or coordinator.device_id


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [RunlaiSensor(coordinator, d) for d in SENSOR_DESCRIPTIONS],
        update_before_add=False,
    )
