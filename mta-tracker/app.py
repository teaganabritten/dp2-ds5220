import io
import importlib
import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import boto3
import matplotlib
import matplotlib.pyplot as plt
import requests
from boto3.dynamodb.conditions import Attr


matplotlib.use("Agg")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MTA_API = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"
TABLE_NAME = os.environ["DYNAMO_TABLE"]
S3_BUCKET = os.environ["S3_BUCKET"]
AWS_REGION = os.environ["AWS_REGION"]
PLOT_KEY = os.environ.get("PLOT_KEY", "mta/status/latest.png")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)
gtfs_realtime_pb2 = importlib.import_module("google.transit.gtfs_realtime_pb2")


def fetch_mta_data():
    """Fetch and parse the real-time MTA feed."""
    try:
        response = requests.get(MTA_API, timeout=30)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        logger.info("Successfully fetched MTA realtime feed.")
        return feed
    except Exception as exc:
        logger.error("Error fetching MTA data: %s", exc)
        return None


def build_snapshot(feed):
    """Convert the realtime feed into a compact DynamoDB item."""
    route_counts = Counter()
    trip_update_count = 0
    vehicle_count = 0
    alert_count = 0

    for entity in feed.entity:
        if entity.HasField("trip_update"):
            trip_update_count += 1
            route_id = entity.trip_update.trip.route_id or "unknown"
            route_counts[route_id] += 1
        if entity.HasField("vehicle"):
            vehicle_count += 1
            route_id = entity.vehicle.trip.route_id or "unknown"
            route_counts[route_id] += 1
        if entity.HasField("alert"):
            alert_count += 1

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return {
        "id": timestamp,
        "timestamp": timestamp,
        "entity_count": len(feed.entity),
        "trip_update_count": trip_update_count,
        "vehicle_count": vehicle_count,
        "alert_count": alert_count,
        "route_counts": dict(route_counts.most_common(10)),
    }


def save_snapshot(snapshot):
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=snapshot)
    logger.info("Stored snapshot %s in DynamoDB.", snapshot["id"])


def load_recent_snapshots(hours=72):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_iso = cutoff.isoformat(timespec="seconds")
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan(
        FilterExpression=Attr("timestamp").gte(cutoff_iso),
    )
    items = response.get("Items", [])
    items.sort(key=lambda item: item["timestamp"])
    return items


def render_plot(snapshots):
    if not snapshots:
        logger.warning("No snapshots available to plot.")
        return None

    timestamps = [item["timestamp"] for item in snapshots]
    entity_counts = [item["entity_count"] for item in snapshots]
    trip_updates = [item["trip_update_count"] for item in snapshots]
    vehicles = [item["vehicle_count"] for item in snapshots]
    alerts = [item["alert_count"] for item in snapshots]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, entity_counts, label="Entities", linewidth=2)
    ax.plot(timestamps, trip_updates, label="Trip updates", linewidth=2)
    ax.plot(timestamps, vehicles, label="Vehicles", linewidth=2)
    ax.plot(timestamps, alerts, label="Alerts", linewidth=2)
    ax.set_title("MTA realtime feed history")
    ax.set_xlabel("Timestamp (UTC)")
    ax.set_ylabel("Count")
    ax.legend()
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def upload_plot(buffer):
    s3_client.upload_fileobj(
        buffer,
        S3_BUCKET,
        PLOT_KEY,
        ExtraArgs={"ContentType": "image/png"},
    )
    logger.info("Uploaded plot to s3://%s/%s", S3_BUCKET, PLOT_KEY)


def main():
    feed = fetch_mta_data()
    if feed is None:
        raise SystemExit(1)

    snapshot = build_snapshot(feed)
    save_snapshot(snapshot)

    snapshots = load_recent_snapshots()
    plot_buffer = render_plot(snapshots)
    if plot_buffer is None:
        raise SystemExit(1)

    upload_plot(plot_buffer)


if __name__ == "__main__":
    main()

