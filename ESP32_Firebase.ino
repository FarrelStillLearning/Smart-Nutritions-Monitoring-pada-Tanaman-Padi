#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>
#include <EEPROM.h>
#include "time.h"  

// FIREBASE & WIFI LIBRARIES 
#include <WiFi.h>
#include <Firebase_ESP_Client.h>

// Provide the token generation process info.
#include "addons/TokenHelper.h"
// Provide the RTDB payload printing info and other helper functions.
#include "addons/RTDBHelper.h"

// WIFI & FIREBASE CONFIG
#define WIFI_SSID "Redmi" 
#define WIFI_PASSWORD "servant0507"

// API Key & Database URL
#define API_KEY "AIzaSyDaLe6vUXp_cgestcYSDVuxQ2QVw1t4s_M"
#define DATABASE_URL "https://matkul-9f44d-default-rtdb.asia-southeast1.firebasedatabase.app/"

// KONFIGURASI WAKTU (NTP)
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 25200;  
const int   daylightOffset_sec = 0;

// Firebase objects
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;
bool signupOK = false;

// PIN CONFIGURATION 
// I2C untuk ADS1115
#define I2C_SDA 21
#define I2C_SCL 22

// pH Sensor (via ADS1115)
#define PH_ADC_CHANNEL 0    

// TDS Sensor
#define TDS_ADC_CHANNEL 1   

// DS18B20 Temperature
#define ONE_WIRE_BUS 4      

// Soil Moisture (via ADS1115)
#define SOIL_ADC_CHANNEL 2  

// DHT22
#define DHT_PIN 15          
#define DHT_TYPE DHT22

// Rainfall Sensor
#define RAIN_PIN 33         

// Output
#define LED_PIN 2           
#define BUZZER_PIN 5        

// SENSOR OBJECTS 
Adafruit_ADS1115 ads;  
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature DS18B20(&oneWire);
DHT dht(DHT_PIN, DHT_TYPE);

// KALIBRASI pH
// EEPROM addresses untuk menyimpan kalibrasi
#define EEPROM_SIZE 64
#define ADDR_PH_NEUTRAL_VOLTAGE 0
#define ADDR_PH_ACID_VOLTAGE 4
#define ADDR_CALIBRATED_FLAG 8

// Default kalibrasi values
float neutralVoltage = 2110.0;  // mV untuk pH 6.86 (2.110 V)
float acidVoltage = 2360.0;     // mV untuk pH 4.01 (2.360 V)

// Konstanta pH 
const float PH_NEUTRAL = 6.86;  
const float PH_ACID = 4.01;     

// GLOBAL VARIABLES 
float phValue = 7.0;
float tdsValue = 0.0;
float waterTemp = 25.0;
float airTemp = 25.0;
float humidity = 50.0;
int soilMoisture = 0;
int rainfallValue = 0;

// TDS THRESHOLD
#define TDS_LOW_THRESHOLD     450     
#define TDS_HIGH_THRESHOLD    2000    

// SOIL MOISTURE THRESHOLD 
#define SOIL_DRY_THRESHOLD     33
#define SOIL_WET_THRESHOLD     90

// Timing
unsigned long previousMillis = 0;
const long interval = 2000;  

// LED Blinking untuk alarm
unsigned long ledBlinkMillis = 0;
const long ledBlinkInterval = 15;  
bool ledState = false;

// FUNGSI WAKTU
String getTimestamp() {
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)){
    Serial.println("Gagal mengambil waktu");
    return "N/A";
  }
  
  char timeStringBuff[50];
  // Format: YYYY-MM-DD HH:MM:SS
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(timeStringBuff);
}

