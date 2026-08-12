def model_snapshot(instance, fields):
    data = {}
    for field in fields:
        value = getattr(instance, field)
        if hasattr(value, "pk"):
            data[field] = {"id": value.pk, "repr": str(value)}
        else:
            data[field] = value
    return data
