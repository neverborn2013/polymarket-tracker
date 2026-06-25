import json
import time
import urllib.parse
import re
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Radar V51.8 Premium", layout="wide")

# --- 🎨 CHUẨN HÓA GIAO DIỆN HỆ THỐNG ---
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

st.title("🚀 POLYMARKET RADAR V51.8 - QUICK-TEST 1 MIN & 30 MIN")

# --- 💾 KHỞI TẠO BỘ NHỚ ĐỆM TRẠNG THÁI CACHING ---
if "price_history" not in st.session_state:
    st.session_state.price_history = {}
if "cents_price_history" not in st.session_state:
    st.session_state.cents_price_history = {}
if "last_signal_time" not in st.session_state:
    st.session_state.last_signal_time = {}
if "last_whale_alert_v47" not in st.session_state:
    st.session_state.last_whale_alert_v47 = {}

# --- 🕒 ĐIỀU CHỈNH LOGIC TIMER THEO YÊU CẦU KIỂM TRA NHANH ---
if "bot_start_time" not in st.session_state:
    st.session_state.bot_start_time = time.time()
if "last_summary_time" not in st.session_state:
    st.session_state.last_summary_time = st.session_state.bot_start_time
# Cờ hiệu kiểm soát mốc gửi 1 phút đầu tiên
if "is_first_1min_sent" not in st.session_state:
    st.session_state.is_first_1min_sent = False

if "summary_data_accumulator" not in st.session_state:
    st.session_state.summary_data_accumulator = {}

# Cấu hình giá trị mặc định cho Hệ thống
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 100  
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"
if "channel_vip" not in st.session_state:
    st.session_state.channel_vip = "-1004312043313"
if "channel_ngach" not in st.session_state:
    st.session_state.channel_ngach = "-1004377611538"