// SETUP 
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("╔════════════════════════════════════════╗");
  Serial.println("║      IoT Sensor Monitoring System      ║");
  Serial.println("╚════════════════════════════════════════╝");
  
  // KONEKSI WIFI
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(300);
  }
  Serial.println();
  Serial.print("Connected with IP: ");
  Serial.println(WiFi.localIP());
  Serial.println();

  // SETUP WAKTU (NTP)
  Serial.println("Mengambil waktu dari server NTP...");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  struct tm timeinfo;
  if(getLocalTime(&timeinfo)){
     Serial.println("Waktu tersinkronisasi: " + getTimestamp());
  } else {
     Serial.println("Gagal sinkronisasi waktu, akan mencoba lagi di background.");
  }

  // KONFIGURASI FIREBASE
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;

  // Sign up anonim
  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("[FIREBASE] Sign up OK");
    signupOK = true;
  } else {
    Serial.printf("[FIREBASE] Sign up Error: %s\n", config.signer.signupError.message.c_str());
  }

  // Set callback status
  config.token_status_callback = tokenStatusCallback; 
  
  // Inisialisasi Firebase
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  // Initialize I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  
  // Initialize ADS1115
  if (!ads.begin()) {
    Serial.println("[ERROR] ADS1115 tidak ditemukan!");
    while (1);
  }
  ads.setGain(GAIN_ONE);  // ±4.096V range
  Serial.println("[OK] ADS1115 siap (GAIN_ONE: ±4.096V)");
  
  // Initialize EEPROM
  EEPROM.begin(EEPROM_SIZE);
  loadCalibration();
  
  // Initialize sensors
  DS18B20.begin();
  dht.begin();
  
  // Initialize output pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Test LED dan Buzzer
  digitalWrite(LED_PIN, HIGH);
  tone(BUZZER_PIN, 1000, 200);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("\n[INIT] Semua sensor siap!");
  Serial.println("\n[KALIBRASI pH - SUDAH DI-SET!]");
  Serial.println("Kalibrasi saat ini: pH 6.86 = 2.110V, pH 4.01 = 2.360V");
  Serial.println("\nPerintah:");
  Serial.println("  ph7   - Kalibrasi ulang buffer pH 6.86");
  Serial.println("  ph4   - Kalibrasi ulang buffer pH 4.01");
  Serial.println("  show  - Tampilkan kalibrasi saat ini");
  Serial.println("  reset - Reset ke kalibrasi user (2.110V & 2.360V)");
  Serial.println("\n" + String('=') + String('=') + String('=') + String('=') + String('='));
  Serial.println();
}

// MAIN LOOP
void loop() {
  handleSerialCommands();
  
  // Baca sensor dengan interval
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    // Baca semua sensor
    readAllSensors();
    
    // Tampilkan ke Serial Monitor
    displaySensorData();
    
    // Cek kondisi alarm
    checkAlarmConditions();

    // Kirim ke Firebase
    sendDataToFirebase();
  }
}

// FUNGSI KIRIM KE FIREBASE
void sendDataToFirebase() {
  if (Firebase.ready() && signupOK) {
    
    // Ambil waktu saat ini
    String currentTime = getTimestamp();

    // Kirim pH & Timestamp pH
    Firebase.RTDB.setFloat(&fbdo, "/Monitoring/pH", phValue);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/pH_Time", currentTime);
    
    // Kirim TDS & Timestamp TDS
    Firebase.RTDB.setFloat(&fbdo, "/Monitoring/TDS", tdsValue);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/TDS_Time", currentTime);
    
    // Kirim Suhu Air & Timestamp
    Firebase.RTDB.setFloat(&fbdo, "/Monitoring/WaterTemp", waterTemp);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/WaterTemp_Time", currentTime);
    
    // Kirim Suhu Udara & Timestamp
    Firebase.RTDB.setFloat(&fbdo, "/Monitoring/AirTemp", airTemp);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/AirTemp_Time", currentTime);
    
    // Kirim Kelembaban & Timestamp
    Firebase.RTDB.setFloat(&fbdo, "/Monitoring/Humidity", humidity);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/Humidity_Time", currentTime);
    
    // Kirim Soil Moisture & Timestamp
    Firebase.RTDB.setInt(&fbdo, "/Monitoring/SoilMoisture", soilMoisture);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/SoilMoisture_Time", currentTime);
    
    // Kirim Rainfall & Timestamp
    Firebase.RTDB.setInt(&fbdo, "/Monitoring/Rainfall", rainfallValue);
    Firebase.RTDB.setString(&fbdo, "/Monitoring/Rainfall_Time", currentTime);

    // Timestamp Global 
    Firebase.RTDB.setString(&fbdo, "/Monitoring/timestamp", currentTime);

    // Cek apakah ada error saat pengiriman terakhir
    if (fbdo.errorReason() != "") {
       Serial.print("[FIREBASE ERROR] ");
       Serial.println(fbdo.errorReason());
    } else {
       Serial.print("[FIREBASE] Data & Timestamp terkirim: ");
       Serial.println(currentTime);
    }
  }
}

// FUNGSI BACA SENSOR
void readAllSensors() {
  // 1. Baca pH
  phValue = readPH();
  
  // 2. Baca TDS
  tdsValue = readTDS();
  
  // 3. Baca DS18B20 (suhu air)
  waterTemp = readDS18B20();
  
  // 4. Baca DHT22 (suhu & kelembaban udara)
  readDHT22();
  
  // 5. Baca Soil Moisture
  soilMoisture = readSoilMoisture();
  
  // 6. Baca Rainfall
  rainfallValue = readRainfall();
}

