import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
from datetime import datetime
import random
import json
import os
import hashlib
import pickle

# Optional: Firebase admin for realtime DB polling
try:
    import firebase_admin
    from firebase_admin import credentials, db
except Exception:
    firebase_admin = None

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="🌾 SmartFarm Expert System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== LOAD AI MODELS (NAIVE BAYES & SCALER) ====================
@st.cache_resource
def load_ai_models():
    model = None
    scaler = None
    try:
        # Load Model Naive Bayes
        model_path = os.path.join(os.path.dirname(__file__), "model_naivebayes.pkl")
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

        # Load Scaler
        scaler_path = os.path.join(os.path.dirname(__file__), "scaler.pkl")
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                scaler = pickle.load(f)
                
        return model, scaler
    except Exception as e:
        st.error(f"Error loading AI Models: {e}")
        return None, None

ai_model, ai_scaler = load_ai_models()

# Mapping Hasil Prediksi
AI_CLASSES = {
    0: "Sehat",
    1: "Kurang Hara", 
    2: "Tanah Masam", 
    3: "Kering"
}

# ==================== KNOWLEDGE BASE & MASTER DATA ====================
KNOWLEDGE_BASE = []
MASTER_DATA = {}

# Load external knowledge base
KB_FILE = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
try:
    if os.path.exists(KB_FILE):
        with open(KB_FILE, "r", encoding="utf-8") as _f:
            _kb = json.load(_f)
            if isinstance(_kb, list): KNOWLEDGE_BASE = _kb
except:
    pass

# Load master data definitions
MASTER_FILE = os.path.join(os.path.dirname(__file__), "master_data.json")
try:
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as mf:
            MASTER_DATA = json.load(mf).get('definitions', {})
except:
    pass

def get_label_from_master(sensor, value):
    defs = MASTER_DATA.get(sensor)
    if not defs: return None
    for d in defs:
        op = d.get('operator')
        if op == '<' and value < d.get('value'): return d.get('label')
        elif op == '>' and value > d.get('value'): return d.get('label')
        elif op == 'range' and d.get('min') <= value <= d.get('max'): return d.get('label')
        elif 'value' in d and value == d.get('value'): return d.get('label')
    return None

# ==================== FIREBASE CONNECTION ====================
def init_firebase():
    if not firebase_admin._apps:
        try:
            cred_path = "firebase_credentials.json"
            if not os.path.exists(cred_path):
                cred_path = os.path.join(os.path.dirname(__file__), "firebase_credentials.json")
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://matkul-9f44d-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
                return True
            else:
                return False
        except Exception:
            return False
    return True

def get_data_from_firebase(is_connected):
    if is_connected:
        try:
            ref = db.reference('/Monitoring')
            data = ref.get()
            
            if data:
                return {
                    'ph': float(data.get('pH') or data.get('ph') or 7.0),
                    'tds': int(data.get('TDS') or data.get('tds') or 0),
                    'soil_moisture': int(data.get('SoilMoisture') or data.get('soil_moisture') or data.get('soil') or 0),
                    'water_temp': float(data.get('WaterTemp') or data.get('suhu_air') or 0),
                    'air_temp': float(data.get('AirTemp') or data.get('suhu_udara') or 0),
                    'air_humidity': int(data.get('Humidity') or data.get('humidity') or data.get('kelembaban_udara') or 0),
                    'rainfall': int(data.get('Rainfall') or data.get('rainfall') or data.get('curah_hujan') or 0),
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'date': datetime.now().strftime("%d-%m-%Y")
                }
        except:
            pass

    # Dummy Data Generator (Offline Mode)
    return {
        'ph': round(random.uniform(5.5, 8.5), 2),
        'tds': int(random.uniform(300, 2500)),
        'soil_moisture': int(random.uniform(10, 100)),
        'water_temp': round(random.uniform(22, 35), 1),
        'air_temp': round(random.uniform(24, 38), 1),
        'air_humidity': int(random.uniform(40, 95)),
        'rainfall': int(random.choice([0, 100])),
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'date': datetime.now().strftime("%d-%m-%Y")
    }

