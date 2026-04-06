import csv
import os
import time
from datetime import datetime
import serial

# SERIAL PORT
SERIAL_PORT = "/dev/tty.usbmodem1101"
BAUD_RATE = 9600

CSV_FILE = "asset_log.csv"

# ✅ HARDCODED LOCATION
LOCATION = "Amit Chakma Engineering Building Medway, 1151 Richmond St, London, ON N6A 3K7"


def ensure_csv_exists(filename):
    if not os.path.exists(filename):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp",
                "UID",
                "Asset",
                "Status",
                "Location"
            ])


def append_to_csv(uid, asset, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            uid,
            asset,
            status,
            LOCATION
        ])


def main():
    ensure_csv_exists(CSV_FILE)

    print(f"Opening {SERIAL_PORT}...")
    print("Waiting for scans...\n")

    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            time.sleep(2)

            while True:
                raw_line = ser.readline().decode("utf-8", errors="ignore").strip()

                if not raw_line:
                    continue

                parts = raw_line.split(",")

                if len(parts) != 3:
                    print(f"Ignored: {raw_line}")
                    continue

                uid, asset, status = [p.strip() for p in parts]

                append_to_csv(uid, asset, status)

                print("Logged scan:")
                print(f"  UID: {uid}")
                print(f"  Asset: {asset}")
                print(f"  Status: {status}")
                print(f"  Location: {LOCATION}\n")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopped logger.")


if __name__ == "__main__":
    main()