"""Return-value contracts for dashboard / scheduling / snapshot utilities.

This module is meant to be the single source of truth for:
- what each function returns (TypedDict / type aliases)
- a copy-pasteable EXAMPLE_* payload for each return type

Keep this file small, explicit, and stable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, TypedDict, Literal


# ---------- Schedule ----------

RoomId = str
SlotId = str  # "1", "2", ...


Schedule = Dict[SlotId, List[RoomId]]
"""Example: {"1": ["R1", "R1B"], "2": [...]}"""


SCHEDULE_EXAMPLE: Schedule = {
    "1": ["R1", "R1B", "R2"],
    "2": ["R1", "R3"],
}


# ---------- Room info (static config) ----------

class RoomInfo(TypedDict):
    room_id: str
    building: str
    type: str
    capacity: int
    floor: str


ROOM_INFO_EXAMPLE: RoomInfo = {
    "room_id": "R1",
    "building": "R",
    "type": "Sala gradonata",
    "capacity": 300,
    "floor": "0",
}


RoomsInfo = List[RoomInfo]
"""List of RoomInfo items loaded from setting_config.json"""


ROOMS_INFO_EXAMPLE: RoomsInfo = [ROOM_INFO_EXAMPLE]


# ---------- Parsed timestamp parts ----------

class TimestampParts(TypedDict):
    month: int               # 1..12
    weekday: str             # e.g. "Monday"
    hour: int                # 0..23
    minute: int              # 0..59


TIMESTAMP_PARTS_EXAMPLE: TimestampParts = {
    "month": 1,
    "weekday": "Wednesday",
    "hour": 10,
    "minute": 20,
}


# ---------- Snapshot (latest sensor values cache) ----------

DeviceType = Literal["temperature", "wifi"]  # extend if needed
IndexNumber = str  # typically "1", "2", ...

class SnapshotItem(TypedDict):
    value: Any
    received_at: int  # unix timestamp (seconds)


Snapshot = Dict[RoomId, Dict[DeviceType, Dict[IndexNumber, SnapshotItem]]]
"""Structure expected by pick_latest_value():
snapshot[room_id][device_type][index_number] = {"value": ..., "received_at": ...}
"""


SNAPSHOT_EXAMPLE: Snapshot = {
    "R1": {
        "temperature": {
            "1": {"value": 26.5, "received_at": 1735756800},
        },
        "wifi": {
            "1": {"value": 42, "received_at": 1735756810},
        },
    }
}


# ---------- Dashboard payload (student dashboard response) ----------

class RoomDashboardItem(RoomInfo, total=False):
    """RoomInfo plus dynamic fields computed per request."""

    available: bool
    temperature: float
    students: int


ROOM_DASHBOARD_ITEM_EXAMPLE: RoomDashboardItem = {
    **ROOM_INFO_EXAMPLE,
    "available": True,
    "temperature": 27.3,
    "students": 18,
}


StudentDashboardResponse = List[RoomDashboardItem]
"""Return type for get_student_dashboard_response()."""


STUDENT_DASHBOARD_RESPONSE_EXAMPLE: StudentDashboardResponse = [ROOM_DASHBOARD_ITEM_EXAMPLE]


# ---------- AC decision payload ----------

class ACDecision(TypedDict, total=False):
    """Decision can be True/False/None (None = keep previous / no change / not applicable)."""

    decision: Optional[bool]
    decided_time: int  # unix timestamp (seconds)


ACDecisionMap = Dict[RoomId, ACDecision]


AC_DECISION_MAP_EXAMPLE: ACDecisionMap = {
    "R1": {"decision": True, "decided_time": 1735756820},
    "R2": {"decision": None, "decided_time": 1735756820},
}



#Controller
"""
contracts.py

This file documents the data contracts used by Controller.py:
- Catalog HTTP response shape
- MQTT sensor topics + payload
- Controller snapshot cache structure
- Analyzer decision output shape
- MQTT actuator cmd topic + payload
- REST responses

(Keep this as the single source of truth for formats.)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


# ============================================================
# 1) Catalog HTTP Contract
# ============================================================

class CatalogDeviceLocation(TypedDict, total=False):
    room: str


class CatalogDeviceMqttTopics(TypedDict, total=False):
    """
    The controller expects these keys when present:
      - val: topic for sensor values (subscribe)
      - cmd: topic for actuator commands (publish)
    """
    val: str
    cmd: str


