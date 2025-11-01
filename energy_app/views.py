import os
import requests
from datetime import datetime, timedelta
from dateutil import tz
from django.shortcuts import render

RIGA_TZ = tz.gettz("Europe/Riga")

def home(request):
    fetcher_url = os.getenv("FETCHER_URL", "http://fetcher_service:5000")
    try:
        resp = requests.get(f"{fetcher_url}/prices", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return render(request, "home.html", {"error": f"{e}"})

    if not data or "values" not in data:
        return render(request, "home.html", {"error": "No data available from fetcher"})

    all_values = []
    for v in data["values"]:
        try:
            start = datetime.fromisoformat(v["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(v["end"].replace("Z", "+00:00"))
            price = float(v["price"])
        except Exception:
            continue
        all_values.append({"start": start, "end": end, "price": price})

    all_values.sort(key=lambda x: x["start"])

    now = datetime.now(RIGA_TZ)
    tomorrow = now.date() + timedelta(days=1)
    tomorrow_values = [v for v in all_values if v["start"].date() == tomorrow]

        
    avg_price = round(sum(v["price"] for v in tomorrow_values) / len(tomorrow_values), 2) if tomorrow_values else None

    current_price = 0  

    context = {
        "currency": data.get("currency", "EUR"),
        "all_values": tomorrow_values,
        "min_price": min(tomorrow_values, key=lambda x: x["price"]) if tomorrow_values else None,
        "max_price": max(tomorrow_values, key=lambda x: x["price"]) if tomorrow_values else None,
        "current_price": current_price,
        "avg_price": avg_price,
        "current_time": now,
    }

    return render(request, "home.html", context)

def debug_prices(request):
    return render(request, "home.html", {"all_values": [], "current_price": 0})
