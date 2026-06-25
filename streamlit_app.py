import json
import time
import urllib.parse
import re
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Radar V52.2 Premium", layout="wide")

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

st.title("🚀 POLYMARKET RADAR V52.2 - CHU KỲ BÁO CÁO ĐỊNH KỲ 10 PHÚT")

# --- 💾 KHỞI TẠO BỘ NHỚ ĐỆM TRẠNG THÁI CACHING ---
if "price_history" not in st.session_state:
    st.session_state.price_history = {}
if "cents_price_history" not in st.session_state:
    st.session_state.cents_price_history = {}
if "last_signal_time" not in st.session_state:
    st.session_state.last_signal_time = {}
if "last_whale_alert_v47" not in st.session_state:
    st.session_state.last_whale_alert_v47 = {}

# --- 🕒 LOGIC ĐẾM THỜI GIAN THEO DÕI ---
if "bot_start_time" not in st.session_state:
    st.session_state.bot_start_time = time.time()
if "last_summary_time" not in st.session_state:
    st.session_state.last_summary_time = time.time()
if "is_first_1min_sent" not in st.session_state:
    st.session_state.is_first_1min_sent = False
if "summary_data_accumulator" not in st.session_state:
    st.session_state.summary_data_accumulator = {}
if "last_sent_log" not in st.session_state:
    st.session_state.last_sent_log = "Chưa gửi bản tin nào."

# Cấu hình hệ thống mặc định
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 150  
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"
if "channel_vip" not in st.session_state:
    st.session_state.channel_vip = "-1004312043313"
if "channel_ngach" not in st.session_state:
    st.session_state.channel_ngach = "-1004377611538"

