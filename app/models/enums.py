from enum import StrEnum


class TransportMode(StrEnum):
    train = "train"
    bus = "bus"
    tram = "tram"
    metro = "metro"


class IncidentType(StrEnum):
    delay = "delay"
    cancellation = "cancellation"
    signalling_issue = "signalling_issue"
    weather = "weather"
    staff_shortage = "staff_shortage"
    congestion = "congestion"
    vehicle_fault = "vehicle_fault"
    other = "other"


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(StrEnum):
    open = "open"
    monitoring = "monitoring"
    resolved = "resolved"
