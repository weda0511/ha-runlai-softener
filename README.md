# 润莱智联软水机 (Runlai Softener) — Home Assistant 集成

把「**润莱智联**」App（温州市润新机械 / 润莱 RunLucky）控制的**中央软水机**接进 Home Assistant：实时运行状态、用水量、缺盐/漏水报警全部本地化展示。

> English summary: A custom integration for Runlai (RunLuckyIot / Runxin) water softeners. It talks to the vendor's cloud API (reverse-engineered from the Android app) using your app account, and exposes sensors for remaining capacity, water consumption, flow rate, hardness, salt/leak alarms and more. Chinese-only vendor cloud, so the rest of this README is in Chinese.

## 原理

- 润莱软水机的 WiFi 模块是博联（BroadLink）OEM 模块，本地协议为未公开的 `0x520f`，HA 官方 broadlink 集成判定不支持；
- 但设备状态/控制走的是润新自有云 `http://api.admin-runxin.com`（App 逆向得到），登录为 OAuth2 password 模式，**token 有效期约 365 天**；
- 本集成用你的 App 手机号 + 密码自动登录，token 存内存，401 自动重登，**无需抓包、无需人工续期**。

## 传感器一览（16 sensor + 10 binary_sensor）

| 实体 | 说明 | 单位 |
|:--|:--|:--|
| 剩余制水量 | 当前周期还能制多少软水 | m³ |
| 今日用水 | 当日软水用水量 | m³ |
| 本月用水 / 上月用水 | 云端月度统计 | m³ |
| 周均用水 | 滚动周均 | m³ |
| 周期制水量 | 一个再生周期的总制水量 | m³ |
| 瞬时流量 | 实时流量 | m³/h |
| 原水硬度 | 设置的原水硬度 | mg/L |
| 树脂体积 | 树脂装填量 | L |
| 单次加盐量 | 再生一次的加盐量 | kg |
| 再生次数 | 累计再生次数 | 次 |
| 阀位状态 | 运行/反洗/吸盐慢洗/盐箱注水/正洗 | — |
| 设备时间 / 设备最后上报 / 接口状态 / 最后更新 | 心跳信息 | — |

binary_sensor：缺盐报警、缺盐提醒、树脂更换提醒、滤料更换提醒、**漏水报警**、度假模式、时钟芯片故障、存储器故障、多位置/无位置信号故障。

## 服务

- `runlai_softener.forced_regeneration` —— 立即强制再生（等价于 App 里的「强制再生」按钮），可选参数 `device_id`。

## 安装

### HACS（自定义仓库）

1. HACS → 设置 → 添加自定义仓库，填本仓库地址，类别选 **集成**；
2. 搜索「润莱」安装，重启 Home Assistant；
3. 设置 → 设备与服务 → 添加集成 → 「润莱智联软水机」→ 输入 App 手机号和密码 → 选择设备（账号下有多台时会让你选）。

### 手动

把 `custom_components/runlai_softener/` 拷到 `<config>/custom_components/` 下，重启。

## 注意

- 云端接口为 **HTTP 明文**（厂商设计如此），意味着凭据与数据在公网明文传输——这是润莱自己的安全问题，介意请勿用；
- 接口逆向自 App v0.2.x（2026-11），接口变更可能导致失效，届时更新集成；
- 控制类只做了「强制再生」；修改参数（硬度、再生时间等）请继续用官方 App。

## 致谢

架构参考 [ha_hfwater](https://github.com/shaonianchen/ha_hfwater) 等社区水费集成。
