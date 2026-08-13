from datetime import date
from datetime import datetime
from decimal import Decimal

from django.db.models.fields.files import FieldFile


def serialize_audit_value(value):
    if hasattr(value, "pk"):
        return {"id": value.pk, "repr": str(value)}
    if isinstance(value, FieldFile):
        return value.name or ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def model_snapshot(instance, fields):
    data = {"id": instance.pk}
    for field in fields:
        data[field] = serialize_audit_value(getattr(instance, field))
    return data