// pH SENSOR
float readPH() {
  int32_t rawSum = 0;
  
  // Rata-rata 10 pembacaan dari ADS1115
  for(int i = 0; i < 10; i++) {
    rawSum += ads.readADC_SingleEnded(PH_ADC_CHANNEL);
    delay(10);
  }
  int16_t rawAvg = rawSum / 10;
  
  // Konversi ke voltage (ADS1115 GAIN_ONE: 1 bit = 0.125 mV)
  float voltage = rawAvg * 0.125;  // dalam mV
  
  // Hitung pH berdasarkan kalibrasi
  float pH = calculatePH(voltage);
  
  return pH;
}

float calculatePH(float voltage) {
  // Linear interpolation antara dua titik kalibrasi
  // pH 7: neutralVoltage
  // pH 4: acidVoltage

  float slope = (PH_ACID - PH_NEUTRAL) / (acidVoltage - neutralVoltage);
  float ph = PH_NEUTRAL + slope * (voltage - neutralVoltage);
  
  return ph;
}

// TDS SENSOR (ADS1115 A1)
float readTDS() {
  int32_t rawSum = 0;

  // Rata-rata 10 pembacaan dari ADS1115 A1
  for (int i = 0; i < 10; i++) {
    rawSum += ads.readADC_SingleEnded(TDS_ADC_CHANNEL);
    delay(10);
  }

  int16_t rawAvg = rawSum / 10;

  // Konversi ke tegangan
  // GAIN_ONE → 1 bit = 0.125 mV
  float voltage_mV = rawAvg * 0.125;
  float voltage = voltage_mV / 1000.0; // Volt

  // Kompensasi suhu
  float compensationCoefficient = 1.0 + 0.02 * (waterTemp - 25.0);
  float compensationVoltage = voltage / compensationCoefficient;

  // Konversi ke TDS (ppm)
  float tds = (133.42 * compensationVoltage * compensationVoltage * compensationVoltage
              -255.86 * compensationVoltage * compensationVoltage
              +857.39 * compensationVoltage) * 0.5;

  if (tds < 0) tds = 0; // safety clamp

  return tds;
}

// DS18B20 TEMPERATURE
float readDS18B20() {
  DS18B20.requestTemperatures();
  float temp = DS18B20.getTempCByIndex(0);
  
  // Cek jika pembacaan valid
  if(temp == DEVICE_DISCONNECTED_C || temp == 85.0) {
    return waterTemp;  // Return nilai sebelumnya jika error
  }
  
  return temp;
}

// DHT22 
void readDHT22() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  // Cek jika pembacaan valid
  if (!isnan(h) && !isnan(t)) {
    humidity = h;
    airTemp = t;
  }
}

// SOIL MOISTURE
int readSoilMoisture() {
  int32_t rawSum = 0;
  
  // Rata-rata 5 pembacaan dari ADS1115 channel A2
  for(int i = 0; i < 5; i++) {
    rawSum += ads.readADC_SingleEnded(SOIL_ADC_CHANNEL);
    delay(10);
  }
  int16_t rawAvg = rawSum / 5;
  
  // Konversi ke voltage (ADS1115 GAIN_ONE: 1 bit = 0.125 mV)
  float voltage = rawAvg * 0.125;  // dalam mV
  
  // Konversi ke persentase (Capacitive sensor V2.00: basah=tinggi, kering=rendah)
  int moisture = map(voltage, 1000, 3000, 100, 0); 
  moisture = constrain(moisture, 0, 100);
  
  return moisture;
}

// RAINFALL SENSOR
int readRainfall() {
  int analogValue = analogRead(RAIN_PIN);
  
  // Konversi ke persentase (kering=tinggi, basah=rendah)
  int rainfall = map(analogValue, 4095, 0, 0, 100);
  rainfall = constrain(rainfall, 0, 100);
  
  return rainfall;
}

