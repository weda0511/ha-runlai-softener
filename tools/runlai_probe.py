#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""润莱智联（runxin RunLuckyIot）云端接口探针
从 APK(H5壳) 逆向得出：
  - 登录:   POST http://api.admin-runxin.com/connect/token  (OpenIddict password grant)
  - 设备:   /api/run-lucky/device/app/device/get-device-with--data?id={deviceId}
  - 列表:   /api/run-lucky/device/app/device-control/get-device-list
  - 详情:   /api/run-lucky/device/app/device-lookup/get-device-detail?familyId&deviceId
  - 用水:   POST /api/run-lucky/device/app/device/device-flow-statistics {deviceId,startTime,endTime,reportTimeType}
  - 再生:   POST /api/run-lucky/device/app/device-control/forced-regeneration {querys}
用法:
  python runlai_probe.py login <手机号> <密码>     # 登录并缓存 token
  python runlai_probe.py devices                   # 设备列表 + 详情
  python runlai_probe.py data <deviceId>           # 设备实时数据(protocolData)
  python runlai_probe.py flow <deviceId> [天数]    # 用水量统计(默认90天)
  python runlai_probe.py check                     # 体检:token 有效性
"""
import json, sys, os, time, urllib.request, urllib.parse, urllib.error

BASE = "http://api.admin-runxin.com"
TOKEN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".runlai_token.json")

def http(method, path, token=None, form=None, body=None, timeout=25):
    url = BASE + path
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json;charset=UTF-8"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
        code = 200
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        code = e.code
    try:
        return code, json.loads(raw) if raw.strip() else {}
    except Exception:
        return code, raw


def login(phone, password, save=True):
    form = {"__tenant": "", "grant_type": "password", "scope": "RunLuckyIot",
            "username": phone, "password": password, "client_id": "RunLuckyIot_App"}
    code, r = http("POST", "/connect/token", form=form)
    if code == 200 and isinstance(r, dict) and r.get("access_token"):
        if save:
            with open(TOKEN_CACHE, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), **{k: r.get(k) for k in
                          ("access_token", "refresh_token", "expires_in", "token_type")}}, f, ensure_ascii=False)
        print("[OK] 登录成功")
        for k in ("token_type", "expires_in", "scope"):
            if r.get(k) is not None:
                print("   %-12s %s" % (k, r[k]))
        print("   access_token %s...%s" % (r["access_token"][:20], r["access_token"][-8:]))
        return r["access_token"]
    print("[FAIL] HTTP %s %s" % (code, json.dumps(r, ensure_ascii=False)[:300] if isinstance(r, dict) else str(r)[:300]))
    return None


def load_token():
    if not os.path.exists(TOKEN_CACHE):
        sys.exit("无缓存 token，先: python runlai_probe.py login <手机号> <密码>")
    d = json.load(open(TOKEN_CACHE, encoding="utf-8"))
    age = time.time() - d.get("ts", 0)
    print("[i] 缓存 token 已 %d 分钟" % (age / 60))
    return d["access_token"]


def jdump(label, r, limit=2000):
    s = json.dumps(r, ensure_ascii=False, indent=2)
    print("\n=== %s ===" % label)
    print(s[:limit] + ("\n...[截断]" if len(s) > limit else ""))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd == "login":
        if len(sys.argv) < 4:
            sys.exit("用法: login <手机号> <密码>")
        login(sys.argv[2], sys.argv[3])
        return

    tok = load_token()

    if cmd == "check":
        code, r = http("GET", "/api/run-lucky/device/app/device-control/get-device-list", token=tok)
        print("[check] HTTP", code)
        jdump("get-device-list", r)

    elif cmd == "devices":
        code, r = http("GET", "/api/run-lucky/device/app/device-control/get-device-list", token=tok)
        print("[devices] HTTP", code)
        jdump("设备列表", r, 4000)

    elif cmd == "data":
        did = sys.argv[2] if len(sys.argv) > 2 else ""
        code, r = http("GET", "/api/run-lucky/device/app/device/get-device-with--data", token=tok,
                       form=None)
        # 该接口为 GET querys: /get-device-with--data?id=xxx
        code, r = http("GET", "/api/run-lucky/device/app/device/get-device-with--data?id=%s" % did, token=tok)
        print("[data] HTTP", code)
        jdump("设备实时数据", r, 6000)

    elif cmd == "flow":
        did = sys.argv[2] if len(sys.argv) > 2 else ""
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 90
        start = time.strftime("%Y-%m-%dT00:00:00", time.localtime(time.time() - days * 86400))
        end = time.strftime("%Y-%m-%dT%H:%M:%S")
        code, r = http("POST", "/api/run-lucky/device/app/device/device-flow-statistics", token=tok,
                       body={"deviceId": did, "startTime": start, "endTime": end, "reportTimeType": 0})
        print("[flow] HTTP", code, "range", start, "→", end)
        jdump("用水量统计", r, 6000)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