# ==================== HELPER: SAFE VALUE FOR WIDGETS ====================
def safe_val(val, min_v, max_v):
    """Memastikan nilai default widget tidak error jika sensor memberikan nilai aneh"""
    if val < min_v: return min_v
    if val > max_v: return max_v
    return val

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0c4a6e, #1e293b, #0f172a);
        color: #e2e8f0;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    .section-header {
        display: flex; align-items: center; gap: 10px;
        font-size: 1.5rem; font-weight: 700; margin: 1.5rem 0 1rem;
        color: #94a3b8;
    }
    .section-header .icon {
        display: inline-flex; justify-content: center; align-items: center;
        width: 36px; height: 36px; border-radius: 50%;
        background: rgba(56, 189, 248, 0.15);
        color: #60a5fa;
        font-size: 1.1rem;
    }
    .sensor-card {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 16px; padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        border: 1px solid rgba(56, 189, 248, 0.2);
        transition: all 0.3s ease;
    }
    .sensor-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.3), 0 0 0 2px rgba(34, 197, 94, 0.3);
    }
    .sensor-title {
        font-size: 0.85rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;
        margin-bottom: 6px;
    }
    .sensor-value {
        font-size: 2.1rem; font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .sensor-unit { font-size: 1.2rem; color: #cbd5e1; margin-left: 4px; }
    .sensor-label { font-size: 0.9rem; font-weight: 600; color: #60a5fa; margin-top: 4px; }
    .sensor-label.bad { color: #f87171; }
    .sensor-label.good { color: #4ade80; }
    .sensor-label.warn { color: #fbbf24; }

    /* AI Prediction Card (Realtime) */
    .ai-realtime-card {
        background: linear-gradient(135deg, #2e1065, #4c1d95);
        border-left: 6px solid #d8b4fe;
        padding: 25px;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        display: flex; align-items: center; justify-content: space-between;
    }
    .ai-realtime-title { color: #e9d5ff; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
    .ai-realtime-result { font-size: 2.5rem; color: #ffffff; font-weight: 900; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    .ai-realtime-sub { color: #c084fc; font-size: 0.9rem; }

    .terminal-box {
        background-color: #0c0c0c; color: #e0e0e0; padding: 24px;
        border-radius: 12px; border: 1px solid #334155;
        font-family: 'JetBrains Mono', monospace; white-space: pre-wrap;
    }
    .terminal-box .hl-key { color: #60a5fa; font-weight: bold; }
    .terminal-box .hl-val { color: #34d399; }
    .terminal-box .hl-warn { color: #fbbf24; }
    div.stButton > button {
        background: linear-gradient(90deg, #10b981, #059669); color: white;
        font-weight: 700; padding: 12px 20px; border-radius: 12px; width: 100%; border: none;
    }
    .streamlit-expanderHeader { background: rgba(30, 41, 59, 0.7) !important; color: #cbd5e1 !important; }
    
    /* STATUS BADGE */
    .status-online { color: #4ade80; font-weight: bold; padding: 2px 8px; border: 1px solid #4ade80; border-radius: 4px; }
    .status-offline { color: #f87171; font-weight: bold; padding: 2px 8px; border: 1px solid #f87171; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ==================== FUZZY LOGIC FUNCTIONS ====================
def trimf(x, abc):
    a, b, c = abc; y = np.zeros_like(x)
    mask_left = (x > a) & (x <= b); mask_right = (x > b) & (x < c)
    if b != a: y[mask_left] = (x[mask_left] - a) / (b - a)
    if c != b: y[mask_right] = (c - x[mask_right]) / (c - b)
    y[x == b] = 1.0
    return y

def trapmf(x, abcd):
    a, b, c, d = abcd; y = np.zeros_like(x)
    mask_left = (x > a) & (x < b); mask_right = (x > c) & (x < d)
    if b != a: y[mask_left] = (x[mask_left] - a) / (b - a)
    y[(x >= b) & (x <= c)] = 1.0
    if d != c: y[mask_right] = (d - x[mask_right]) / (d - c)
    return y

def defuzzifikasi_centroid(x, mfx):
    num = np.sum(x * mfx); den = np.sum(mfx)
    return num / den if den != 0 else 0

x_irigasi = np.linspace(0, 3000, 1000)
irigasi_sedikit = trapmf(x_irigasi, [0, 0, 1000, 1200])
irigasi_cukup   = trimf(x_irigasi, [1000, 1600, 2200])
irigasi_banyak  = trapmf(x_irigasi, [2000, 2500, 3000, 3000])

x_pestisida = np.linspace(0, 100, 500)
pestisida_kurang   = trimf(x_pestisida, [0, 15, 30])
pestisida_optimal  = trimf(x_pestisida, [25, 45, 65])
pestisida_berlebih = trapmf(x_pestisida, [55, 75, 100, 100])

x_pupuk = np.linspace(0, 100, 500)
pupuk_stop = trapmf(x_pupuk, [0, 0, 10, 25])
pupuk_sedikit = trimf(x_pupuk, [15, 35, 55])
pupuk_penuh = trimf(x_pupuk, [45, 62.5, 80])

def fuzzifikasi_input(tds, ph, hum, hujan):
    mu = {}
    if tds <= 400: mu['tds_kurang'] = 1.0
    elif 400 < tds < 500: mu['tds_kurang'] = (500 - tds) / 100.0
    else: mu['tds_kurang'] = 0.0
    if 400 <= tds <= 500: mu['tds_ideal'] = (tds - 400) / 100.0
    elif 500 < tds <= 1900: mu['tds_ideal'] = 1.0
    elif 1900 < tds < 2100: mu['tds_ideal'] = (2100 - tds) / 200.0
    else: mu['tds_ideal'] = 0.0
    if tds <= 1900: mu['tds_lebih'] = 0.0
    elif 1900 < tds < 2100: mu['tds_lebih'] = (tds - 1900) / 200.0
    else: mu['tds_lebih'] = 1.0

    if ph <= 6.0: mu['ph_masam'] = 1.0
    elif 6.0 < ph < 7.0: mu['ph_masam'] = (7.0 - ph) / 1.0
    else: mu['ph_masam'] = 0.0
    if 6.0 <= ph <= 7.0: mu['ph_netral'] = (ph - 6.0) / 1.0
    elif 7.0 < ph <= 8.0: mu['ph_netral'] = 1.0
    elif 8.0 < ph < 9.0: mu['ph_netral'] = (9.0 - ph) / 1.0
    else: mu['ph_netral'] = 0.0
    if ph <= 8.0: mu['ph_basa'] = 0.0
    elif 8.0 < ph < 9.0: mu['ph_basa'] = (ph - 8.0) / 1.0
    else: mu['ph_basa'] = 1.0

    if hum <= 28: mu['hum_kering'] = 1.0
    elif 28 < hum < 38: mu['hum_kering'] = (38 - hum) / 10.0
    else: mu['hum_kering'] = 0.0
    if 28 <= hum <= 38: mu['hum_opt'] = (hum - 28) / 10.0
    elif 38 < hum <= 85: mu['hum_opt'] = 1.0
    elif 85 < hum < 95: mu['hum_opt'] = (95 - hum) / 10.0
    else: mu['hum_opt'] = 0.0
    if hum <= 85: mu['hum_basah'] = 0.0
    elif 85 < hum < 95: mu['hum_basah'] = (hum - 85) / 10.0
    else: mu['hum_basah'] = 1.0

    if hujan < 0.5: mu['hujan_cerah'] = 1.0; mu['hujan_turun'] = 0.0
    else: mu['hujan_cerah'] = 0.0; mu['hujan_turun'] = 1.0
    return mu

def inferensi_mamdani_baru(mu):
    tds_k, tds_i, tds_l = mu['tds_kurang'], mu['tds_ideal'], mu['tds_lebih']
    hum_k, hum_o, hum_b = mu['hum_kering'], mu['hum_opt'], mu['hum_basah']
    ph_m, ph_n, ph_b    = mu['ph_masam'], mu['ph_netral'], mu['ph_basa']
    hujan_c, hujan_t    = mu['hujan_cerah'], mu['hujan_turun']

    rules_irigasi, rules_pupuk, rules_pesti = [], [], []

    rules_irigasi.append(np.fmin(hum_k, irigasi_banyak))
    kondisi_air_berlebih = np.fmax(hum_b, hujan_t)
    rules_irigasi.append(np.fmin(kondisi_air_berlebih, irigasi_sedikit))
    rules_irigasi.append(np.fmin(np.fmin(hum_o, hujan_c), irigasi_cukup))

    rules_pupuk.append(np.fmin(hum_k, pupuk_stop))
    rules_pupuk.append(np.fmin(ph_m, pupuk_stop))
    rules_pupuk.append(np.fmin(tds_l, pupuk_stop))
    syarat_pupuk_hujan = np.fmin(hujan_t, np.fmin(tds_k, ph_n))
    rules_pupuk.append(np.fmin(syarat_pupuk_hujan, pupuk_penuh))
    syarat_pupuk_std = np.fmin(hum_o, np.fmin(ph_n, tds_k))
    rules_pupuk.append(np.fmin(syarat_pupuk_std, pupuk_penuh))
    syarat_pupuk_mnt = np.fmin(hum_o, np.fmin(ph_n, tds_i))
    rules_pupuk.append(np.fmin(syarat_pupuk_mnt, pupuk_sedikit))

    rules_pesti.append(np.fmin(ph_m, pestisida_berlebih))
    rules_pesti.append(np.fmin(kondisi_air_berlebih, pestisida_berlebih))
    rules_pesti.append(np.fmin(np.fmin(hum_k, hujan_c), pestisida_kurang))
    rules_pesti.append(np.fmin(hum_o, pestisida_optimal))

    agg_irigasi = np.zeros_like(x_irigasi)
    for r in rules_irigasi: agg_irigasi = np.fmax(agg_irigasi, r)
    agg_pupuk = np.zeros_like(x_pupuk)
    for r in rules_pupuk: agg_pupuk = np.fmax(agg_pupuk, r)
    agg_pesti = np.zeros_like(x_pestisida)
    for r in rules_pesti: agg_pesti = np.fmax(agg_pesti, r)

    return agg_irigasi, agg_pupuk, agg_pesti

def hitung_diagnosa_cf(mu, rules_db):
    mapping = {
        "ph": {"masam": "ph_masam", "netral": "ph_netral", "basa": "ph_basa"},
        "tds": {"kurang": "tds_kurang", "ideal": "tds_ideal", "berlebih": "tds_lebih"},
        "kelembaban": {"kering": "hum_kering", "lembab": "hum_opt", "basah": "hum_basah"},
        "curah_hujan": {"cerah": "hujan_cerah", "hujan": "hujan_turun"}
    }
    best_rule = None; max_belief = -1.0 
    for rule in rules_db:
        try:
            conds = rule['conditions']
            val_ph   = mu.get(mapping["ph"].get(conds["ph"]), 0.0)
            val_tds  = mu.get(mapping["tds"].get(conds["tds"]), 0.0)
            val_hum  = mu.get(mapping["kelembaban"].get(conds["kelembaban"]), 0.0)
            val_rain = mu.get(mapping["curah_hujan"].get(conds["curah_hujan"]), 0.0)
            fire_strength = min(val_ph, val_tds, val_hum, val_rain)
            rule_cf_val = rule.get('results', {}).get('cf', 0.0) 
            current_score = fire_strength * rule_cf_val
            if current_score > max_belief:
                max_belief = current_score; best_rule = rule
        except Exception: continue
    if best_rule is None and rules_db: best_rule = rules_db[0]
    elif best_rule is None: best_rule = {"id": "ERR", "description": "Error", "results": {"status_t": "Error", "air_r": "-", "pupuk_q": "-", "pestisida_s": "-", "action_steps": [], "cf": 0}}
    return best_rule, max_belief * 100

# ==================== MAIN APP ====================

# 1. Fetch data Realtime
is_firebase_ok = init_firebase()
d = get_data_from_firebase(is_firebase_ok)

# 2. DEVICE STATUS LOGIC (ONLINE/OFFLINE based on Value Changes)
# Kunci sensor untuk dipantau perubahannya (exclude timestamp)
sensor_keys = ['ph', 'tds', 'soil_moisture', 'water_temp', 'air_temp', 'air_humidity', 'rainfall']
current_values = {k: d[k] for k in sensor_keys}

# Inisialisasi State Status
if 'device_status' not in st.session_state:
    st.session_state['device_status'] = 'OFFLINE' # Mulai dari Offline
    st.session_state['last_sensor_values'] = current_values
    st.session_state['last_change_time'] = time.time()

# Cek Perubahan
if current_values != st.session_state['last_sensor_values']:
    # Jika ada perubahan nilai sensor
    st.session_state['device_status'] = 'ONLINE'
    st.session_state['last_sensor_values'] = current_values
    st.session_state['last_change_time'] = time.time()
else:
    # Jika nilai SAMA (tidak berubah), cek durasi
    elapsed_time = time.time() - st.session_state['last_change_time']
    if elapsed_time > 20: # Timeout 20 detik
        st.session_state['device_status'] = 'OFFLINE'

# --- Inisialisasi DataFrame untuk Grafik ---
if 'history_df' not in st.session_state:
    st.session_state['history_df'] = pd.DataFrame(columns=['Waktu', 'pH', 'TDS', 'Kelembaban', 'Suhu'])

# Update DataFrame History (Hanya simpan jika Online atau data baru masuk)
new_row = {
    'Waktu': d['timestamp'],
    'pH': d['ph'],
    'TDS': d['tds'],
    'Kelembaban': d['soil_moisture'],
    'Suhu': d['water_temp']
}
# Tambah data baru & batasi 20 baris terakhir
st.session_state['history_df'] = pd.concat([st.session_state['history_df'], pd.DataFrame([new_row])], ignore_index=True).tail(20)


# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/sprout.png", width=60)
    st.markdown("<h2 style='color: #60a5fa; margin: 0;'>Smart Nutrition Monitoring</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; margin-top: -8px;'>IoT Expert Dashboard</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # STATUS INDICATOR
    status_color = "status-online" if st.session_state['device_status'] == 'ONLINE' else "status-offline"
    st.markdown(f"**Status Perangkat:** <span class='{status_color}'>{st.session_state['device_status']}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    is_firebase_ok = init_firebase()
    if is_firebase_ok: st.markdown("🟢 <span style='color: #4ade80;'>Firebase: Online</span>", unsafe_allow_html=True)
    else: st.markdown("⚠️ <span style='color: #fbbf24;'>Firebase: Offline</span>", unsafe_allow_html=True)
    
    if ai_model and ai_scaler: st.success("🤖 Model ML Loaded!")
    else: st.warning("⚠️ Model ML Tidak Ditemukan")

    use_auto_refresh = st.checkbox("🔄 Auto-Refresh Sensor", value=True)
    refresh_interval = st.slider("Interval (detik)", 2, 10, 3, help="Kecepatan update data sensor")
    
    st.markdown("---")
    st.caption("© 2025 Smart Nutrition Monitoring")

# Header
st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h1 style="color: white; margin: 0; font-weight: 800;">Smart Nutrition Monitoring</h1>
    <p style="color: #94a3b8; margin-top: 8px;">Alat IoT untuk Monitoring Nutrisi Tanah pada Tanaman Padi</p>
</div>
""", unsafe_allow_html=True)

# 3. PROSES AI OTOMATIS
ai_status_label = "Model Not Loaded"
ai_input_info = ""

if ai_model and ai_scaler:
    try:
        # FIX: MAPPING INPUT AI YANG BENAR [pH, Temp Udara, Kelembaban Tanah, TDS]
        features = np.array([[d['ph'], d['air_temp'], d['soil_moisture'], d['tds']]])
        scaled_features = ai_scaler.transform(features)
        prediction = ai_model.predict(scaled_features)[0]
        ai_status_label = AI_CLASSES.get(prediction, f"Unknown ({prediction})")
        ai_input_info = f"pH:{d['ph']} | Suhu:{d['air_temp']}°C | Tanah:{d['soil_moisture']}% | TDS:{d['tds']}"
    except Exception as e:
        ai_status_label = "Prediction Error"

# 4. TAMPILKAN CARD AI
st.markdown(f"""
<div class="ai-realtime-card">
    <div>
        <div class="ai-realtime-title">🤖 Status Kesehatan Tanah</div>
        <div class="ai-realtime-result">{ai_status_label}</div>
        <div class="ai-realtime-sub">Input Realtime: {ai_input_info}</div>
    </div>
    <div style="font-size: 3rem;">🌱</div>
</div>
""", unsafe_allow_html=True)

# 5. TAMPILKAN GRID SENSOR
st.markdown('<div class="section-header"><span class="icon">📡</span> <span>Monitoring Lahan</span></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

def get_status_class(value, sensor):
    label = get_label_from_master(sensor, value)
    if not label: return ""
    if "aman" in label.lower() or "ideal" in label.lower() or "optimal" in label.lower(): return "good"
    elif "tinggi" in label.lower() or "berlebih" in label.lower() or "basah" in label.lower(): return "warn"
    else: return "bad"

with col1:
    label = get_label_from_master('ph', d['ph']) or 'Normal'
    st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🧪 pH</div><div><span class="sensor-value">{d['ph']}</span><span class="sensor-unit">pH</span></div><div class="sensor-label {get_status_class(d['ph'], 'ph')}">{label}</div></div>""", unsafe_allow_html=True)
with col2:
    label = get_label_from_master('tds', d['tds']) or 'Normal'
    st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🧪 Nutrisi (TDS)</div><div><span class="sensor-value">{d['tds']}</span><span class="sensor-unit">ppm</span></div><div class="sensor-label {get_status_class(d['tds'], 'tds')}">{label}</div></div>""", unsafe_allow_html=True)
with col3:
    label = get_label_from_master('kelembaban', d['soil_moisture']) or 'Normal'
    st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🌱 Kelembaban Tanah</div><div><span class="sensor-value">{d['soil_moisture']}</span><span class="sensor-unit">%</span></div><div class="sensor-label {get_status_class(d['soil_moisture'], 'kelembaban')}">{label}</div></div>""", unsafe_allow_html=True)
with col4:
    rain_val = d['rainfall']
    rain_label = get_label_from_master('curah_hujan', rain_val) or ('Hujan' if rain_val > 0 else 'Cerah')
    status = "good" if rain_val == 0 else "warn"
    st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🌧️ Curah Hujan</div><div><span class="sensor-value">{rain_val}</span><span class="sensor-unit">mm</span></div><div class="sensor-label {status}">{rain_label}</div></div>""", unsafe_allow_html=True)

col5, col6, col7, col8 = st.columns(4)
with col5: st.markdown(f"""<div class="sensor-card"><div class="sensor-title">💧 Suhu Air</div><div><span class="sensor-value">{d['water_temp']}</span><span class="sensor-unit">°C</span></div></div>""", unsafe_allow_html=True)
with col6: st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🌬️ Suhu Udara</div><div><span class="sensor-value">{d['air_temp']}</span><span class="sensor-unit">°C</span></div></div>""", unsafe_allow_html=True)
with col7: st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🌧️ Kelembaban Udara</div><div><span class="sensor-value">{d['air_humidity']}</span><span class="sensor-unit">%</span></div></div>""", unsafe_allow_html=True)
with col8: st.markdown(f"""<div class="sensor-card"><div class="sensor-title">🕒 Terakhir Update</div><div><span class="sensor-value">{d['timestamp']}</span></div><div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">{d['date']}</div></div>""", unsafe_allow_html=True)

# 6. GRAFIK (LIVE CHART)
st.markdown('<div class="section-header"><span class="icon">📈</span> <span>Grafik Realtime</span></div>', unsafe_allow_html=True)
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.caption("Tren pH & Nutrisi (TDS)")
    st.line_chart(st.session_state['history_df'][['pH', 'TDS']])

with chart_col2:
    st.caption("Tren Kelembaban Tanah & Suhu Air")
    st.line_chart(st.session_state['history_df'][['Kelembaban', 'Suhu']])

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# 7. EXPERT SYSTEM SECTION
st.markdown('<div class="section-header"><span class="icon">🧠</span> <span>Sistem Pakar (Menangani Masalah Padi)</span></div>', unsafe_allow_html=True)

input_col, output_col = st.columns([1, 1.2])

with input_col:
    st.markdown("#### 🎛️ Input Kondisi")
    with st.form("input_form"):
        st.info("Sesuaikan nilai input berdasarkan kondisi lahan saat ini untuk menjalankan sistem pakar.")
        in_tds = st.number_input("Nutrisi (TDS)", 0, 5000, safe_val(int(d['tds']), 0, 5000))
        in_ph = st.number_input("pH", 0.0, 14.0, safe_val(float(d['ph']), 0.0, 14.0), step=0.1)
        in_soil = st.slider("Kelembaban Tanah (%)", 0, 100, safe_val(int(d['soil_moisture']), 0, 100))
        in_rain = st.radio("Cuaca", [0, 1], format_func=lambda x: "☀️ Cerah" if x == 0 else "🌧️ Hujan", index=1 if d['rainfall'] > 0 else 0)
        submitted = st.form_submit_button("🔍 Analisis Masalah")

with output_col:
    if submitted:
        mu = fuzzifikasi_input(in_tds, in_ph, in_soil, in_rain)
        agg_ir, agg_pp, agg_pt = inferensi_mamdani_baru(mu)
        val_ir = defuzzifikasi_centroid(x_irigasi, agg_ir)
        val_pp = defuzzifikasi_centroid(x_pupuk, agg_pp)
        val_pt = defuzzifikasi_centroid(x_pestisida, agg_pt)
        rule_cf, val_cf = hitung_diagnosa_cf(mu, KNOWLEDGE_BASE)
        
        st.session_state['calc_result'] = {
            'mu': mu, 'val_ir': val_ir, 'val_pp': val_pp, 'val_pt': val_pt,
            'agg_ir': agg_ir, 'agg_pp': agg_pp, 'agg_pt': agg_pt,
            'rule_cf': rule_cf, 'val_cf': val_cf,
            'inputs': {'tds': in_tds, 'ph': in_ph, 'soil': in_soil, 'rain': in_rain}
        }

    if 'calc_result' in st.session_state:
        st.markdown("#### 📋 Hasil Simulasi Fuzzy")
        res_data = st.session_state['calc_result']
        rule = res_data['rule_cf']
        res = rule['results']
        cf_pct = res_data['val_cf']
        steps_txt = "\n".join([f"• {step}" for step in res['action_steps']]) or "  • Tidak ada langkah spesifik."

        output_text = f"""<span class="hl-key">OUTPUT FUZZY (SIMULASI):</span>
  Air        : <span class="hl-val">{res_data['val_ir']:.0f} L</span>
  Pupuk      : <span class="hl-val">{res_data['val_pp']:.2f} kg</span>
  Pestisida  : <span class="hl-val">{res_data['val_pt']:.1f} ml/m²</span>

<span class="hl-key">DIAGNOSA PAKAR:</span>
  Kondisi    : <span class="hl-val">{rule['description']}</span>
  Keyakinan  : <span class="{'hl-warn' if cf_pct < 70 else 'hl-val'}">{cf_pct:.1f}%</span>
  Status     : <span class="{'hl-alert' if 'buruk' in res['status_t'].lower() else 'hl-val'}">{res['status_t']}</span>

<span class="hl-key">REKOMENDASI:</span>
  💧  Air        : {res['air_r']}
  🌿 Pupuk      : {res['pupuk_q']}
  🐞 Pestisida  : {res['pestisida_s']}

<span class="hl-key">LANGKAH PERBAIKAN:</span>
<span class="steps">{steps_txt}</span>"""
        
        st.markdown(f'<div class="terminal-box">{output_text}</div>', unsafe_allow_html=True)
        
        with st.expander("📊 Grafik Fuzzy"):
            fig, ax = plt.subplots(1, 3, figsize=(15, 4), constrained_layout=True)
            ax[0].plot(x_irigasi, irigasi_sedikit, 'r--', alpha=0.7); ax[0].plot(x_irigasi, irigasi_cukup, 'g--', alpha=0.7); ax[0].plot(x_irigasi, irigasi_banyak, 'b--', alpha=0.7)
            ax[0].fill_between(x_irigasi, res_data['agg_ir'], color='#3b82f6', alpha=0.3)
            ax[0].axvline(res_data['val_ir'], color='k', linewidth=2)
            ax[0].set_title("Volume Irigasi")
            ax[1].plot(x_pupuk, pupuk_stop, 'r--', alpha=0.7); ax[1].plot(x_pupuk, pupuk_sedikit, 'g--', alpha=0.7); ax[1].plot(x_pupuk, pupuk_penuh, 'b--', alpha=0.7)
            ax[1].fill_between(x_pupuk, res_data['agg_pp'], color='#10b981', alpha=0.3)
            ax[1].axvline(res_data['val_pp'], color='k', linewidth=2)
            ax[1].set_title("Dosis Pupuk")
            ax[2].plot(x_pestisida, pestisida_kurang, 'r--', alpha=0.7); ax[2].plot(x_pestisida, pestisida_optimal, 'g--', alpha=0.7); ax[2].plot(x_pestisida, pestisida_berlebih, 'b--', alpha=0.7)
            ax[2].fill_between(x_pestisida, res_data['agg_pt'], color='#ef4444', alpha=0.3)
            ax[2].axvline(res_data['val_pt'], color='k', linewidth=2)
            ax[2].set_title("Dosis Pestisida")
            st.pyplot(fig)
    else:
        st.info("Klik tombol **Analisis Masalah** untuk melihat detail dosis & rekomendasi.")

# Auto-refresh
if use_auto_refresh:
    with st.spinner("🔄 Memperbarui data sensor..."):
        time.sleep(refresh_interval)
    st.rerun()