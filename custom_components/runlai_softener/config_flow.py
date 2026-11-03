# -*- coding: utf-8 -*-
"""配置流: 手机号+密码登录 -> 选择设备 -> 完成; 密码变更后可重新认证."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MAC,
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from . import RunlaiClient

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema({
    vol.Required(CONF_PHONE): str,
    vol.Required(CONF_PASSWORD): str,
})


async def _login_and_list(hass, phone: str, password: str) -> tuple[str | None, list[dict], str]:
    """登录并列出设备; 返回 (错误码, 设备列表, 提示)."""
    client = RunlaiClient(async_get_clientsession(hass), phone, password)
    try:
        await client._login()
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("润莱登录失败: %s", err)
        return "auth_failed", [], str(err)[:120]
    try:
        devices = await client.get_device_list()
    except Exception as err:  # noqa: BLE001
        return "device_list_failed", [], str(err)[:120]
    if not devices:
        return "no_devices", [], "账号下没有设备"
    return None, devices, ""


class RunlaiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._phone: str = ""
        self._password: str = ""
        self._devices: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None) -> Any:
        errors: dict = {}
        if user_input is not None:
            err, devices, msg = await _login_and_list(
                self.hass, user_input[CONF_PHONE], user_input[CONF_PASSWORD]
            )
            if err is None:
                self._phone = user_input[CONF_PHONE]
                self._password = user_input[CONF_PASSWORD]
                self._devices = devices
                if len(devices) == 1:
                    return self._create_entry(devices[0])
                return await self.async_step_device()
            errors["base"] = err
            _LOGGER.warning("润莱配置失败 %s: %s", err, msg)
        return self.async_show_form(step_id="user", data_schema=LOGIN_SCHEMA, errors=errors)

    async def async_step_device(self, user_input: dict | None = None) -> Any:
        errors: dict = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device = next((d for d in self._devices if d["deviceId"] == device_id), None)
            if device:
                return self._create_entry(device)
            errors["base"] = "unknown_device"
        names = {
            d["deviceId"]: "%s (%s)" % (d.get("deviceName", "?"), d.get("mac", "")[:17])
            for d in self._devices
        }
        schema = vol.Schema({
            vol.Required(CONF_DEVICE_ID): vol.In(names),
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        })
        return self.async_show_form(step_id="device", data_schema=schema, errors=errors)

    def _create_entry(self, device: dict) -> Any:
        return self.async_create_entry(
            title=device.get("deviceName", "润莱软水机"),
            data={
                CONF_PHONE: self._phone,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device["deviceId"],
                CONF_DEVICE_NAME: device.get("deviceName", "润莱软水机"),
                CONF_DEVICE_MAC: device.get("mac", ""),
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )

    async def async_step_reauth(self, entry_data: dict) -> Any:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict | None = None) -> Any:
        errors: dict = {}
        if user_input is not None and self._reauth_entry is not None:
            err, _, _ = await _login_and_list(
                self.hass, user_input[CONF_PHONE], user_input[CONF_PASSWORD]
            )
            if err is None:
                entry = self._reauth_entry
                data = dict(entry.data)
                data[CONF_PHONE] = user_input[CONF_PHONE]
                data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                self.hass.config_entries.async_update_entry(entry, data=data)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = err
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=LOGIN_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RunlaiOptionsFlow:
        return RunlaiOptionsFlow(config_entry)


class RunlaiOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        src = {**self._config_entry.data, **self._config_entry.options}
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=int(src.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))): vol.All(int, vol.Range(min=120)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