// DISPLAY DATA
void displaySensorData() {
  Serial.println("\n===== SENSOR READINGS =====");
  
  // pH
  Serial.print("║ pH Value        : ");
  Serial.print(phValue, 2);
  printpHStatus(phValue);
  
 // TDS
  Serial.print("║ TDS (ppm)       : ");
  Serial.print(tdsValue, 0);
  Serial.print(" ppm");
  printTDSStatus(tdsValue);

  // Temperature Water
  Serial.print("║ Water Temp      : ");
  Serial.print(waterTemp, 1);
  Serial.println(" °C");
  
  // Air Temperature
  Serial.print("║ Air Temp        : ");
  Serial.print(airTemp, 1);
  Serial.println(" °C");
  
  // Humidity
  Serial.print("║ Humidity        : ");
  Serial.print(humidity, 1);
  Serial.println(" %");
  
  // Soil Moisture
  Serial.print("║ Soil Moisture   : ");
  Serial.print(soilMoisture);
  Serial.print(" %");
  printSoilStatus(soilMoisture);
  
  // Rainfall
  Serial.print("║ Rainfall        : ");
  Serial.print(rainfallValue);
  Serial.print(" %");
  printRainStatus(rainfallValue);
  
  Serial.println("==========");
}

void printpHStatus(float ph) {
  if(ph < 6.5) {
    Serial.println("  [ASAM]");
  } else if(ph > 7.5) {
    Serial.println("  [BASA]");
  } else {
    Serial.println("  [NETRAL]");
  }
}

void printSoilStatus(int moisture) {
  if (moisture < SOIL_DRY_THRESHOLD) {
    Serial.println("  [KERING]");
  } 
  else if (moisture <= SOIL_WET_THRESHOLD) {
    Serial.println("  [LEMBAB / MACAK-MACAK]");
  } 
  else {
    Serial.println("  [BASAH / TERGENANG]");
  }
}


void printRainStatus(int rain) {
  if(rain < 20) {
    Serial.println("  [TIDAK HUJAN]");
  } else if(rain < 60) {
    Serial.println("  [GERIMIS]");
  } else {
    Serial.println("  [HUJAN DERAS]");
  }
}

void printTDSStatus(float tds) {
  if (tds < TDS_LOW_THRESHOLD) {
    Serial.println("  [KURANG / STARVING]");
  } 
  else if (tds <= TDS_HIGH_THRESHOLD) {
    Serial.println("  [IDEAL / OPTIMAL]");
  } 
  else {
    Serial.println("  [BERLEBIH / TOXIC]");
  }
}


// ALARM CONDITIONS
void checkAlarmConditions() {
  bool alarm = false;
  
// Cek TDS berlebih (toxic)
if (tdsValue > TDS_HIGH_THRESHOLD) {
  alarm = true;
  Serial.println("[ALARM] TDS terlalu tinggi (TOXIC)!");
}

  // Cek kondisi pH ekstrim
  if(phValue < 5.0 || phValue > 9.0) {
    alarm = true;
    Serial.println("[ALARM] pH di luar batas normal!");
  }
  
  // Cek suhu air terlalu tinggi
  if(waterTemp > 35.0) {
    alarm = true;
    Serial.println("[ALARM] Suhu air terlalu tinggi!");
  }
  
 // Cek tanah terlalu kering
if (soilMoisture < SOIL_DRY_THRESHOLD) {
  alarm = true;
  Serial.println("[ALARM] Tanah terlalu kering!");
}

// Cek tanah tergenang
if (soilMoisture > SOIL_WET_THRESHOLD) {
  alarm = true;
  Serial.println("[ALARM] Tanah tergenang!");
}
  
  // Logic LED dan Buzzer
  if(alarm) {
    // ALARM: LED kedip-kedip + Buzzer ON
    unsigned long currentMillis = millis();
    if(currentMillis - ledBlinkMillis >= ledBlinkInterval) {
      ledBlinkMillis = currentMillis;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
    }
    tone(BUZZER_PIN, 2000);  // Buzzer terus bunyi
  } else {
    // NORMAL: LED ON steady + Buzzer OFF
    digitalWrite(LED_PIN, HIGH);
    noTone(BUZZER_PIN);  // Matikan buzzer
  }
}

// KALIBRASI pH 
void handleSerialCommands() {
  if(Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();
    
    if(command == "ph7" || command == "ph6.86") {
      calibratePH7();
    }
    else if(command == "ph4" || command == "ph4.01") {
      calibratePH4();
    }
    else if(command == "show") {
      showCalibration();
    }
    else if(command == "reset") {
      resetCalibration();
    }
    else if(command != "") {
      Serial.println("[ERROR] Perintah tidak dikenal!");
      Serial.println("Gunakan: ph7, ph4, show, reset");
    }
  }
}

