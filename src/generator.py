import json
import random
import uuid
from datetime import date, datetime, timedelta

TOURS = [
    {"tour_id": "T1", "tour_name": "Onboarding",    "total_steps": 5},
    {"tour_id": "T2", "tour_name": "New dashboard", "total_steps": 3},
    {"tour_id": "T3", "tour_name": "Billing setup", "total_steps": 4},
]
PLANS = ["free", "pro", "enterprise"]
N_ACCOUNTS = 80


def _account_of(user_id: str) -> str:
    return f"a{int(user_id[1:]) % N_ACCOUNTS + 1:03d}"


def generate_events(day: date, n_sessions: int, rnd: random.Random) -> list[dict]:
    """Чисті події: кожна сесія = один тур, який користувач проходить або кидає на якомусь кроці."""
    events = []
    for _ in range(n_sessions):
        user_id = f"u{rnd.randint(1, 500):04d}"
        tour = rnd.choice(TOURS)
        session_id = str(uuid.UUID(int=rnd.getrandbits(128)))
        device = {"os": rnd.choice(["Windows", "macOS", "iOS", "Android"]),
                  "browser": rnd.choice(["Chrome", "Safari", "Edge", "Firefox"])}
        ts = datetime.combine(day, datetime.min.time()) + timedelta(seconds=rnd.randint(0, 86_000))

        def make(event_type, step=None):
            nonlocal ts
            ts += timedelta(seconds=rnd.randint(2, 40))
            return {
                "event_id": str(uuid.UUID(int=rnd.getrandbits(128))),
                "event_ts": ts.isoformat(),
                "user_id": user_id,
                "account_id": _account_of(user_id),
                "session_id": session_id,
                "event_type": event_type,
                "tour_id": tour["tour_id"],
                "step_number": step,
                "properties": {"device": device,
                               "page_url": "/app/" + tour["tour_name"].lower().replace(" ", "-"),
                               "locale": rnd.choice(["en-US", "uk-UA", "de-DE"])},
            }

        events.append(make("tour_shown"))
        for step in range(1, tour["total_steps"] + 1):
            events.append(make("step_viewed", step))
            if rnd.random() < 0.12:                      # користувач закрив тур на цьому кроці
                events.append(make("tour_dismissed", step))
                break
            events.append(make("step_completed", step))
        else:                                            # цикл дійшов до кінця без break
            events.append(make("tour_completed", tour["total_steps"]))
            if rnd.random() < 0.3:
                events.append(make("cta_clicked"))
    return events


def add_data_issues(events: list[dict], day_index: int, rnd: random.Random) -> list[str]:
    """Додає реалістичні проблеми й повертає рядки JSON lines."""
    out = []
    for e in events:
        e = dict(e)
        if day_index >= 2:                               # з 3-го дня з'являється нове поле
            e["experiment_variant"] = rnd.choice(["A", "B"])
        r = rnd.random()
        if r < 0.01:
            e["user_id"] = None                          # відсутній користувач
        elif r < 0.015:
            e["event_type"] = "tour_restarted"           # невідомий тип події
        elif r < 0.035:                                  # пізня подія: час з учорашнього дня
            e["event_ts"] = (datetime.fromisoformat(e["event_ts"]) - timedelta(days=1)).isoformat()
        out.append(json.dumps(e))
        if rnd.random() < 0.03:                          # дублікат (повторна відправка)
            out.append(json.dumps(e))
    out.append('{"event_id": "broken-1", "event_ts": ')   # зіпсований рядок
    return out


def generate_account_changes(day: date, day_index: int, rnd: random.Random) -> list[dict]:
    """1-й день: знімок усіх акаунтів. Далі: кілька змін плану на день."""
    ts = datetime.combine(day, datetime.min.time()) + timedelta(hours=rnd.randint(8, 20))
    if day_index == 0:
        ids = range(1, N_ACCOUNTS + 1)
        return [{"account_id": f"a{i:03d}", "plan": rnd.choice(["free", "free", "pro"]),
                 "company_size": rnd.choice(["1-10", "11-50", "51-200", "200+"]),
                 "updated_at": ts.isoformat()} for i in ids]
    changed = rnd.sample(range(1, N_ACCOUNTS + 1), k=rnd.randint(2, 5))
    return [{"account_id": f"a{i:03d}", "plan": rnd.choice(PLANS[1:]),
             "company_size": rnd.choice(["1-10", "11-50", "51-200", "200+"]),
             "updated_at": ts.isoformat()} for i in changed]