# Danh sách URLs theo dõi mục tiêu mặc định ban đầu
RAW_URL_LIST = """
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-25-2026 
https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-25-2026 
 https://polymarket.com/vi/event/highest-temperature-in-seoul-on-june-25-2026 
 https://polymarket.com/vi/event/highest-temperature-in-shanghai-on-june-25-2026 
 https://polymarket.com/vi/event/highest-temperature-in-cape-town-on-june-25-2026 
 https://polymarket.com/vi/event/highest-temperature-in-wellington-on-june-25-2026
  https://polymarket.com/vi/event/highest-temperature-in-tel-aviv-on-june-25-2026
 https://polymarket.com/vi/event/highest-temperature-in-london-on-june-25-2026   
   https://polymarket.com/vi/event/highest-temperature-in-paris-on-june-25-2026 
    https://polymarket.com/event/highest-temperature-in-madrid-on-june-25-2026
    https://polymarket.com/vi/event/highest-temperature-in-munich-on-june-25-2026  
    https://polymarket.com/vi/event/highest-temperature-in-atlanta-on-june-25-2026 
https://polymarket.com/event/highest-temperature-in-new-york-on-june-25-2026  
 https://polymarket.com/vi/event/highest-temperature-in-san-francisco-on-june-25-2026    
https://polymarket.com/event/bitcoin-above-105k-on-june-26-2026 
https://polymarket.com/event/ethereum-above-4200-on-june-26-2026
https://polymarket.com/event/solana-ath-in-june-2026
https://polymarket.com/vi/event/what-price-will-bitcoin-hit-june-22-28-2026
https://polymarket.com/vi/event/what-price-will-bitcoin-hit-in-june-2026
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

# --- ⚙️ SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("⚙️ Cấu hình Engine V51.8")
    tg_token_input = st.text_input("Telegram Bot Token:", value=st.session_state.tg_token, type="password")
    
    st.write("---")
    st.header("📢 Định tuyến Kênh Telegram")
    id_vip_input = st.text_input("ID Kênh VIP (Cá Voi):", value=st.session_state.channel_vip)
    id_ngach_input = st.text_input("ID Kênh Ngách (Tổng Kết / Gom Sớm):", value=st.session_state.channel_ngach)

    st.write("---")
    st.header("🛡️ Bộ lọc Volume & Quét")
    threshold_input = st.slider("Ngưỡng lọc tiền Cá Voi ($):", 50, 2000, value=st.session_state.whale_threshold, step=50)
    refresh_input = st.slider("Tần suất quét làm mới (giây):", 5, 60, value=st.session_state.refresh_rate)
    
    if st.button("⚡ ĐỒNG BỘ SUITE TOÀN DIỆN V51.8", use_container_width=True):
        st.session_state.whale_threshold = threshold_input
        st.session_state.refresh_rate = refresh_input
        st.session_state.tg_token = tg_token_input
        st.session_state.channel_vip = id_vip_input.strip()
        st.session_state.channel_ngach = id_ngach_input.strip()
        st.toast(f"🔒 Đã cấu hình: Xuất tổng kết sau 1 phút chạy thử nghiệm!")

WHALE_LIMIT = float(st.session_state.whale_threshold)
REFRESH_TIME = int(st.session_state.refresh_rate)
TELEGRAM_TOKEN = st.session_state.tg_token

st.subheader(f"📋 Thị trường đang theo dõi chiến thuật (Top 6 Bins vốn cao):")
slugs_text = st.text_area(
    "Nhập danh sách Link sự kiện Polymarket cần quét:", 
    value="\n".join([f"https://polymarket.com/event/{s}" for s in st.session_state.target_slugs]),
    height=120
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
                real_usd_yes = round((est_volume * price_yes) / 100, 2)

                raw_bins.append({
                    "Bin_Name": base_name,
                    "YES_Price": price_yes,
                    "Total_Asset_Value": real_usd_yes
                })
            
            df_raw = pd.DataFrame(raw_bins)
            if df_raw.empty: return None

            df_raw = df_raw.sort_values(by="Total_Asset_Value", ascending=False).head(6)

            final_data = []
            for _, row in df_raw.iterrows():
                final_data.append({
                    "Nhánh Cược (Bin)": row['Bin_Name'], 
                    "Side": "YES", 
                    "Giá (Cents)": float(f"{row['YES_Price']:.2f}"), 
                    "Tổng vốn vị thế ($)": row['Total_Asset_Value']
                })
                
            asset_label = "THỜI TIẾT" if is_weather else ("THỂ THAO" if is_sports else "TIN TỨC CỘNG ĐỒNG")
            return {"title": market_title, "df": pd.DataFrame(final_data), "label": asset_label}
        return None
    except: return None

def send_telegram(chat_id, message):
    if not TELEGRAM_TOKEN or not chat_id: return
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

current_now = time.time()
st.write("---")

# Hiển thị bộ đếm giám sát trực tiếp trên giao diện chính
elapsed_from_start = current_now - st.session_state.bot_start_time
elapsed_from_last_summary = current_now - st.session_state.last_summary_time

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.metric("⏱️ Tổng thời gian Bot đã chạy", f"{int(elapsed_from_start // 60)} phút {int(elapsed_from_start % 60)} giây")
with col_t2:
    target_wait = 60 if not st.session_state.is_first_1min_sent else 1800
    st.metric("⏳ Tiến trình đếm ngược gửi báo cáo", f"{int(elapsed_from_last_summary)} / {target_wait} giây")

for target_slug in st.session_state.target_slugs:
    data = get_polymarket_top6_data(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    asset_label = data["label"]
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
        
        flow_type = "🔄 ỔN ĐỊNH NỀN"

        if previous_usd is not None:
            delta_cash = abs(real_usd - previous_usd)
            
            if delta_cash >= WHALE_LIMIT:
                flow_type = "👑 [VIP] CÁ VOI KHỦNG"
                st.markdown(f'<div class="whale-real-alert">👑 PHÁT HIỆN CÁ VOI ĐẠT CHUẨN | Nhánh: {mốc_đấu} | Tiền ròng: ${delta_cash:,.2f}</div>', unsafe_allow_html=True)
                
                last_alert_time = st.session_state.last_whale_alert_v47.get(history_key, 0)
                if current_now - last_alert_time > 20:
                    urgent_msg = (
                        f"👑 *[CÁ VOI KHỦNG PHÁT HIỆN BIẾN ĐỘNG]* 👑\n\n"
                        f"🏆 *Thị trường ({asset_label}):* {title}\n"
                        f"📌 *Mốc:* `{mốc_đấu}`\n"
                        f"💵 *Mức giá:* `{price_cents:.2f}¢`\n"
                        f"💰 *Tiền vào ròng:* *${delta_cash:,.2f}*\n"
                        f"📊 *Tổng vốn vị thế hiện tại:* *${real_usd:,.2f}*"
                    )
                    send_telegram(st.session_state.channel_vip, urgent_msg)
                    st.session_state.last_whale_alert_v47[history_key] = current_now
                    
            elif delta_cash >= (WHALE_LIMIT * 0.4):
                flow_type = "🐟 [NGÁCH] GOM SỚM"
                last_signal = st.session_state.last_signal_time.get(history_key, 0)
                if current_now - last_signal > 30:
                    gom_msg = (
                        f"🐟 *[TÍN HIỆU GOM SỚM / BIẾN ĐỘNG NGÁCH]* 🐟\n\n"
                        f"🏆 *Thị trường ({asset_label}):* {title}\n"
                        f"📌 *Nhánh:* `{mốc_đấu}`\n"
                        f"💵 *Mức giá:* `{price_cents:.2f}¢`\n"
                        f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                        f"📊 *Tổng vốn vị thế hiện tại:* *${real_usd:,.2f}*"
                    )
                    send_telegram(st.session_state.channel_ngach, gom_msg)
                    st.session_state.last_signal_time[history_key] = current_now
                
            elif delta_cash < 5.0:
                flow_type = f"⚪ Nhỏ lẻ (${delta_cash:.2f})"
            else:
                flow_type = f"⚪ Nhỏ lẻ (${delta_cash:.2f})"

        # --- AUTO RISK ENGINE (CHỐT LỜI >90¢ / CẮT LỖ -45%) ---
        if previous_cents is not None and previous_cents != price_cents:
            if price_cents >= 90.0 and previous_cents < 90.0:
                flow_type = "💰 SIÊU LỢI NHUẬN (>90¢)"
                profit_msg = (
                    f"🎯 *[BÁO ĐỘNG ĐẠT MỤC TIÊU: CHỐT LỜI ĐỈNH CAO]* 🎯\n\n"
                    f"🏆 *Thị trường ({asset_label}):* {title}\n"
                    f"📌 *Nhánh:* `{mốc_đấu}`\n"
                    f"🚀 *Trạng thái:* Giá cược bứt phá vượt ngưỡng an toàn **90¢**\n"
                    f"📈 *Giá cũ:* `{previous_cents:.2f}¢` ➡️ *Giá hiện tại:* `{price_cents:.2f}¢`\n"
                    f"💡 *Hành động:* Thực hiện chốt lời!"
                )
                send_telegram(st.session_state.channel_ngach, profit_msg)
            
            drop_ratio = (previous_cents - price_cents) / previous_cents
            if drop_ratio >= 0.45:
                flow_type = "🚨 CẮT LỖ KHẨN CẤP (-45%)"
                loss_msg = (
                    f"⚠️ *[BÁO ĐỘNG RỦI RO: TỰ ĐỘNG CẮT LỖ]* ⚠️\n\n"
                    f"🏆 *Thị trường ({asset_label}):* {title}\n"
                    f"📌 *Nhánh:* `{mốc_đấu}`\n"
                    f"🛑 *Trạng thái:* Phát hiện bước giá sụt giảm sâu đột ngột vượt quá **45%**!\n"
                    f"📉 *Giá chu kỳ trước:* `{previous_cents:.2f}¢` ➡️ *Giá hiện tại:* `{price_cents:.2f}¢` (*Giảm mạnh {drop_ratio*100:.1f}%*)\n"
                    f"💸 *Hành động:* Cân nhắc thoát vị thế cắt lỗ bảo vệ tài khoản!"
                )
                send_telegram(st.session_state.channel_ngach, loss_msg)

        st.session_state.price_history[history_key] = real_usd
        st.session_state.cents_price_history[history_key] = price_cents
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

    # --- TÍCH LŨY DỮ LIỆU TOP 3 BINS CÓ VỐN LỚN NHẤT THỰC TẾ ---
    top3_df = df.sort_values(by="Tổng vốn vị thế ($)", ascending=False).head(3)
    bin_strings = []
    for _, r in top3_df.iterrows():
        bin_strings.append(f"  • Mốc {r['Nhánh Cược (Bin)']}: *{r['Giá (Cents)']:.2f}¢* (Vốn vị thế: `${r['Tổng vốn vị thế ($)']:,.2f}`)")
    
    st.session_state.summary_data_accumulator[title] = {
        "label": asset_label,
        "bins_info": "\n".join(bin_strings)
    }

# --- 🛰️ ĐIỀU KIỆN KÍCH HOẠT THỜI GIAN GỬI TỔNG KẾT (1 PHÚT ĐẦU & 30 PHÚT ĐỀU) ---
trigger_report = False
header_label = ""

if not st.session_state.is_first_1min_sent:
    # 1. KIỂM TRA CHẠY ĐỦ 1 PHÚT (60 GIÂY) ĐẦU TIÊN ĐỂ GỬI TEST NGHIỆM THU
    if current_now - st.session_state.bot_start_time >= 60:
        trigger_report = True
        header_label = "📊 [BÁO CÁO KIỂM TRA NHANH - 1 PHÚT KHỞI CHẠY]"
        st.session_state.is_first_1min_sent = True
else:
    # 2. CÁC CHU KỲ TIẾP THEO SẼ TỰ ĐỘNG ĐẾM ĐỀU ĐẶN ĐÚNG 30 PHÚT (1800 GIÂY)
    if current_now - st.session_state.last_summary_time >= 1800:
        trigger_report = True
        header_label = "📊 [BÁO CÁO TỔNG KẾT ĐỊNH KỲ 30 PHÚT]"

if trigger_report:
    if st.session_state.summary_data_accumulator:
        summary_msg = f"{header_label} 📊\n"
        summary_msg += "====================================\n\n"
        
        # Lấy đầy đủ dữ liệu tích lũy của toàn bộ các thành phố
        for city_title, content in st.session_state.summary_data_accumulator.items():
            summary_msg += f"🏙️ *Thị trường:* {city_title.upper()}\n"
            summary_msg += f"🏷️ *Phân loại:* `{content['label']}`\n"
            summary_msg += f"🔥 *Top 3 Bins Vốn Lớn Nhất Thực Tế:*\n{content['bins_info']}\n"
            summary_msg += "------------------------------------\n\n"
        
        summary_msg += f"🕒 *Thời gian xuất:* {time.strftime('%H:%M:%S', time.localtime(current_now))}"
        
        send_telegram(st.session_state.channel_ngach, summary_msg)
        
        # Cập nhật mốc thời gian để làm căn cứ tính chu kỳ 30 phút tiếp theo
        st.session_state.last_summary_time = current_now
        # Làm sạch hoàn toàn bộ đệm để tích lũy dữ liệu cho chu kỳ mới
        st.session_state.summary_data_accumulator = {}

# Tự động reload trang theo tần suất cài đặt ở Slider
time.sleep(REFRESH_TIME)
st.rerun()
