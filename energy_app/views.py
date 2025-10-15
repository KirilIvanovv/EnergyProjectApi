from datetime import timezone
from django.shortcuts import render
from django.http import HttpResponse
from nordpool import elspot
from dateutil import tz
from django.utils import timezone
from datetime import datetime

def home(request):
    price_spot = elspot.Prices()

    AREA = "LV"

    try:
        data = price_spot.fetch(areas = [AREA])
    except Exception as e:
        return render(request, "home.html", {"error": str(e)})

    areas = data.get("areas", {})
    lv = areas.get(AREA) or {}
    values = lv.get("values", []) if lv else []

    valid_prices = []
    for x in values:
        if x.get("value") is not None:
            valid_prices.append(x)

    if not valid_prices:
        return render(request, "home.html", {"error": "No valid price data available."})
 
    min_item = min(valid_prices, key=lambda x: x["value"])
    max_item = max(valid_prices, key=lambda x: x["value"])

    riga_tz = tz.gettz("Europe/Riga")

    def fmt(dt):
        if dt is None:
            return None
        return dt.astimezone(riga_tz)
    
    now = timezone.now().astimezone(riga_tz)

    current_price = None
    for v in valid_prices:
        start = fmt(v.get("start"))
        end = fmt(v.get("end"))
        if start and end and start <= now < end:
            current_price = v.get("value")
            current_start = start
            current_end = end
            break

    context = {
        "min_price": min_item["value"],
        "min_start": fmt(min_item.get("start")),
        "min_end": fmt(min_item.get("end")),

        "max_price": max_item["value"],
        "max_start": fmt(max_item.get("start")),
        "max_end": fmt(max_item.get("end")),

        "current_price": current_price,
        "current_start": current_start if current_price else None,
        "current_end": current_end if current_price else None,

        "all_values": [
            {"start": fmt(v.get("start")), "end": fmt(v.get("end")), "price": v.get("value")}
            for v in valid_prices
        ],
        "currency": data.get("currency", "EUR"),
        "updated": data.get("updated"),
         "today_date": timezone.now().date(),
    }

    return render(request, "home.html", context)

