import json
import time
import urllib.parse
import re
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Radar V49.9 Smart Filter", layout="wide")

# --- 🎨 CHUẨN HÓA GIAO DIỆN CSS ---
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
    .market-header {
        background-color: #2c3e50;
        color: #f1c40f;
        padding: 10px 15px;
        border-radius: 6px;
        margin-top: 18px;
        margin-bottom: 8px;
        font-weight: bold;
        font-size: 14px;
        border-left: 5px solid #3498db;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 POLYMARKET RADAR V49.9 - GIẢI PHÓNG BỘ LỌC BOT & ĐỊNH VỊ TOP 6 BINS")

# Khởi tạo bộ nhớ đệm trạng thái hệ thống phòng tránh mất dữ liệu khi Rerun
if "last_whale_alert_v47" not in st.session_state:
    st.session_state.last_whale_alert_v47 = {}
if "price_history" not in st.session_state:
    st.session_state.price_history = {}
if "cents_price_history" not in st.session_state:
    st.session_state.cents_price_history = {}
if "entry_price_history" not in st.session_state:
    st.session_state.entry_price_history = {}
if "last_signal_time" not in st.session_state:
    st.session_state.last_signal_time = {}
if "reported_tele_keys" not in st.session_state:
    st.session_state.reported_tele_keys = []

# Danh sách URL theo dõi mặc định dựa trên cấu trúc các thành phố khí hậu của bạn
RAW_URL_LIST = """
https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-cape-town-on-june-24-2026
  https://polymarket.com/vi/event/highest-temperature-in-wellington-on-june-24-2026  
   https://polymarket.com/vi/event/highest-temperature-in-paris-on-june-24-2026
     https://polymarket.com/event/highest-temperature-in-madrid-on-june-24-2026
     https://polymarket.com/vi/event/highest-temperature-in-munich-on-june-24-2026   
    https://polymarket.com/vi/event/highest-temperature-in-atlanta-on-june-24-2026  
https://polymarket.com/vi/event/what-price-will-ethereum-hit-june-22-28-2026
https://polymarket.com/vi/sports/world-cup/fifwc-che-can-2026-06-24
https://polymarket.com/vi/sports/world-cup/fifwc-bih-qat-2026-06-24
https://polymarket.com/vi/sports/world-cup/fifwc-sco-bra-2026-06-24
https://polymarket.com/vi/sports/world-cup/fifwc-mar-hai-2026-06-24
https://polymarket.com/vi/sports/world-cup/fifwc-cze-mex-2026-06-24
https://polymarket.com/vi/sports/world-cup/fifwc-rsa-kr-2026-06-24
https://polymarket.com/event/bitcoin-above-105k-on-june-26-2026
https://polymarket.com/event/ethereum-above-4200-on-june-26-2026
https://polymarket.com/event/solana-ath-in-june-2026
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

default_slugs = [extract_slug(line) for line in RAW_URL_LIST.strip().split("\n") if extract_slug(line)]

if "target_slugs" not in st.session_state:
    st.session_state.target_slugs = default_slugs
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 200  
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"

if "channel_vip" not in st.session_state:
    st.session_state.channel_vip = "-1004312043313"
if "channel_ngach" not in st.session_state:
    st.session_state.channel_ngach = "-1004377611538"

with st.sidebar:
    with st.form(key="config_form_v49_9"):
        st.header("⚙️ Cấu hình Engine V49.9")
        tg_token_input = st.text_input("Telegram Bot Token:", value=st.session_state.tg_token, type="password")
        
        st.write("---")
        st.header("📢 Định tuyến Kênh")
        id_vip_input = st.text_input("ID Kênh VIP (Cá Voi):", value=st.session_state.channel_vip)
        id_ngach_input = st.text_input("ID Kênh Ngách (Gom Sớm):", value=st.session_state.channel_ngach)

        st.write("---")
        st.header("🛡️ Quản trị bộ lọc rủi ro")
        threshold_input = st.slider("Ngưỡng lọc tiền Cá Voi ($):", 50, 2000, value=st.session_state.whale_threshold, step=25)
        refresh_input = st.slider("Tần suất quét làm mới (giây):", 5, 60, value=st.session_state.refresh_rate)
        
        submit_button = st.form_submit_button(label="⚡ ĐỒNG BỘ ENGINE V49.9 SMART", use_container_width=True)
        
        if submit_button:
            st.session_state.whale_threshold = threshold_input
            st.session_state.refresh_rate = refresh_input
            st.session_state.tg_token = tg_token_input
            st.session_state.channel_vip = id_vip_input.strip()
            st.session_state.channel_ngach = id_ngach_input.strip()
            st.toast("🚀 Đã mở khóa bộ lọc thông minh, sẵn sàng bắt tín hiệu thật!")

TELEGRAM_TOKEN = st.session_state.tg_token
whale_threshold_usd = st.session_state.whale_threshold
refresh_rate = st.session_state.refresh_rate

st.subheader(f"📋 Danh sách thành phố đang giám sát ({len(st.session_state.target_slugs)}):")
slugs_text = st.text_area(
    "Danh sách URLs Polymarket mục tiêu:", 
    value="\n".join([f"https://polymarket.com/event/{s}" for s in st.session_state.target_slugs]),
    height=130
)

current_input_slugs = [extract_slug(line) for line in slugs_text.split("\n") if extract_slug(line)]
if current_input_slugs and current_input_slugs != st.session_state.target_slugs:
    st.session_state.target_slugs = current_input_slugs

def get_polymarket_top6_data(slug):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and res.json():
            event_data = res.json()[0] if isinstance(res.json(), list) else res.json()
            market_title = event_data.get("title", "Sự Kiện Polymarket")
            markets_list = event_data.get("markets", [])
            
            title_lower = market_title.lower()
            is_weather = "°c" in title_lower or "temperature" in title_lower or "°f" in title_lower
            is_sports = " vs " in title_lower or " vs. " in title_lower or "match" in title_lower

            raw_bins = []
            for m in markets_list:
                full_title = m.get("title", "")
                group_title = m.get("groupItemTitle", "")
                base_name = group_title if group_title else (full_title if full_title else market_title)
                
                try:
                    prices_arr = json.loads(m.get("outcomePrices", "[0, 0]"))
                    price_yes = float(prices_arr[0]) * 100
                except: price_yes = 0.0

                liquidity = float(m.get("liquidity", 0))
                est_volume = round(liquidity / 4, 2)
                
                # Tính toán tổng vốn vị thế dựa trên thanh khoản thực tế
                real_usd_yes = round((est_volume * price_yes) / 100, 2)

                raw_bins.append({
                    "Bin_Name": base_name,
                    "YES_Price": price_yes,
                    "Volume": est_volume,
                    "Total_Asset_Value": real_usd_yes
                })
            
            df_raw = pd.DataFrame(raw_bins)
            if df_raw.empty: return None

            # Sắp xếp lấy đúng 6 nhánh cược (bins) có tổng vốn vị thế cao nhất
            df_raw = df_raw.sort_values(by="Total_Asset_Value", ascending=False).head(6)

            final_data = []
            for _, row in df_raw.iterrows():
                final_data.append({
                    "Nhánh Cược (Bin)": row['Bin_Name'], 
                    "Side": "YES", 
                    "Giá (Cents)": float(f"{row['YES_Price']:.2f}"), 
                    "Tổng vốn vị thế ($)": row['Total_Asset_Value']
                })
                
            asset_type = "THỜI TIẾT" if is_weather else ("THỂ THAO" if is_sports else "TIN TỨC CỘNG ĐỒNG")
            return {"title": market_title, "df": pd.DataFrame(final_data), "asset_type": asset_type, "is_weather": is_weather}
        return None
    except: return None

def send_telegram(chat_id, message):
    if not TELEGRAM_TOKEN or not chat_id: return
    try: 
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, 
                      timeout=5)
    except: pass

current_now = time.time()
st.write("---")

for target_slug in st.session_state.target_slugs:
    data = get_polymarket_top6_data(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    asset_label = data["asset_type"]
    is_weather_mode = data["is_weather"]
    analysis_labels = []
    
    st.markdown(f'<div class="market-header">📡 RADAR GÁC CỔNG [{asset_label} - TOP 6 BINS]: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_đấu = row["Nhánh Cược (Bin)"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Tổng vốn vị thế ($)"]
        
        history_key = f"{target_slug}_{mốc_đấu}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        previous_cents = st.session_state.cents_price_history.get(history_key, None)
        
        flow_type = "⚪ Nhỏ lẻ"

        # --- CHỐT CHẶN PHÂN TẦNG QUẢN TRỊ RỦI RO ---
        if previous_cents is not None:
            if history_key in st.session_state.reported_tele_keys:
                entry_price = st.session_state.entry_price_history.get(history_key, previous_cents)
                total_drop_cents = entry_price - price_cents
                
                last_sig_time = st.session_state.last_signal_time.get(history_key, 0)
                allow_send_signal = (current_now - last_sig_time) > 120 
                
                is_trigger_sl = False
                reason_sl = ""
                
                if previous_cents <= 0.1 and price_cents <= 0.1:
                    is_trigger_sl = False
                else:
                    if is_weather_mode:
                        if price_cents <= 0.2 and previous_cents > 0.2:
                            is_trigger_sl = True
                            reason_sl = f"🚨 CHỐT CHẶN KHẨN CẤP: Nhánh khí hậu sập sát sàn đáy `{price_cents:.2f}¢`"
                    else:
                        if price_cents <= 4.0 and previous_cents > 4.0:
                            is_trigger_sl = True
                            reason_sl = f"🚨 CHỐT CHẶN TỬ THẦN: Cửa thể thao sập chạm sàn nguy hiểm `{price_cents:.1f}¢`"
                    
                    if not is_trigger_sl and entry_price > 1.0:
                        if entry_price > 50.0 and total_drop_cents >= 12.0:
                            is_trigger_sl = True
                            reason_sl = f"📉 Cửa trên gãy cấu trúc: Sụt giảm -{total_drop_cents:.1f}¢ từ gốc `{entry_price:.1f}¢`"
                        elif entry_price < 30.0 and (total_drop_cents / entry_price) >= 0.50:
                            is_trigger_sl = True
                            reason_sl = f"📉 Cửa dưới vỡ trận: Bị xả quá 50% giá trị vị thế gốc `{entry_price:.1f}¢`"

                if is_trigger_sl and allow_send_signal:
                    alert_sl = (
                        f"🚨 *[BÁO ĐỘNG PHÂN LUỒNG: ÉP LỆNH XẢ HÀNG V49.9]* 🚨\n\n"
                        f"🏆 *Thị trường ({asset_label}):* {title}\n"
                        f"📌 *Nhánh:* `{mốc_đấu}`\n"
                        f"⚠️ *Lý do rủi ro:* {reason_sl}\n"
                        f"💵 *Giá mua gốc:* `{entry_price:.2f}¢` ➡️ *Hiện tại:* `{price_cents:.2f}¢`"
                    )
                    send_telegram(st.session_state.channel_vip, alert_sl)
                    send_telegram(st.session_state.channel_ngach, alert_sl)
                    st.session_state.last_signal_time[history_key] = current_now

        st.session_state.cents_price_history[history_key] = price_cents

        # --- ENGINE BỘ LỌC THÔNG MINH ĐÃ ĐƯỢC GIẢI PHÓNG V49.9 ---
        if previous_usd is None:
            flow_type = "🔄 KHỞI TẠO NỀN"
        else:
            delta_cash = abs(real_usd - previous_usd)
            
            # ĐIỀU CHỈNH: Nới lỏng hoàn toàn bộ lọc cho mảng thời tiết, tránh khóa nhầm lệnh nhỏ của người dùng
            if is_weather_mode:
                is_price_too_high_or_low = price_cents > 99.5 or price_cents < 0.05
                # Chỉ coi là Bot MM nếu biến động cực kỳ bất thường (Quá lớn > 200,000$ hoặc quá bé < 0.2$)
                is_invalid_delta = delta_cash < 0.2 or delta_cash > 200000.0
                is_bot_pattern = is_invalid_delta or is_price_too_high_or_low
            else:
                is_price_too_high_or_low = price_cents > 95.0 or price_cents < 3.0
                is_invalid_delta = delta_cash < 5.0 or delta_cash > 50000.0
                cent_part = round(real_usd - int(real_usd), 2)
                is_bot_pattern = cent_part not in [0.0, 0.5] or is_invalid_delta or is_price_too_high_or_low
            
            if is_bot_pattern:
                flow_type = "🤖 BOT MARKET MAKER (ĐÃ KHÓA)"
            else:
                last_alert_time = st.session_state.last_whale_alert_v47.get(history_key, 0)
                
                # Điều chỉnh ngưỡng bắt Cá Voi cho linh hoạt theo từng mảng
                current_threshold = whale_threshold_usd if not is_weather_mode else (whale_threshold_usd * 0.4)

                if delta_cash >= current_threshold:
                    flow_type = "👑 [VIP] CÁ VOI KHỦNG"
                    st.markdown(f'<div class="whale-real-alert">👑 PHÁT HIỆN CÁ VOI | Nhánh: {mốc_đấu} | Tiền ròng: ${delta_cash:,.2f}</div>', unsafe_allow_html=True)
                    
                    if current_now - last_alert_time > 20:
                        urgent_msg = (
                            f"👑 *[PHÁT HIỆN CÁ VOI {asset_label}] V49.9* 👑\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Chi tiết nhánh cược:* `{mốc_đấu}`\n"
                            f"💵 *Mức giá gom hợp lý:* `{price_cents:.2f}¢`\n"
                            f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                            f"📊 *Tổng vốn vị thế:* *${real_usd:,.2f}*"
                        )
                        send_telegram(st.session_state.channel_vip, urgent_msg)
                        st.session_state.last_whale_alert_v47[history_key] = current_now
                        
                        if history_key not in st.session_state.reported_tele_keys:
                            st.session_state.reported_tele_keys.append(history_key)
                            st.session_state.entry_price_history[history_key] = price_cents
                        
                elif (is_weather_mode and delta_cash >= 1.5) or (not is_weather_mode and delta_cash >= 50.0):
                    # Đã hạ điều kiện tiền ròng xuống 1.5$ cho mảng Thời tiết để bắt được dòng tiền ngách sớm của user thực tế
                    flow_type = "🐟 [NGÁCH] GOM SỚM"
                    if current_now - last_alert_time > 20:
                        ngach_msg = (
                            f"🐟 *[TÍN HIỆU GOM SỚM {asset_label}] V49.9* 🐟\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Nhánh:* `{mốc_đấu}`\n"
                            f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                            f"📊 *Tổng vốn vị thế:* *${real_usd:,.2f}*"
                        )
                        send_telegram(st.session_state.channel_ngach, ngach_msg)
                        st.session_state.last_whale_alert_v47[history_key] = current_now
                        
                        if history_key not in st.session_state.reported_tele_keys:
                            st.session_state.reported_tele_keys.append(history_key)
                            st.session_state.entry_price_history[history_key] = price_cents
                else:
                    flow_type = f"⚪ Nhỏ lẻ (${delta_cash:.2f})"
        
        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

time.sleep(refresh_rate)
st.rerun()