class CatalogDevice(TypedDict, total=False):
    """
    Minimal device fields used by Controller:

    - id: string id, used to filter sensor_1 / actuator_1
    - type: "wifi" or "temperature" (controller filters by these)
    - location.room: used to map topics by room_id
    - mqtt_topics.val: subscribe topic for sensor values
    - mqtt_topics.cmd: publish topic for actuator commands
    """
    id: str
    type: str
    location: CatalogDeviceLocation
    mqtt_topics: CatalogDeviceMqttTopics


# Controller fetches:
#   GET {catalog_base_url}/devices
# and expects the response to be:
CatalogDevicesResponse = List[CatalogDevice]
# (If the HTTP response is a dict, controller wraps it into a list in runtime.)


# ============================================================
# 2) MQTT Topics & Payloads (Sensors -> Controller)
# ============================================================

# Topic parsing rule used by Controller._parse_topic(topic):
# - topic must end with "/value"
# - room_id      = parts[-4]
# - device_type  = parts[-3]
# - index_number = parts[-2]   (NOTE: string, because from topic text)
#
# So a compatible topic shape is:
#   .../{room_id}/{device_type}/{index_number}/value

class SensorIncomingPayload(TypedDict, total=False):
    """
    JSON payload expected on sensor value topics.

    Controller reads:
      id -> sensor_id
      v  -> value
      u  -> unit
      t  -> sensor_timestamp

    received_at is added by the controller when the message arrives.
    """
    id: str
    v: Any
    u: Any
    t: Any


# ============================================================
# 3) Controller Snapshot Cache (latest_by_room)
# ============================================================

RoomId = str
DeviceType = str
IndexNumber = str  # important: parsed from MQTT topic, so it's a string

class SnapshotItem(TypedDict, total=False):
    sensor_id: str
    value: Any
    unit: Any
    sensor_timestamp: Any
    received_at: float


# Controller stores snapshot as:
# latest_by_room[room_id][device_type][index_number] = SnapshotItem
SnapshotByIndex = Dict[IndexNumber, SnapshotItem]
SnapshotByDeviceType = Dict[DeviceType, SnapshotByIndex]
ControllerSnapshot = Dict[RoomId, SnapshotByDeviceType]


# ============================================================
# 4) Analyzer -> Controller Decision Contract (AC decision)
# ============================================================

class ACDecisionItem(TypedDict, total=False):
    """
    Output per room returned by OccupancyAnalyzer.deciede_ac_from_room_info().

    - decide: True/False/None
      True  => should turn ON
      False => should turn OFF
      None  => no action / insufficient data
    - decide_time: a timestamp (float) when the decision was computed
    """
    decide: Optional[bool]
    decide_time: Optional[float]


ACDecisionByRoom = Dict[RoomId, ACDecisionItem]


# ============================================================
# 5) MQTT Actuator CMD (Controller -> Actuator)
# ============================================================

# The controller publishes to the "cmd" topic provided by catalog:
#   temperature_cmd_topic_by_room[room_id] = device["mqtt_topics"]["cmd"]

ACStatus = Literal["ON", "OFF"]

class ActuatorCmdPayload(TypedDict, total=False):
    """
    JSON payload published by Controller.send_ac_cmd().

    Always includes:
      - status: "ON" or "OFF"

    Optionally includes:
      - mode: string (if caller passes it)
    """
    status: ACStatus
    mode: str


# Example payloads sent:
#   {"status": "ON"}
#   {"status": "OFF"}
#   {"status": "ON", "mode": "..."}


# ============================================================
# 6) REST API Responses (CherryPy)
# ============================================================

# GET "/" returns: OccupancyAnalyzer.get_student_dashboard_response(request_timestamp, snapshot)
# The exact dashboard schema depends on analyzer implementation, but the controller returns JSON.

# GET "/debug/cache" returns: ControllerSnapshot as JSON.


# ============================================================
# 7) Timing / Throttle Rules (Controller side)
# ============================================================

# Controller applies command throttling rules before publishing:
# - if a room has never sent a cmd: allow
# - else allow only if:
#     (now - last_sent_time) >= 30 seconds
#   AND
#     new_state != last_state
#
# This is stored in controller.ac_last_sent_by_room:
#   { room_id: {"status": bool, "time": float} }
