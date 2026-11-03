# -*- coding: utf-8 -*-
"""润莱智联(RunLuckyIot)软水机接入.

从「润莱智联」App 逆向得到的云端接口(均为润新自有云, 明文 HTTP):
  - 登录:  POST /connect/token  OAuth2 password 模式(client_id=RunLuckyIot_App), token 有效期约 365 天
  - 实时:  GET /api/run-lucky/device/app/device/get-device-with--data?id={deviceId}
  - 统计:  POST /api/run-lucky/device/app/device/device-flow-statistics
           body {deviceId, startTime, endTime, reportTimeType}  (1=月 3=日)
  - 再生:  POST /api/run-lucky/device/app/device-control/forced-regeneration?id={deviceId}

集成持有手机号+密码, token 存内存, 401 时自动重新登录, 无需人工续期.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MAC,
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PATH_DEVICE_DATA,
    PATH_DEVICE_LIST,
    PATH_FLOW_STATISTICS,
    PATH_FORCED_REGENERATION,
    PATH_TOKEN,
    STD_DAILY,
    STD_LAST_EVENT,
    STD_MONTH_LAST,
    STD_MONTH_THIS,
    STD_RESIDUAL,
    STD_STATUS,
    STD_UPDATED,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


class RunlaiClient:
    """润莱智联云端 API 客户端(自动登录)."""

    def __init__(self, session: aiohttp.ClientSession, phone: str, password: str) -> None:
        self._session = session
        self._phone = phone
        self._password = password
        self._token: str | None = None

    async def _login(self) -> str:
        form = {
            "__tenant": "",
            "grant_type": "password",
            "scope": "RunLuckyIot",
            "username": self._phone,
            "password": self._password,
            "client_id": "RunLuckyIot_App",
        }
        async with self._session.post(
            API_BASE + PATH_TOKEN, data=form,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            text = await resp.text()
            if resp.status == 429:
                raise UpdateFailed("登录接口限流(429), 服务器要求稍后重试")
            if resp.status != 200:
                raise ConfigEntryAuthFailed(
                    "登录失败(HTTP %s): %s —— 请在集成配置里更新手机号/密码" % (resp.status, text[:150])
                )
            payload = _loads(text)
            token = (payload or {}).get("access_token")
            if not token:
                raise ConfigEntryAuthFailed("登录返回无 access_token: %s" % text[:150])
            self._token = token
            _LOGGER.info("润莱智联登录成功, token 有效期 %s 秒", payload.get("expires_in"))
            return token

    async def request(
        self, method: str, path: str, *, params: dict | None = None,
        json_body: dict | None = None, _retry: bool = True,
    ) -> Any:
        """带 token 的请求; 401 自动重新登录一次."""
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": aiohttp.ClientTimeout(total=25),
        }
        if params:
            kwargs["params"] = params
        if json_body is not None:
            kwargs["json"] = json_body
        async with self._session.request(method, API_BASE + path, **kwargs) as resp:
            text = await resp.text()
            if resp.status == 429:
                raise UpdateFailed("接口限流(429), 服务器要求稍后重试")
            if resp.status in (401, 403):
                if _retry:
                    self._token = None
                    await self._login()
                    return await self.request(
                        method, path, params=params, json_body=json_body, _retry=False
                    )
                raise ConfigEntryAuthFailed("接口持续返回 HTTP %s" % resp.status)
            if resp.status == 404:
                raise UpdateFailed("接口 404: %s (接口可能变更)" % path)
            if resp.status >= 400:
                raise UpdateFailed("接口 HTTP %s: %s" % (resp.status, text[:200]))
        return _loads(text) if text.strip() else None

    # ---- 业务接口 ----
    async def get_device_list(self) -> list[dict]:
        return await self.request("GET", PATH_DEVICE_LIST) or []

    async def get_device_data(self, device_id: str) -> dict:
        return await self.request(
            "GET", PATH_DEVICE_DATA, params={"id": device_id}
        ) or {}

    async def flow_statistics(self, device_id: str, report_time_type: int, days: int) -> list[dict]:
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
        end = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return await self.request(
            "POST", PATH_FLOW_STATISTICS,
            json_body={
                "deviceId": device_id, "startTime": start,
                "endTime": end, "reportTimeType": report_time_type,
            },
        ) or []

    async def forced_regeneration(self, device_id: str) -> Any:
        return await self.request(
            "POST", PATH_FORCED_REGENERATION, params={"id": device_id}
        )


def _loads(text: str) -> Any:
    import json
    try:
        return json.loads(text)
    except ValueError:
        return None


class RunlaiCoordinator(DataUpdateCoordinator):
    """轮询实时状态 + 月度用水统计."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        cfg = {**entry.data, **entry.options}
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(
                seconds=int(cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            ),
        )
        self.entry = entry
        self.client = RunlaiClient(
            async_get_clientsession(hass), cfg[CONF_PHONE], cfg[CONF_PASSWORD]
        )
        self.device_id: str = cfg[CONF_DEVICE_ID]
        self.device_name: str = cfg.get(CONF_DEVICE_NAME, "润莱软水机")

    async def _async_update_data(self) -> dict:
        try:
            device = await self.client.get_device_data(self.device_id)
        except aiohttp.ClientError as err:
            raise UpdateFailed("网络错误: %s" % err) from err
        if not device or "protocolData" not in (device or {}):
            raise UpdateFailed("设备数据为空(设备可能被解绑)")

        pd = device["protocolData"]
        result: dict[str, Any] = dict(pd)  # protocolData 原样放入, 供 binary_sensor 使用

        # 月度用水统计(取本月与上月)
        try:
            monthly = await self.client.flow_statistics(self.device_id, 1, 400)
        except (UpdateFailed, aiohttp.ClientError) as err:
            _LOGGER.warning("月度统计获取失败(不影响实时数据): %s", err)
            monthly = []
        now = datetime.now()
        this_month, last_month = now.strftime("%Y-%m"), (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        for item in monthly:
            key = str(item.get("dateTime", ""))[:7]
            if key == this_month:
                result[STD_MONTH_THIS] = item.get("flowRate")
            elif key == last_month:
                result[STD_MONTH_LAST] = item.get("flowRate")

        result[STD_LAST_EVENT] = device.get("lastEventTime")
        result["_mac"] = device.get("mac")
        result[STD_STATUS] = "ok"
        result[STD_UPDATED] = datetime.now().astimezone().isoformat(timespec="seconds")
        _LOGGER.debug("runlai_softener 更新成功: 剩余制水量=%s 今日=%s",
                      pd.get(STD_RESIDUAL), pd.get(STD_DAILY))
        return result


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = RunlaiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # 服务: 强制再生
    async def _force_regen(call: ServiceCall) -> None:
        target_id = call.data.get("device_id") or coordinator.device_id
        await coordinator.client.forced_regeneration(target_id)

    hass.services.async_register(DOMAIN, "forced_regeneration", _force_regen)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, "forced_regeneration")
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
