import random
from datetime import datetime, timedelta

from model import PaymentMethod, VisitEvent

from config import TRANSIT_MINUTES, VISIT_MINUTES, CLOSE_MINUTES


def assign_delivery_quantity(planned_quantity: int) -> int:
    """70% full delivery, 20% partial, 10% zero."""
    roll = random.random()
    if roll < 0.70:
        return planned_quantity
    elif roll < 0.90:
        return random.randint(1, planned_quantity - 1) if planned_quantity > 1 else 0
    return 0


def assign_arrival_time(last_departure_time: datetime) -> datetime:
    """Arrival = last departure + random transit (20–120 min, steps of 10)."""
    minutes = random.choice(range(*TRANSIT_MINUTES))
    return last_departure_time + timedelta(minutes=minutes)


def assign_signature_time(arrival_time: datetime) -> datetime:
    """Signature happens during the visit (20–110 min after arrival)."""
    minutes = random.choice(range(*VISIT_MINUTES))
    return arrival_time + timedelta(minutes=minutes)


def assign_departure_time(signature_time: datetime) -> datetime:
    """Driver leaves after signing (5–115 min after signature)."""
    minutes = random.choice(range(*CLOSE_MINUTES))
    return signature_time + timedelta(minutes=minutes)


def assign_payment_method() -> str:
    return random.choice(list(PaymentMethod)).value


def simulate_visit(row: dict, cache_last_time: datetime) -> tuple[VisitEvent, datetime, int]:
    """
    Simulate a single delivery visit.
    Time chain: last_departure → arrival → signature → departure → next visit
    """
    row["delivery_quantity"] = assign_delivery_quantity(int(row["quantity"]))
    row["arrival_time"]      = assign_arrival_time(cache_last_time)
    row["signature_time"]    = assign_signature_time(row["arrival_time"])
    row["departure_time"]    = assign_departure_time(row["signature_time"])
    row["payment_method"]    = assign_payment_method()

    event = VisitEvent(
        date=str(row["date"]),
        customer_id=str(row["customer_id"]),
        route_id=str(row["route_id"]),
        order_id=str(row["order_id"]),
        warehouse_code=str(row["warehouse_code"]),
        quantity=int(row["quantity"]),
        delivery_quantity=row["delivery_quantity"],
        arrival_time=row["arrival_time"],
        signature_time=row["signature_time"],
        departure_time=row["departure_time"],
        payment_method=row["payment_method"],
    )

    return event, row["departure_time"], int(row["sequence"])