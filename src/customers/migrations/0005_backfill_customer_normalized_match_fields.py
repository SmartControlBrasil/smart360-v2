from django.db import migrations


BACKFILL_BATCH_SIZE = 500


def _normalize_phone(value):
    digits = "".join(char for char in (value or "") if char.isdigit())
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    return digits


def _normalize_domain(value):
    from urllib.parse import urlsplit

    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    domain = (parsed.netloc or "").split("@")[-1].lower()
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def backfill_normalized_match_fields(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    last_pk = 0
    while True:
        batch = list(Customer.objects.filter(pk__gt=last_pk).order_by("pk")[:BACKFILL_BATCH_SIZE])
        if not batch:
            break
        for customer in batch:
            try:
                customer.normalized_phone = _normalize_phone(customer.phone)
                customer.normalized_whatsapp = _normalize_phone(customer.whatsapp)
                customer.normalized_domain = _normalize_domain(customer.website)
            except Exception:
                customer.normalized_phone = customer.normalized_phone or ""
                customer.normalized_whatsapp = customer.normalized_whatsapp or ""
                customer.normalized_domain = customer.normalized_domain or ""
        Customer.objects.bulk_update(
            batch,
            ["normalized_phone", "normalized_whatsapp", "normalized_domain"],
        )
        last_pk = batch[-1].pk


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0004_customer_normalized_match_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_normalized_match_fields, migrations.RunPython.noop),
    ]
