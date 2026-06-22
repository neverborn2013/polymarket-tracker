import json
import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Free-Format Tracker V40", layout="wide")

# --- 🎨 CSS INTERFACE ---
st.markdown(
    """
    <style>
    @keyframes blink-green {
        0% { background-color: rgba(46, 204, 113, 0.15); border-color: #2ecc71; box-shadow: 0 0 5px #2ecc71; }
        50% { background-color: rgba(46, 204, 113, 0.85); border-color: #27ae60; box-shadow: 0 0 15px #2ecc71; color: white; }
        100% { background-color: rgba(46, 204, 113, 0.15); border-color: #2ecc71; box-shadow: 0 0 5px #2ecc71; }
    }
    .whale-real-alert {
        padding: 12px;
        border: 2px solid #2ecc71;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
        animation: blink-green 1.5s infinite;
        color: #1e7e34;
    }
    .city-header {
        background-color: #2c3e50;
        color: white;
        padding: 8px 15px;
        border-radius: 5px;
        margin-top: 15px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 POLYMARKET TRACKER V40 - TEXT-LIST LINKS (YES ONLY)")

# --- 🔐 STATE INITIALIZATION ---
if "last_whale_alert_v40" not in st.session_state:
    st.session_state.last_whale_alert_v40 = {}
if "price_history" not in st.session_state:
    st.session_state.price_history = {}

# =====================================================================
# 🎯 KHU VỰC DÁN LINK THOẢI MÁI (MỖI DÒNG MỘT LINK - KHÔNG CẦN DẤU NGOẶC)
# Bạn muốn thêm bao nhiêu link thì cứ xuống dòng dán bình thường vào đây.
# Không lo lỗi viết sai dấu ngoặc kép trên iPhone nữa!
# =====================================================================
RAW_URL_LIST = """
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-22-2026
    https://polymarket.com/event/highest-temperature-in-madrid-on-june-23-2026
   https://polymarket.com/event/highest-temperature-in-singapore-on-june-22-2026 
   https://polymarket.com/event/highest-temperature-in-new-york-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-london-on-june-22-2026   
 https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-shanghai-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-shenzhen-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-chengdu-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-guangzhou-on-june-22-2026
  https://polymarket.com/vi/event/highest-temperature-in-kuala-lumpur-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-manila-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-busan-on-june-22-2026  
 https://polymarket.com/vi/event/highest-temperature-in-karachi-on-june-22-20226 
  https://polymarket.com/vi/event/highest-temperature-in-paris-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-munich-on-june-22-2026  
  https://polymarket.com/vi/event/highest-temperature-in-istanbul-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-ankara-on-june-22-2026    
https://polymarket.com/vi/event/highest-temperature-in-warsaw-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-helsinki-on-june-22-2026 
   https://polymarket.com/vi/event/highest-temperature-in-amsterdam-on-june-22-20226 
  https://polymarket.com/vi/event/highest-temperature-in-moscow-on-june-22-2026
   https://polymarket.com/vi/event/highest-temperature-in-nyc-on-june-22-2026   
 https://polymarket.com/vi/event/highest-temperature-in-atlanta-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-chicago-on-june-22-2026
  https://polymarket.com/vi/event/highest-temperature-in-houston-on-june-22-2026
 https://polymarket.com/vi/event/highest-temperature-in-miami-on-june-22-2026  
 https://polymarket.com/vi/event/highest-temperature-in-los-angeles-on-june-22-2026  
 https://polymarket.com/vi/event/highest-temperature-in-san-francisco-on-june-22-2026   
https://polymarket.com/vi/event/highest-temperature-in-seattle-on-june-22-2026   
https://polymarket.com/vi/event/highest-temperature-in-denver-on-june-22-2026    
https://polymarket.com/vi/event/highest-temperature-in-dallas-on-june-22-2026  
 https://polymarket.com/vi/event/highest-temperature-in-austin-on-june-22-202
 https://polymarket.com/vi/event/highest-temperature-in-toronto-on-june-22-2026
"""

def extract_slug(url_str):
    try:
        cleaned_url = url_str.strip().rstrip('/')
        if not cleaned_url: return None
        parsed = urllib.parse.urlparse(cleaned_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if "event" in path_parts or "market" in path_parts: return path_parts[-1]
        return path_parts[-1]
    except: return None

# Tự động lọc và xử lý danh sách chuỗi thô thành mảng liên kết chuẩn
default_cities = []
for line in RAW_URL_LIST.strip().split("\n"):
    slug = extract_slug(line)
    if slug: default_cities.append(slug)

if "city_slugs" not in st.session_state:
    st.session_state.city_slugs = default_cities
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 1500  # Ngưỡng mặc định 1500 để chặn bot mồi hiệu quả
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFyI8XFh3S_7WpW5D87uP6k"

default_routing = {"default": "-1004312043313"}
if "channel_routing" not in st.session_state:
    st.session_state.channel_routing = default_routing

# --- 🛠️ SIDEBAR CONFIG ---
with st.sidebar:
    with st.form(key="config_form"):
        st.header("🔌 Telegram Setup")
        tg_token_input = st.text_input("Bot Token:", value=st.session_state.tg_token, type="password")
        id_def = st.text_input("ID Kênh Nhận Tin:", value=st.session_state.channel_routing.get("default", ""))

        st.write("---")
        st.header("🛡️ Filters")
        threshold_input = st.slider("Ngưỡng tiền lọc Cá Mập ($):", 50, 5000, value=st.session_state.whale_threshold, step=50)
        refresh_input = st.slider("Tốc độ quét (giây):", 5, 60, value=st.session_state.refresh_rate)
        
        submit_button = st.form_submit_button(label="💾 CẬP NHẬT ĐỒNG BỘ V40", use_container_width=True)
        
        if submit_button:
            st.session_state.whale_threshold = threshold_input
            st.session_state.refresh_rate = refresh_input
            st.session_state.tg_token = tg_token_input
            st.session_state.channel_routing = {"default": id_def.strip()}
            st.toast("✅ Đã áp dụng cấu hình đồng bộ!")

TELEGRAM_TOKEN = st.session_state.tg_token
whale_threshold_usd = st.session_state.whale_threshold
refresh_rate = st.session_state.refresh_rate

# --- 📝 INTERFACE LIST DISPLAY ---
st.subheader(f"📋 Hệ thống đang quét ngầm liên tục {len(st.session_state.city_slugs)} link kèo dưới đây:")
cities_text = st.text_area(
    "Danh sách link hiện tại:", 
    value="\n".join([f"https://polymarket.com/event/{s}" for s in st.session_state.city_slugs]),
    height=150
)

current_input_slugs = []
for line in cities_text.split("\n"):
    slug = extract_slug(line)
    if slug: current_input_slugs.append(slug)

if current_input_slugs and current_input_slugs != st.session_state.city_slugs:
    st.session_state.city_slugs = current_input_slugs
    st.toast("🔄 Đã ghi nhận danh sách link mới!")

def get_polymarket_hot_zones(slug):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and res.json():
            event_data = res.json()[0] if isinstance(res.json(), list) else res.json()
            market_title = event_data.get("title", "Kèo Không Tên")
            markets_list = event_data.get("markets", [])
            
            raw_bins = []
            for m in markets_list:
                base_name = m.get("groupItemTitle") or m.get("title", "")
                if "will be " in base_name: base_name = base_name.split("will be ")[-1].strip()
                else: base_name = base_name.replace(market_title, "").strip()
                
                try:
                    prices_arr = json.loads(m.get("outcomePrices", "[0, 0]"))
                    price_yes = float(prices_arr[0]) * 100
                except: price_yes = 0.0

                liquidity = float(m.get("liquidity", 0))
                est_volume = round(liquidity / 4, 2)

                raw_bins.append({
                    "Base_Name": base_name,
                    "YES_Price": price_yes,
                    "Volume": est_volume
                })
            
            df_raw = pd.DataFrame(raw_bins)
            hot_zones = df_raw.sort_values(by="Volume", ascending=False).head(4)

            final_data = []
            for _, row in hot_zones.iterrows():
                real_usd_yes = round((row['Volume'] * row['YES_Price']) / 100, 2)
                final_data.append({"Bin": row['Base_Name'], "Side": "YES", "Giá (Cents)": round(row['YES_Price'], 2), "Giá trị lệnh thực ($)": real_usd_yes})
                
            return {"title": market_title, "df": pd.DataFrame(final_data)}
        return None
    except: return None

def send_telegram_all(message):
    if not TELEGRAM_TOKEN: return
    target_chat_id = st.session_state.channel_routing.get("default", "").strip()
    if not target_chat_id: return
    try: 
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": target_chat_id, "text": message, "parse_mode": "Markdown"}, 
                      timeout=5)
    except: 
        pass

# --- MAIN LOOP ---
current_now = time.time()
st.write("---")

for target_slug in st.session_state.city_slugs:
    data = get_polymarket_hot_zones(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    analysis_labels = []
    
    st.markdown(f'<div class="city-header">🏙️ ĐANG QUÉT CHỈ CỬA YES: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_nhiệt = row["Bin"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Giá trị lệnh thực ($)"]
        
        history_key = f"{target_slug}_{mốc_nhiệt}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        
        flow_type = "⚪ Nhỏ lẻ"

        if real_usd >= whale_threshold_usd:
            if previous_usd is not None and abs(real_usd - previous_usd) <= 5.0:
                flow_type = "🤖 BOT REFILL"
            else:
                flow_type = "🔥 CÓ NGƯỜI MUA YES"
                st.markdown(f'<div class="whale-real-alert">🟢 PHÁT HIỆN CÁ MẬP YES 🟢 Mốc: {mốc_nhiệt} | Số tiền: ${real_usd:,.2f}</div>', unsafe_allow_html=True)
                
                last_alert_time = st.session_state.last_whale_alert_v40.get(history_key, 0)
                if current_now - last_alert_time > 15:
                    urgent_msg = (
                        f"📊 *BÁO ĐỘNG BIẾN ĐỘNG: MUA ĐỒNG Ý (YES)* 📊\n\n"
                        f"🏙 *Thị trường:* {title}\n"
                        f"📌 *Vị thế mốc:* `{mốc_nhiệt}`\n"
                        f"🎯 *Hành động:* *🟢 MUA ĐỒNG Ý (YES)*\n"
                        f"💵 *Mức giá:* `{price_cents}¢`\n"
                        f"💰 *Tổng tiền cửa YES hiện tại:* *${real_usd:,.2f}*\n"
                        f"📬 _Hệ thống bảo vệ: Chỉ lọc lệnh YES trị giá cao._"
                    )
                    send_telegram_all(urgent_msg)
                    st.session_state.last_whale_alert_v40[history_key] = current_now
        
        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

st.info(f"⚙️ Radar V40 đang hoạt động hoàn toàn tự động. Vòng lặp {refresh_rate} giây.")
time.sleep(refresh_rate)
st.rerun()
