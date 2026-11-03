# -*- coding: utf-8 -*-
"""润莱智联软水机集成常量."""
from __future__ import annotations

DOMAIN = "runlai_softener"

CONF_PHONE = "phone"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_MAC = "device_mac"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 300  # 秒, 实时状态轮询

API_BASE = "http://api.admin-runxin.com"
PATH_TOKEN = "/connect/token"
PATH_DEVICE_LIST = "/api/run-lucky/device/app/device-lookup/get-device-list"
PATH_DEVICE_DATA = "/api/run-lucky/device/app/device/get-device-with--data"
PATH_FLOW_STATISTICS = "/api/run-lucky/device/app/device/device-flow-statistics"
PATH_FORCED_REGENERATION = "/api/run-lucky/device/app/device-control/forced-regeneration"

# ---- 归一化数据字段 ----
STD_RESIDUAL = "residual_water_production"       # 剩余制水量 m³
STD_DAILY = "daily_water_consumption"            # 今日用水 m³
STD_WEEKLY_AVG = "average_weekly_water_consumption"  # 周均用水 m³
STD_PERIODIC = "periodic_water_production"       # 周期制水量 m³
STD_FLOW_RATE = "flow_rate"                      # 瞬时流量 m³/h
STD_HARDNESS = "raw_water_hardness"              # 原水硬度 mg/L
STD_RESIN = "resin_volume"                       # 树脂体积 L
STD_SALT_ADD = "salt_addition"                   # 每次加盐量 kg
STD_REGEN_TIMES = "regeneration_times"           # 再生次数
STD_STATION = "station"                          # 阀位(0=运行/制水)
STD_CURRENT_TIME = "device_current_time"         # 设备时间
STD_LAST_EVENT = "last_event_time"               # 最后上报
STD_STATUS = "status"                            # ok / error
STD_UPDATED = "updated"                          # 集成更新时间
STD_MONTH_THIS = "month_water"                   # 本月用水 m³(统计接口)
STD_MONTH_LAST = "last_month_water"              # 上月用水 m³(统计接口)

# binary_sensor 字段(bool 型, 均取自 protocolData)
BINARY_FIELDS = {
    "salt_shortage_alarm": ("缺盐报警", "mdi:alert-octagon"),
    "salt_shortage_reminder": ("缺盐提醒", "mdi:alert-outline"),
    "resin_replacement_reminder": ("树脂更换提醒", "mdi:sync-alert"),
    "filter_material_reminder": ("滤料更换提醒", "mdi:filter-remove-outline"),
    "water_leakage": ("漏水报警", "mdi:water-alert"),
    "vacation_pattern": ("度假模式", "mdi:beach"),
    "clock_chip_fault": ("时钟芯片故障", "mdi:clock-alert"),
    "memory_error_fault": ("存储器故障", "mdi:memory"),
    "multiple_position_signal_fault": ("多位置信号故障", "mdi:sitemap-outline"),
    "no_position_signal_fault": ("无位置信号故障", "mdi:signal-off"),
}