void calibratePH7() {
  Serial.println("\n[KALIBRASI] Kalibrasi pH 6.86 (atau 7)...");
  Serial.println("Pastikan probe dalam buffer pH 6.86 (atau 7)");
  
  delay(1000);
  
  // Baca voltage saat ini dari ADS1115
  int32_t rawSum = 0;
  for(int i = 0; i < 20; i++) {
    rawSum += ads.readADC_SingleEnded(PH_ADC_CHANNEL);
    delay(50);
  }
  int16_t rawAvg = rawSum / 20;
  
  neutralVoltage = rawAvg * 0.125;  // Konversi ke mV
  
  Serial.print("✓ pH 6.86 Voltage: ");
  Serial.print(neutralVoltage, 2);
  Serial.print(" mV (");
  Serial.print(neutralVoltage / 1000.0, 3);
  Serial.println(" V)");
  
  saveCalibration();
  Serial.println("Kalibrasi pH 6.86 tersimpan!");
  
  // Beep konfirmasi
  tone(BUZZER_PIN, 1500, 100);
  delay(150);
  tone(BUZZER_PIN, 1500, 100);
}

void calibratePH4() {
  Serial.println("\n[KALIBRASI] Kalibrasi pH 4.01 (atau 4)...");
  Serial.println("Pastikan probe dalam buffer pH 4.01 (atau 4)");
  
  delay(1000);
  
  // Baca voltage saat ini dari ADS1115
  int32_t rawSum = 0;
  for(int i = 0; i < 20; i++) {
    rawSum += ads.readADC_SingleEnded(PH_ADC_CHANNEL);
    delay(50);
  }
  int16_t rawAvg = rawSum / 20;
  
  acidVoltage = rawAvg * 0.125;  // Konversi ke mV
  
  Serial.print("✓ pH 4.01 Voltage: ");
  Serial.print(acidVoltage, 2);
  Serial.print(" mV (");
  Serial.print(acidVoltage / 1000.0, 3);
  Serial.println(" V)");
  
  saveCalibration();
  Serial.println("Kalibrasi pH 4.01 tersimpan!");
  
  // Beep konfirmasi
  tone(BUZZER_PIN, 1500, 100);
  delay(150);
  tone(BUZZER_PIN, 1500, 100);
}

void showCalibration() {
  Serial.println("\n===== KALIBRASI pH =====");
  Serial.print("║ pH 6.86 (Neutral) : ");
  Serial.print(neutralVoltage / 1000.0, 3);
  Serial.print(" V (");
  Serial.print(neutralVoltage, 1);
  Serial.println(" mV)");
  
  Serial.print("║ pH 4.01 (Acid)    : ");
  Serial.print(acidVoltage / 1000.0, 3);
  Serial.print(" V (");
  Serial.print(acidVoltage, 1);
  Serial.println(" mV)");
  
  // Hitung slope
  float slope = (PH_ACID - PH_NEUTRAL) / (acidVoltage - neutralVoltage);
  Serial.print("║ Slope             : ");
  Serial.println(slope, 4);
  
  Serial.println("==========\n");
}

void resetCalibration() {
  Serial.println("\n[RESET] Mengembalikan kalibrasi ke nilai user...");
  
  // Nilai kalibrasi yang sudah terbukti akurat
  neutralVoltage = 2110.0;  // 2.110 V untuk pH 6.86
  acidVoltage = 2360.0;     // 2.360 V untuk pH 4.01
  
  saveCalibration();
  
  Serial.println("✓ Kalibrasi direset ke nilai user (V_PH6.86=2.110V, V_PH4.01=2.360V)!");
  tone(BUZZER_PIN, 1000, 200);
}

void saveCalibration() {
  // Simpan ke EEPROM
  EEPROM.put(ADDR_PH_NEUTRAL_VOLTAGE, neutralVoltage);
  EEPROM.put(ADDR_PH_ACID_VOLTAGE, acidVoltage);
  EEPROM.write(ADDR_CALIBRATED_FLAG, 0xAA);  // Flag bahwa sudah dikalibrasi
  EEPROM.commit();
}

void loadCalibration() {
  byte flag = EEPROM.read(ADDR_CALIBRATED_FLAG);
  
  if(flag == 0xAA) {
    EEPROM.get(ADDR_PH_NEUTRAL_VOLTAGE, neutralVoltage);
    EEPROM.get(ADDR_PH_ACID_VOLTAGE, acidVoltage);
    Serial.println("[EEPROM] Kalibrasi dimuat dari memory");
  } else {
    Serial.println("[EEPROM] Menggunakan kalibrasi default");
  }
}