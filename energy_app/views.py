from django.shortcuts import render
from nordpool import elspot
from datetime import datetime, timedelta
from dateutil import tz

def home(request):
    AREA = "LV"
    riga_tz = tz.gettz("Europe/Riga")

    try:
        prices = elspot.Prices()
        data = prices.fetch(areas=[AREA])
    except Exception as e:
        return render(request, "home.html", {"error": f" {e}"})

    if not data or "areas" not in data:
        return render(request, "home.html", {"error": "No data available"})

    lv_data = data["areas"].get(AREA)
    if not lv_data or "values" not in lv_data:
        return render(request, "home.html", {"error": "No price data for the specified area"})

    all_values = []
    for v in lv_data["values"]:
        if not v["value"] or not v["start"]:
            continue
        start = v["start"].astimezone(riga_tz)
        end = start + timedelta(hours=1)
        all_values.append({"start": start, "end": end, "price": v["value"]})

    if not all_values:
        return render(request, "home.html", {"error": "No valid price data available"})

    now = datetime.now(riga_tz)
    current_price = None
    for v in all_values:
        if v["start"] <= now < v["end"]:
            current_price = v["price"]
            break

    min_price = min(all_values, key=lambda x: x["price"])
    max_price = max(all_values, key=lambda x: x["price"])

    context = {
        "currency": data.get("currency", "EUR"),
        "all_values": all_values,
        "min_price": min_price,
        "max_price": max_price,
        "current_price": current_price,
        "current_time": now,
    }

    return render(request, "home.html", context)
