#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

#define RED_PIN 6
#define GREEN_PIN 5
#define BLUE_PIN 3

MFRC522 mfrc522(SS_PIN, RST_PIN);

unsigned long lastScanTime = 0;
const unsigned long IDLE_DELAY = 20000; // 20 seconds before idle glow
bool idleGlowOn = false;

// Convert UID bytes into readable string format (e.g. "43:74:B5:FD")
String uidToString(MFRC522::Uid *uid) {
  String result = "";
  for (byte i = 0; i < uid->size; i++) {
    if (uid->uidByte[i] < 0x10) result += "0";
    result += String(uid->uidByte[i], HEX);
    if (i < uid->size - 1) result += ":";
  }
  result.toUpperCase();
  return result;
}

// Set RGB LED color (common cathode)
void setColor(int redValue, int greenValue, int blueValue) {
  analogWrite(RED_PIN, redValue);
  analogWrite(GREEN_PIN, greenValue);
  analogWrite(BLUE_PIN, blueValue);
}

void turnOffRGB() {
  setColor(0, 0, 0);
}

// Green flash for valid scan
void showSuccess() {
  setColor(0, 255, 0);
  delay(700);
  turnOffRGB();
}

// Red flash for invalid scan
void showError() {
  setColor(255, 0, 0);
  delay(700);
  turnOffRGB();
}

// Orange glow when idle
void showIdleGlow() {
  setColor(255, 15, 0);
}

// Map UID to asset name
String getAssetName(String uid) {
  if (uid == "43:74:B5:FD") {
    return "Defibrillator";
  }
  else if (uid == "C3:AE:ED:F6") {
    return "Infusion Pump";
  }
  else {
    return "Invalid Card Entry";
  }
}

// Check if scanned card is valid
bool isValidCard(String uid) {
  return (uid == "43:74:B5:FD" || uid == "C3:AE:ED:F6");
}

void setup() {
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);

  turnOffRGB();

  Serial.begin(9600);
  delay(1000);

  SPI.begin();
  mfrc522.PCD_Init(); // Initialize RFID reader

  Serial.println("RFID Medical Supply Tracking System");
  Serial.println("Scan an RFID tag...");

  lastScanTime = millis();
}

void loop() {
  // Activate idle glow if no scans for set duration
  if (!idleGlowOn && millis() - lastScanTime >= IDLE_DELAY) {
    showIdleGlow();
    idleGlowOn = true;
  }

  // Wait for RFID scan
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  String uid = uidToString(&mfrc522.uid);
  String item = getAssetName(uid);
  bool valid = isValidCard(uid);

  turnOffRGB();
  idleGlowOn = false;

  // Send scan data to Python (UID, item name, validity)
  Serial.print(uid);
  Serial.print(",");
  Serial.print(item);
  Serial.print(",");
  Serial.println(valid ? "VALID" : "INVALID");

  // Visual feedback
  if (valid) {
    showSuccess();
  } else {
    showError();
  }

  lastScanTime = millis();

  // Stop reading current card
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(500);
}