from flask import Flask, jsonify # type: ignore
from nordpool import elspot
from dateutil import tz
from datetime import datetime, timedelta
import json
import os
import logging

try:
    from apscheduler.schedulers.background import BackgroundScheduler # type: ignore
    APSCHEDULER_AVAILABLE = True
except Exception:
    APSCHEDULER_AVAILABLE = False

app = Flask(__name__)

DATA_FILE = os.environ.get("FETCHER_DATA_FILE", "/data/data.json")
RIGA_TZ = tz.gettz("Europe/Riga")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fetcher")

def normalize_nordpool_data(raw_data, area="LV"):
    if not raw_data or "areas" not in raw_data:
        return None

    area_data = raw_data["areas"].get(area)
    if not area_data or "values" not in area_data:
        return None

    values = []
    for v in area_data["values"]:
        if not v.get("value") or not v.get("start"):
            continue
        start_local = v["start"].astimezone(RIGA_TZ)
        end_local = start_local + timedelta(hours=1)

        values.append({
            "start": start_local.isoformat(),
            "end": end_local.isoformat(),
            "price": float(v["value"])
        })

    result = {
        "currency": raw_data.get("currency", "EUR"),
        "area": area,
        "fetched_at": datetime.now(RIGA_TZ).isoformat(),
        "values": values
    }
    return result

@app.route('/datafetch', methods=['GET'])
def fetch_endpoint():
    try:
        logger.info("Starting fetch from Nord Pool...")
        prices = elspot.Prices()
        raw = prices.fetch(areas=["LV"])
        normalized = normalize_nordpool_data(raw, area="LV")
        if not normalized:
            logger.warning("No valid data returned from Nord Pool.")
            return jsonify({"status": "error", "message": "No data returned"}), 500

        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        logger.info("Data saved to %s", DATA_FILE)
        return jsonify({"status": "ok", "file": DATA_FILE})
    except Exception as e:
        logger.exception("Fetch failed")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/prices", methods=["GET"])
def prices_endpoint():
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "No data yet"}), 404
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        logger.exception("Failed to read data file")
        return jsonify({"error": str(e)}), 500

def scheduled_fetch():
    try:
        logger.info("Scheduled fetch started")
        prices = elspot.Prices()
        raw = prices.fetch(areas=["LV"])
        normalized = normalize_nordpool_data(raw, area="LV")
        if not normalized:
            logger.warning("Scheduled fetch returned no data")
            return
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        logger.info("Scheduled fetch saved data")
    except Exception:
        logger.exception("Scheduled fetch error")

if __name__ == "__main__":
    if APSCHEDULER_AVAILABLE:
        scheduler = BackgroundScheduler()
        scheduler.add_job(scheduled_fetch, "interval", minutes=int(os.environ.get("FETCH_INTERVAL_MIN", 60)))
        scheduler.start()
        logger.info("Background scheduler started (interval minutes=%s)", os.environ.get("FETCH_INTERVAL_MIN", 60))
    else:
        logger.info("APScheduler not available; scheduled fetch disabled")

    scheduled_fetch()
    app.run(host="0.0.0.0", port=int(os.environ.get("FETCHER_PORT", 5000)))
