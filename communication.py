import csv
import os
import time
from datetime import datetime

import serial
import requests
import objc

from Foundation import NSObject, NSRunLoop, NSDate
import CoreLocation


SERIAL_PORT = "/dev/tty.usbmodem1101"
BAUD_RATE = 9600
CSV_FILE = "asset_log.csv"


# Create CSV file with headers if it doesn't exist
def ensure_csv_exists(filename: str) -> None:
    if not os.path.exists(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp",
                "UID",
                "Asset",
                "Status",
                "Latitude",
                "Longitude",
                "Approx_Address"
            ])


# Delegate class to handle macOS location updates
class LocationDelegate(NSObject):
    def init(self):
        self = objc.super(LocationDelegate, self).init()
        if self is None:
            return None
        self.location = None
        self.error = None
        return self

    def locationManager_didUpdateLocations_(self, manager, locations):
        if locations:
            self.location = locations[-1]

    def locationManager_didFailWithError_(self, manager, error):
        self.error = str(error)


# Convert coordinates into a readable address using OpenStreetMap API
def reverse_geocode(lat: float, lon: float) -> str:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2"},
            headers={"User-Agent": "rfid-logger/1.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("display_name", "Unknown")
    except requests.RequestException:
        return "Unknown"


# Get current Mac location (latitude, longitude, address)
def get_mac_location(timeout_seconds: int = 10) -> tuple[str, str, str]:
    manager = CoreLocation.CLLocationManager.alloc().init()
    delegate = LocationDelegate.alloc().init()
    manager.setDelegate_(delegate)

    if hasattr(manager, "requestWhenInUseAuthorization"):
        manager.requestWhenInUseAuthorization()

    manager.startUpdatingLocation()

    start = time.time()
    while time.time() - start < timeout_seconds:
        # Allow location updates to process
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.2)
        )

        if delegate.location is not None:
            loc = delegate.location.coordinate()
            lat = float(loc.latitude)
            lon = float(loc.longitude)
            manager.stopUpdatingLocation()
            address = reverse_geocode(lat, lon)
            return str(lat), str(lon), address

        if delegate.error is not None:
            manager.stopUpdatingLocation()
            return "", "", f"Location error: {delegate.error}"

    manager.stopUpdatingLocation()
    return "", "", "Location unavailable"


# Append a new scan record to CSV
def append_to_csv(
    filename: str,
    uid: str,
    asset: str,
    status: str,
    latitude: str,
    longitude: str,
    approx_address: str
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            uid,
            asset,
            status,
            latitude,
            longitude,
            approx_address
        ])


def main() -> None:
    ensure_csv_exists(CSV_FILE)

    print(f"Opening {SERIAL_PORT} at {BAUD_RATE} baud...")
    print(f"Logging scans to {CSV_FILE}")
    print("Getting Mac location access...")
    print("Waiting for RFID scans...\n")

    try:
        # Open serial connection to Arduino
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            time.sleep(2)  # allow Arduino to reset

            while True:
                raw_line = ser.readline().decode("utf-8", errors="ignore").strip()

                if not raw_line:
                    continue

                parts = raw_line.split(",")

                # Expect format: UID, Asset, Status
                if len(parts) != 3:
                    print(f"Ignored: {raw_line}")
                    continue

                uid, asset, status = [p.strip() for p in parts]

                # Get current location for each scan
                lat, lon, approx_address = get_mac_location()

                append_to_csv(
                    CSV_FILE,
                    uid,
                    asset,
                    status,
                    lat,
                    lon,
                    approx_address
                )

                # Print log to terminal
                print("Logged scan:")
                print(f"  UID: {uid}")
                print(f"  Asset: {asset}")
                print(f"  Status: {status}")
                print(f"  Location: {approx_address}")
                print(f"  Coordinates: {lat}, {lon}\n")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopped logger.")


if __name__ == "__main__":
    main()