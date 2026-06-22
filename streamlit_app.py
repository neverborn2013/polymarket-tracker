import json
import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Anti-Bot Tracker V47", layout="wide")

# --- 🎨 CSS INTERFACE V47 ---
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

st.title("⚽ POLYMARKET RADAR V47 - HIỂN THỊ CHI TIẾT NHÁNH CƯỢC")

if "last_whale_alert_v47" not in st.session_state:
    st.session_state.last_whale_alert_v47 = {}
if "price_history" not in st.session_state:
    st.session_state.price_history = {}

# --- DANH SÁCH LINK MẶC ĐỊNH SĂN SONG SONG THỂ THAO & THỜI TIẾT ---
RAW_URL_LIST = """
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-23-2026 
  https://polymarket.com/event/highest-temperature-in-madrid-on-june-23-2026
  https://polymarket.com/event/highest-temperature-in-singapore-on-june-23-2026  
 https://polymarket.com/event/highest-temperature-in-new-york-on-june-22-2026 
  https://polymarket.com/vi/event/highest-temperature-in-london-on-june-22-2026   
 https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-23-2026 
 https://polymarket.com/vi/event/highest-temperature-in-seoul-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-taipei-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-beijing-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-chongqing-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-wuhan-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-lucknow-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-qingdao-on-june-23-2026
  https://polymarket.com/vi/event/highest-temperature-in-shanghai-on-june-23-2026 
  https://polymarket.com/vi/event/highest-temperature-in-shenzhen-on-june-23-2026 
  https://polymarket.com/vi/event/highest-temperature-in-chengdu-on-june-23-2026  
 https://polymarket.com/vi/event/highest-temperature-in-guangzhou-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-kuala-lumpur-on-june-23-2026  
 https://polymarket.com/vi/event/highest-temperature-in-manila-on-june-23-2026  
  https://polymarket.com/vi/event/highest-temperature-in-busan-on-june-23-2026 
 https://polymarket.com/vi/event/highest-temperature-in-karachi-on-june-23-20226 
 https://polymarket.com/vi/event/highest-temperature-in-cape-town-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-tel-aviv-on-june-23-2026
 https://polymarket.com/vi/event/highest-temperature-in-wellington-on-june-23-2026
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
https://polymarket.com/vi/sports/wta/wta-tauson-shnaide-2026-06-21 
https://polymarket.com/vi/sports/wta/wta-jovic-wa-2026-06-21
https://polymarket.com/vi/sports/world-cup/fifwc-arg-aut-2026-06-22
https://polymarket.com/vi/sports/world-cup/fifwc-fra-irq-2026-06-22
https://polymarket.com/vi/sports/mlb/mlb-tor-chc-2026-06-21
https://polymarket.com/vi/sports/mlb/mlb-nyy-det-2026-06-22
https://polymarket.com/vi/sports/mlb/mlb-kc-tb-2026-06-22
https://polymarket.com/vi/esports/dota-2/the-international/dota2-xctn-grind-2026-06-22
https://polymarket.com/vi/esports/dota-2/the-international/dota2-xctn-grind-2026-06-22
https://polymarket.com/vi/esports/dota-2/the-international/dota2-pr1-l1ga-2026-06-22
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

default_cities = [extract_slug(line) for line in RAW_URL_LIST.strip().split("\n") if extract_slug(line)]

if "city_slugs" not in st.session_state:
    st.session_state.city_slugs = default_cities
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 1000  
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"

default_routing = {"default": "-1004312043313"}
if "channel_routing" not in st.session_state:
    st.session_state.channel_routing = default_routing

# --- 🛠️ SIDEBAR CONFIG V47 ---
with st.sidebar:
    with st.form(key="config_form_v47"):
        st.header("🔌 Cấu hình Telegram")
        tg_token_input = st.text_input("Bot Token:", value=st.session_state.tg_token, type="password")
        id_def = st.text_input("ID Kênh Nhận Tin Tổng:", value=st.session_state.channel_routing.get("default", ""))

        st.write("---")
        st.header("🛡️ Bộ lọc tối cao V47")
        threshold_input = st.slider("Ngưỡng tiền lọc Cá Mập ($):", 50, 5000, value=st.session_state.whale_threshold, step=50)
        refresh_input = st.slider("Tốc độ quét (giây):", 5, 60, value=st.session_state.refresh_rate)
        
        submit_button = st.form_submit_button(label="💾 KÍCH HOẠT HỆ THỐNG V47", use_container_width=True)
        
        if submit_button:
            st.session_state.whale_threshold = threshold_input
            st.session_state.refresh_rate = refresh_input
            st.session_state.tg_token = tg_token_input
            st.session_state.channel_routing = {"default": id_def.strip()}
            st.toast("✅ Đã kích hoạt hệ thống V47 hiển thị nhánh cược chi tiết!")

TELEGRAM_TOKEN = st.session_state.tg_token
whale_threshold_usd = st.session_state.whale_threshold
refresh_rate = st.session_state.refresh_rate

st.subheader(f"📋 Hệ thống đang giám sát {len(st.session_state.city_slugs)} thị trường:")
cities_text = st.text_area(
    "Danh sách đường dẫn radar quét ngầm:", 
    value="\n".join([f"https://polymarket.com/event/{s}" for s in st.session_state.city_slugs]),
    height=130
)

current_input_slugs = [extract_slug(line) for line in cities_text.split("\n") if extract_slug(line)]
if current_input_slugs and current_input_slugs != st.session_state.city_slugs:
    st.session_state.city_slugs = current_input_slugs

def get_polymarket_hot_zones(slug):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and res.json():
            event_data = res.json()[0] if isinstance(res.json(), list) else res.json()
            market_title = event_data.get("title", "Kèo Thị Trường")
            markets_list = event_data.get("markets", [])
            
            raw_bins = []
            for m in markets_list:
                # 🚀 CẢI TIẾN LÕI V47: Ưu tiên lấy title đầy đủ của market để tránh bị mất tên tay vợt
                full_title = m.get("title", "")
                group_title = m.get("groupItemTitle", "")
                
                if group_title:
                    base_name = f"{full_title} ({group_title})"
                else:
                    base_name = full_title if full_title else market_title
                
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
    except: pass

# --- 🔄 VÒNG LẶP KIỂM TRA ĐỘC QUYỀN V47 ---
current_now = time.time()
st.write("---")

for target_slug in st.session_state.city_slugs:
    data = get_polymarket_hot_zones(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    analysis_labels = []
    
    st.markdown(f'<div class="city-header">📊 ĐANG QUÉT CỬA YES: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_đấu = row["Bin"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Giá trị lệnh thực ($)"]
        
        history_key = f"{target_slug}_{mốc_đấu}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        
        flow_type = "⚪ Nhỏ lẻ"

        # VÒNG 1: Kiểm tra rào chắn số tiền tối thiểu
        if real_usd >= whale_threshold_usd:
            if previous_usd is None:
                flow_type = "🔄 KHỞI TẠO NỀN (BỎ QUA)"
            else:
                delta_cash = abs(real_usd - previous_usd)
                cent_part = round(real_usd - int(real_usd), 2)
                
                # 🛡️ CHIẾN THUẬT KIM CƯƠNG V47: CHẶN BIÊN ĐỘ GIÁ (EDGE LOCK)
                is_price_too_high_or_low = price_cents > 90.0 or price_cents < 5.0
                
                # Kiểm tra độ biến động thực tế hợp lý của lệnh người thật
                is_invalid_delta = delta_cash < 350.0 or delta_cash > 35000.0
                
                is_bot_pattern = cent_part not in [0.0, 0.5] or is_invalid_delta or is_price_too_high_or_low
                
                if is_bot_pattern:
                    if is_price_too_high_or_low and delta_cash >= 350.0:
                        flow_type = "🤖 BOT TẤT TOÁN SÀN (ĐÃ CHẶN)"
                    else:
                        flow_type = "🤖 BOT MARKET MAKER (ĐÃ KHÓA)"
                else:
                    flow_type = "🔥 NGƯỜI THẬT MUA YES"
                    st.markdown(f'<div class="whale-real-alert">👑 PHÁT HIỆN CHUYÊN GIA GOM HÀNG SỚM 👑 Vị thế: {mốc_đấu} | Tiền vào ròng: ${delta_cash:,.2f} | Giá: {price_cents}¢</div>', unsafe_allow_html=True)
                    
                    last_alert_time = st.session_state.last_whale_alert_v47.get(history_key, 0)
                    if current_now - last_alert_time > 20:
                        urgent_msg = (
                            f"👤 *BÁO CÁO DÒNG TIỀN TỰ NHIÊN (CHUYÊN GIA) V47* 👤\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Chi tiết nhánh cược:* `{mốc_đấu}`\n"
                            f"🎯 *Hành động:* *🟢 MUA ĐỒNG Ý (YES)*\n"
                            f"💵 *Mức giá gom hợp lý:* `{price_cents}¢`\n"
                            f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                            f"📊 *Tổng vốn vị thế:* `${real_usd:,.2f}`\n\n"
                            f"🛡 *Radar V47: Sửa lỗi gộp chuỗi, hiển thị tường minh chi tiết tên tay vợt và mốc kèo chấp.*"
                        )
                        send_telegram_all(urgent_msg)
                        st.session_state.last_whale_alert_v47[history_key] = current_now
        
        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

st.info(f"⚙️ Hệ thống hiển thị chi tiết V47 đang hoạt động bảo mật.")
time.sleep(refresh_rate)
st.rerun()
