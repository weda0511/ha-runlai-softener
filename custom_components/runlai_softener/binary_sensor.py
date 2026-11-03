# -*- coding: utf-8 -*-
"""报警类传感器: 缺盐/漏水/树脂/滤料/故障位/度假模式, 数据取自 protocolData."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RunlaiCoordinator
from .const import BINARY_FIELDS, DOMAIN

DEVICE_CLASS_MAP = {
    "salt_shortage_alarm": BinarySensorDeviceClass.PROBLEM,
    "salt_shortage_reminder": BinarySensorDeviceClass.PROBLEM,
    "resin_replacement_reminder": BinarySensorDeviceClass.PROBLEM,
    "filter_material_reminder": BinarySensorDeviceClass.PROBLEM,
    "water_leakage": BinarySensorDeviceClass.MOISTURE,
    "vacation_pattern": None,
    "clock_chip_fault": BinarySensorDeviceClass.PROBLEM,
    "memory_error_fault": BinarySensorDeviceClass.PROBLEM,
    "multiple_position_signal_fault": BinarySensorDeviceClass.PROBLEM,
    "no_position_signal_fault": BinarySensorDeviceClass.PROBLEM,
}


class RunlaiBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: RunlaiCoordinator, field: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._field = field
        self._attr_unique_id = "%s_b_%s" % (coordinator.entry.entry_id, field)
        self._attr_name = "%s %s" % (coordinator.device_name, name)
        self._attr_icon = icon
        dc = DEVICE_CLASS_MAP.get(field)
        if dc is not None:
            self._attr_device_class = dc

    @property
    def device_info(self) -> DeviceInfo:
        from .sensor import coordinator_unique_id
        return DeviceInfo(
            identifiers={(DOMAIN, coordinator_unique_id(self.coordinator))},
            name=self.coordinator.device_name,
            manufacturer="润莱 RunLucky",
            model="中央软水机",
        )

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.data.get(self._field)
        if isinstance(val, bool):
            return val
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and isinstance(
            self.coordinator.data.get(self._field), bool
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            RunlaiBinarySensor(coordinator, field, name, icon)
            for field, (name, icon) in BINARY_FIELDS.items()
        ],
        update_before_add=False,
    )
