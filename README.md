# SmartFarm Expert System - IoT Nutrition Monitoring

Sistem monitoring nutrisi tanah berbasis IoT dengan integrasi **AI (Naive Bayes)**, **Fuzzy Logic (Mamdani)**, dan **Expert System (Forward Chaining)** untuk tanaman padi.

## Fitur Utama

- **ML Classification**: Model Naive Bayes untuk klasifikasi kesehatan tanah (Sehat/Kurang Hara/Tanah Masam/Kering)
- **Fuzzy Logic**: Sistem Mamdani untuk rekomendasi irigasi, pupuk, dan pestisida
- **Expert System**: Forward Chaining dengan 54 rules untuk diagnosis lahan
- **Real-time Monitoring**: Auto-refresh data dari Firebase (ESP32)
- **Grafik Interaktif**: Visualisasi data sensor real-time
- **Modern UI**: Dark gradient theme dengan card animations
- **Device Status**: Online/Offline detection berdasarkan perubahan sensor
- **Firebase Integration**: Realtime Database untuk sinkronisasi data IoT

## Teknologi yang Digunakan

### 1. **ML - Naive Bayes Classifier**
- Model: `model_naivebayes.pkl`
- Scaler: `scaler.pkl`
- Input: pH, Suhu Udara, Kelembaban Tanah, TDS
- Output: Sehat, Kurang Hara, Tanah Masam, Kering

### 2. **Fuzzy Logic - Mamdani**
- **Variabel Input**: TDS, pH, Kelembaban, Curah Hujan
- **Variabel Output**: 
  - Irigasi (ml/hari)
  - Pupuk (%)
  - Pestisida (%)
- **Membership Functions**: Triangular & Trapezoidal
- **Defuzzification**: Centroid Method

### 3. **Expert System - Forward Chaining**
- **54 Rules** dari knowledge_base.json
- **Parameter**: pH (masam/netral/basa), TDS (kurang/ideal/berlebih), Kelembaban (kering/lembab/basah), Curah Hujan (cerah/hujan)
- **Certainty Factor (CF)**: Confidence level dari pakar yaitu petani
- **Output**: Rekomendasi pupuk, air, pestisida, status, action steps

## Instalasi & Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd basecodeiot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Atau menggunakan virtual environment:**

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Setup Firebase Realtime Database

