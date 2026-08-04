"""
Thin REST client for Firestore, used instead of the Firebase JS SDK so that
none of this traffic depends on gstatic.com / the Firebase browser SDK.
Matches the project used by the existing HTML app (pss-checklist).
"""
import requests
import datetime

FIREBASE_API_KEY = "AIzaSyAHzVTjMA0ErfhEhP7a1kQJBCNEV9yMxRo"
PROJECT_ID = "pss-checklist"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

ADMIN_ID = "admin"
ADMIN_PIN = "1111"

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
ALT_GROUPS = [["Mon", "Wed", "Fri"], ["Tue", "Thu", "Sat"]]
TWICE_PAIRS = [["Mon", "Thu"], ["Tue", "Fri"], ["Wed", "Sat"]]
JS_DAY_TO_NAME = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


# ── low level value (de)serialization for Firestore REST "fields" format ──

def _to_value(v):
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_to_value(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _to_value(val) for k, val in v.items()}}}
    return {"stringValue": str(v)}


def _from_value(field):
    if field is None:
        return None
    if "stringValue" in field:
        return field["stringValue"]
    if "booleanValue" in field:
        return field["booleanValue"]
    if "integerValue" in field:
        return int(field["integerValue"])
    if "doubleValue" in field:
        return field["doubleValue"]
    if "nullValue" in field:
        return None
    if "arrayValue" in field:
        vals = field["arrayValue"].get("values", [])
        return [_from_value(v) for v in vals]
    if "mapValue" in field:
        fields = field["mapValue"].get("fields", {})
        return {k: _from_value(v) for k, v in fields.items()}
    return None


def doc_to_dict(doc_json):
    fields = doc_json.get("fields", {})
    return {k: _from_value(v) for k, v in fields.items()}


def dict_to_fields(d):
    return {k: _to_value(v) for k, v in d.items()}


# ── generic Firestore REST operations ──

def get_document(path: str):
    """path like 'employees/6006'. Returns dict or None if missing."""
    url = f"{BASE_URL}/{path}?key={FIREBASE_API_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return None
    return doc_to_dict(resp.json())


def set_document(path: str, data: dict, merge: bool = True):
    """path like 'employees/6006/state/main'."""
    url = f"{BASE_URL}/{path}?key={FIREBASE_API_KEY}"
    if merge:
        mask = "&".join(f"updateMask.fieldPaths={k}" for k in data.keys())
        url += f"&{mask}" if mask else ""
    body = {"fields": dict_to_fields(data)}
    method = requests.patch if merge else requests.patch
    resp = method(url, json=body, timeout=10)
    return resp.status_code == 200


def list_collection(collection: str):
    """Returns list of (doc_id, data) tuples for all docs in a top-level collection."""
    url = f"{BASE_URL}/{collection}?key={FIREBASE_API_KEY}&pageSize=300"
    out = []
    while True:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            break
        data = resp.json()
        for doc in data.get("documents", []):
            doc_id = doc["name"].rsplit("/", 1)[-1]
            out.append((doc_id, doc_to_dict(doc)))
        token = data.get("nextPageToken")
        if not token:
            break
        url = f"{BASE_URL}/{collection}?key={FIREBASE_API_KEY}&pageSize=300&pageToken={token}"
    return out


# ── scheduling logic (ported from employee_dashboard.html) ──

def build_schedule_from_sites(sites):
    sched = {d: [] for d in DAYS}
    everyday = [s for s in sites if s.get("freq") == "E"]
    alt = [s for s in sites if s.get("freq") == "Alt"]
    twice = [s for s in sites if s.get("freq") not in ("E", "Alt")]

    for s in everyday:
        for d in DAYS:
            sched[d].append(s["id"])
    for i, s in enumerate(alt):
        for d in ALT_GROUPS[i % 2]:
            sched[d].append(s["id"])
    for i, s in enumerate(twice):
        for d in TWICE_PAIRS[i % 3]:
            sched[d].append(s["id"])
    return sched


def sites_for_date(sites, blocked_names, date: datetime.date):
    """Returns list of site dicts scheduled for the given date, matching the HTML app's logic."""
    weekday_name = JS_DAY_TO_NAME[(date.weekday() + 1) % 7]  # python Mon=0 -> JS Sun=0 alignment
    if weekday_name == "Sun":
        return []  # no schedule defined for Sunday in DAYS
    schedule = build_schedule_from_sites(sites)
    ids_today = schedule.get(weekday_name, [])
    by_id = {s["id"]: s for s in sites}
    result = []
    for sid in ids_today:
        site = by_id.get(sid)
        if site and site.get("name") not in blocked_names:
            result.append(site)
    return result


def date_key(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")