RAW_URL_LIST = """
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-26-2026 
https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-26-2026 
 https://polymarket.com/vi/event/highest-temperature-in-seoul-on-june-26-2026
 https://polymarket.com/vi/event/highest-temperature-in-shanghai-on-june-26-2026 
 https://polymarket.com/vi/event/highest-temperature-in-cape-town-on-june-26-2026
 https://polymarket.com/vi/event/highest-temperature-in-wellington-on-june-26-2026
  https://polymarket.com/vi/event/highest-temperature-in-tel-aviv-on-june-26-2026
 https://polymarket.com/vi/event/highest-temperature-in-london-on-june-25-2026  
   https://polymarket.com/vi/event/highest-temperature-in-paris-on-june-25-2026
    https://polymarket.com/event/highest-temperature-in-madrid-on-june-25-2026
    https://polymarket.com/vi/event/highest-temperature-in-munich-on-june-25-2026  
    https://polymarket.com/vi/event/highest-temperature-in-atlanta-on-june-25-2026 
https://polymarket.com/vi/event/highest-temperature-in-seattle-on-june-25-2026     
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
    st.header("⚙️ Cấu hình Engine V52.2")
    tg_token_input = st.text_input("Telegram Bot Token:", value=st.session_state.tg_token, type="password")
    
    st.write("---")
    st.header("📢 Định tuyến Kênh Telegram")
    id_vip_input = st.text_input("ID Kênh VIP (Cá Voi):", value=st.session_state.channel_vip)
    id_ngach_input = st.text_input("ID Kênh Ngách (Tổng Kết / Gom Sớm):", value=st.session_state.channel_ngach)

    st.write("---")
    st.header("🛡️ Bộ lọc Volume & Quét")
    threshold_input = st.slider("Ngưỡng lọc tiền Cá Voi ($):", 50, 2000, value=st.session_state.whale_threshold, step=50)
    refresh_input = st.slider("Tần suất quét làm mới (giây):", 5, 60, value=st.session_state.refresh_rate)
    
    if st.button("⚡ ĐỒNG BỘ SUITE TOÀN DIỆN V52.2", use_container_width=True):
        st.session_state.whale_threshold = threshold_input
        st.session_state.refresh_rate = refresh_input
        st.session_state.tg_token = tg_token_input
        st.session_state.channel_vip = id_vip_input.strip()
        st.session_state.channel_ngach = id_ngach_input.strip()
        st.toast(f"🔒 Đồng bộ Suite V52.2 thành công!")

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

# --- 🛰️ HÀM GỬI TELEGRAM ĐẢM BẢO CHẶT TIN NHẮN THEO ĐỘ DÀI ---
def send_telegram_direct(chat_id_str, message):
    if not TELEGRAM_TOKEN or not chat_id_str: 
        return "Lỗi: Chưa nhập Token hoặc ID Kênh."
    try:
        chat_id_int = int(chat_id_str.strip())
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        # Chia nhỏ tin nhắn nếu dữ liệu tổng hợp vượt quá giới hạn an toàn 3500 ký tự
        chunks = [message[i:i+3500] for i in range(0, len(message), 3500)]
        
        for idx, chunk in enumerate(chunks):
            final_text = chunk
            if len(chunks) > 1:
                final_text = f" 📊 [Phần {idx+1}/{len(chunks)}]\n" + chunk
                
            payload = {"chat_id": chat_id_int, "text": final_text, "parse_mode": "Markdown"}
            r = requests.post(url, json=payload, timeout=8)
            if r.status_code != 200:
                reason = r.json().get("description", "Không rõ nguyên nhân")
                return f"Telegram API Từ chối ở Phần {idx+1}: {reason} (Code {r.status_code})"
                
        return "OK"
    except ValueError:
        return f"Lỗi: ID Kênh '{chat_id_str}' không hợp lệ!"
    except Exception as e:
        return f"Lỗi kết nối: {str(e)}"

current_now = time.time()
st.write("---")

# --- 📊 ĐIỀU KHIỂN & ĐỒNG HỒ ĐẾM NGƯỢC ---
elapsed_from_start = current_now - st.session_state.bot_start_time
elapsed_from_last_summary = current_now - st.session_state.last_summary_time

# THIẾT LẬP CHU KỲ: Phút đầu tiên chạy test (60s), các chu kỳ sau đổi thành 10 phút (600s)
target_wait = 60 if not st.session_state.is_first_1min_sent else 600

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.metric("⏱️ Tổng thời gian Bot đã chạy", f"{int(elapsed_from_start // 60)} phút {int(elapsed_from_start % 60)} giây")
with col_t2:
    st.metric("⏳ Tiến trình đếm ngược gửi báo cáo (10 Phút / Lần)", f"{int(elapsed_from_last_summary)} / {target_wait} giây")

if "Thành công" in st.session_state.last_sent_log:
    st.success(f"📢 **Trạng thái gửi tin:** {st.session_state.last_sent_log}")
else:
    st.error(f"📢 **Trạng thái gửi tin:** {st.session_state.last_sent_log}")

# --- 🛰️ KIỂM TRA ĐIỀU KIỆN KÍCH HOẠT GỬI BÁO CÁO ---
trigger_report = False
header_label = ""

if not st.session_state.is_first_1min_sent:
    if elapsed_from_start >= 60:
        trigger_report = True
        header_label = "📊 [BÁO CÁO KIỂM TRA NHANH - 1 PHÚT ĐẦU CHẠY]"
        st.session_state.is_first_1min_sent = True
else:
    if elapsed_from_last_summary >= 600:  # Kích hoạt khi đủ 10 phút
        trigger_report = True
        header_label = "📊 [BÁO CÁO TỔNG KẾT ĐỊNH KỲ 10 PHÚT]"

if trigger_report and st.session_state.summary_data_accumulator:
    summary_msg = f"{header_label} 📊\n"
    summary_msg += "====================================\n\n"
    
    for city_title, content in st.session_state.summary_data_accumulator.items():
        summary_msg += f"🏙️ *Thị trường:* {city_title.upper()}\n"
        summary_msg += f"🏷️ *Phân loại:* `{content['label']}`\n"
        summary_msg += f"🔥 *Top 3 Bins Vốn Lớn Nhất Thực Tế:*\n{content['bins_info']}\n"
        summary_msg += "------------------------------------\n\n"
    
    summary_msg += f"🕒 *Thời gian xuất vị thế:* {time.strftime('%H:%M:%S', time.localtime(current_now))}"
    
    result_status = send_telegram_direct(st.session_state.channel_ngach, summary_msg)
    if result_status == "OK":
        st.session_state.last_sent_log = f"Thành công! Gửi bản tin tổng kết lúc {time.strftime('%H:%M:%S')} về kênh {st.session_state.channel_ngach}"
    else:
        st.session_state.last_sent_log = f"Thất bại! Lý do: {result_status}"
        
    st.session_state.last_summary_time = current_now
    st.session_state.summary_data_accumulator = {}
    st.rerun()

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
                
            asset_label = "THỜI TIẾT" if is_weather else "TIN TỨC CỘNG ĐỒNG"
            return {"title": market_title, "df": pd.DataFrame(final_data), "label": asset_label}
        return None
    except: return None

# --- 🔄 VÒNG LẶP QUÉT DATA REAL-TIME ---
# Chỉ gom data vào accumulator khi gần tiến tới mốc thời gian xuất báo cáo (trước 10 giây) để tối ưu hóa hiệu năng
is_near_report = (not st.session_state.is_first_1min_sent and elapsed_from_start >= 50) or (st.session_state.is_first_1min_sent and elapsed_from_last_summary >= 590)

for target_slug in st.session_state.target_slugs:
    data = get_polymarket_top6_data(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    asset_label = data["label"]
    analysis_labels = []
    
    st.markdown(f'<div class="market-header">📡 RADAR GÁC CỔNG [{asset_label}]: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_đấu = row["Nhánh Cược (Bin)"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Tổng vốn vị thế ($)"]
        
        history_key = f"{target_slug}_{mốc_đấu}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        
        flow_type = "🔄 ỔN ĐỊNH NỀN"

        if previous_usd is not None:
            delta_cash = abs(real_usd - previous_usd)
            if delta_cash >= WHALE_LIMIT:
                flow_type = "👑 [VIP] CÁ VOI KHỦNG"
                st.markdown(f'<div class="whale-real-alert">👑 PHÁT HIỆN CÁ VOI | Tiền ròng: ${delta_cash:,.2f}</div>', unsafe_allow_html=True)
                
                last_alert_time = st.session_state.last_whale_alert_v47.get(history_key, 0)
                if current_now - last_alert_time > 20:
                    urgent_msg = f"👑 *[CÁ VOI KHỦNG]* 👑\n\n🏆 *Thị trường:* {title}\n📌 *Mốc:* `{mốc_đấu}`\n💵 *Giá:* `{price_cents:.2f}¢`\n💰 *Tiền ròng:* *${delta_cash:,.2f}*"
                    send_telegram_direct(st.session_state.channel_vip, urgent_msg)
                    st.session_state.last_whale_alert_v47[history_key] = current_now
            else:
                flow_type = f"⚪ Nhỏ lẻ (${delta_cash:.2f})"

        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

    if is_near_report:
        top3_df = df.sort_values(by="Tổng vốn vị thế ($)", ascending=False).head(3)
        bin_strings = []
        for _, r in top3_df.iterrows():
            bin_strings.append(f"  • Mốc {r['Nhánh Cược (Bin)']}: *{r['Giá (Cents)']:.2f}¢* (Vốn: `${r['Tổng vốn vị thế ($)']:,.2f}`)")
        
        st.session_state.summary_data_accumulator[title] = {
            "label": asset_label,
            "bins_info": "\n".join(bin_strings)
        }

time.sleep(REFRESH_TIME)
st.rerun()