1. Buat project di [Firebase Console](https://console.firebase.google.com/)
2. Aktifkan **Realtime Database**
3. Pergi ke **Project Settings → Service Accounts**
4. Klik **Generate New Private Key**
5. Download file JSON dan rename menjadi `firebase_credentials.json`
6. Letakkan di root folder proyek
7. Update `databaseURL` di app.py jika berbeda

**Struktur Database Firebase:**

```json
Streamlit

```bash
streamlit run app.py
```

## Dashboard Features

### **Modern Dark UI**
- Dark gradient theme (Blue to Slate)
- Glassmorphism effect cards
- Hover animations
- Color-coded status indicators

### **ML Prediction Card**
- Real-time status kesehatan tanah
- Model: Naive Bayes Classifier
- Input features ditampilkan secara live

### File & Folder Structure

```
basecodeiot/
├── app.py                    # Main Streamlit application
├── knowledge_base.json       # 54 Expert System rules
├── master_data.json          # Sensor threshold definitions
├── model_naivebayes.pkl      # Trained ML model
├── scaler.pkl                # Feature scaler for ML
├── firebase_credentials.json # Firebase service account
├── requirements.txt          # Python dependencies
├── run.bat                   # Windows batch script
├── ESP32_Firebase.ino        # ESP32 Arduino code
├── IoT_Sensor_Monitor.ino    # Alternative ESP32 code
├── .gitignore                # Git ignore file
├── README.md                 # Documentation (this file)
└── __pycache__/              # Python cache
```

## Sensor Hardware

### Required Components:
- **ESP32** (WiFi enabled microcontroller)
- **pH Sensor Module** (pH Sensor)
- **TDS Sensor** (Total Dissolved Solids)
- **Soil Moisture Sensor** (Capacitive)
- **DHT22** (Suhu & Kelembaban Udara)
- **DS18B20** (Suhu Air - Waterproof)
- **Rain Sensor Module**
- Power supply 5V

```css
Background: linear-gradient(135deg, #0c4a6e, #1e293b, #1e293b)
Primary: #60a5fa (Light Blue)
Success: #4ade80 (Green)
Warning: #fbbf24 (Yellow)
Danger: #f87171 (Red)
Purple: #d8b4fe (ML Card)
Text: #e2e8f0 (Light Gray)
```
- Auto-update setiap refresh

### **Fuzzy Logic Visualization**
- Membership functions (input & output)
- Defuzzification centroid
- Hasil fuzzy untuk irigasi, pupuk, pestisida

### **Expert System Diagnosis**
- Forward chaining rule matching
- 54 rules dari knowledge_base
- Certainty Factor (CF) calculation
- Status keamanan lahan
- Rekomendasi detail:
  - Air (irigasi/drainase)
  - Pupuk (jenis & jumlah)
  - Pestisida (jenis)
  - Action steps (langkah-langkah tindakan)

### **Sidebar Controls**
- Device status (Online/Offline)
- Firebase connection status
- ML model status
- Auto-refresh toggle
- Refresh interval slider (2-10 detik)
Aplikasi akan terbuka di browser: `http://localhost:****`

## Fitur UI

### 1. **Elevated Cards**
- Card dengan shadow effect yang menonjol
- Hover animation (naik sedikit saat di-hover)
- Color-coded berdasarkan status (hijau/merah/orange)

### 2. **Progress Bars**
- Visualisasi nilai sensor dalam bentuk bar
- Gradient colors sesuai kondisi
- Threshold indicators

### 3. **Interactive Charts**
- Bar charts untuk parameter utama
- Gauge chart untuk confidence factor
- Real-time updates

### 4. **Auto Refresh**
- Configurable interval (5-60 detik)
- Toggle on/off dari sidebar

## Konfigurasi

### Sidebar Settings:
- Auto Refresh (on/off)
- Refresh Interval (2-10 detik)

```
┌─────────────┐      WiFi       ┌──────────────┐
│   ESP32     │ ──────────────> │   Firebase   │
│  + Sensors  │                 │   Realtime   │
└─────────────┘                 │   Database   │
                                └──────────────┘
                                       │
                                       │ Real-time Sync
                                       ▼
                                ┌──────────────┐
                                │  Streamlit   │
                                │  Dashboard   │
                                └──────────────┘

  # Example Rule from Knowledge Base:

```json
{
  "id": "R27",
  "description": "Netral, Lembab, TDS Ideal, Cerah",
  "conditions": {
    "ph": "netral",
    "tds": "ideal",
    "kelembaban": "lembab",
    "curah_hujan": "cerah"
  },
  "results": {
    "pupuk_q": "Tidak perlu pupuk (Kondisi Ideal)",
    "air_r": "Tidak perlu irigasi",
    "pestisida_s": "Tidak perlu pestisida",
    "status_t": "SANGAT AMAN (Kondisi Perfect)",
    "action_steps": [
      "Pertahankan kondisi ini",
      "Cek hama rutin"
    ],
    "cf": 1.0
  }
}
```

**Certainty Factor Interpretation:**
- Sangat Yakin (CF 0.8 - 1.0)
- Yakin (CF 0.6 - 0.8)
- Mungkin Bisa (CF 0.4 - 0.6)
- Kurang Yakin/Ragu (CF 0.2 - 0.4)
- Tidak Yakin/Salah (CF < 0.2)

## Fuzzy Membership Functions

### Input Variables:

**TDS (ppm):**
- Kurang: 0-500 ppm
- Ideal: 400-2100 ppm
- Berlebih: 1900-3000 ppm

**pH:**
- Masam: < 7.0
- Netral: 6.0-9.0
- Basa: > 8.0

**Kelembaban (%):**
- Kering: < 38%
- Lembab: 28-95%
- Basah: > 85%

**Curah Hujan:**
- Cerah: 0
- Hujan: 1

### Output Variables:

**Irigasi (ml/hari):**
- Sedikit: 0-1200 ml
- Cukup: 1000-2200 ml
- Banyak: 2000-3000 ml

**Pupuk (kg):**
- Stop: 0-25 kg
- Sedikit: 15-55 kg
- Banyak: 45-100 kg

## Firebase Connection Error
**Problem:** Firebase: Offline di sidebar

**Solution:**
1. Pastikan `firebase_credentials.json` ada di folder root
2. Cek format JSON credentials (harus valid)
3. Verifikasi `databaseURL` di app.py sesuai dengan Firebase project
4. Cek Firebase Database Rules (pastikan read/write enabled untuk testing)

### Device Status: OFFLINE
**Problem:** Sensor tidak update (stuck di nilai yang sama)

**Solution:**
1. Cek koneksi WiFi ESP32
2. Restart ESP32
3. Verifikasi data terkirim ke Firebase (cek Firebase Console)
4. Timeout default 20 detik, tunggu atau restart app

### Model ML Tidak Ditemukan
**Problem:** "Model ML Tidak Ditemukan" di sidebar

**Solution:**
1. Pastikan file `model_naivebayes.pkl` dan `scaler.pkl` ada di folder root
2. Re-train model jika file hilang/corrupt
3. Download dari repository jika tersedia

## Video Demo

**Link Video Demonstrasi:** [YouTube Link - To Be Added]

## License

MIT License - Free to use for educational purposes