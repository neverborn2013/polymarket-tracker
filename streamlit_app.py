import json
import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Multi-Channel Tracker V36", layout="wide")

# --- 🎨 CSS HIỆU ỨNG GIAO DIỆN ---
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
    .bot-refill-alert {
        padding: 10px;
        border: 1px dashed #7f8c8d;
        border-radius: 8px;
        font-size: 14px;
        text-align: center;
        margin-bottom: 10px;
        background-color: #f8f9fa;
        color: #7f8c8d;
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

st.title("🔥 POLYMARKET TRACKER V36 - MULTI-CHANNEL ROUTING")

# --- 🔐 KHỞI TẠO TRẠNG THÁI HỆ THỐNG ---
if "last_whale_alert_v36" not in st.session_state:
    st.session_state.last_whale_alert_v36 = {}
if "price_history" not in st.session_state:
    st.session_state.price_history = {}

# Sẵn sàng cấu hình mặc định cho 4 thành phố/kèo mẫu cùng lúc
default_cities = [
    "highest-temperature-in-tokyo-on-june-22-2026",
    "highest-temperature-in-singapore-on-june-23-2026",
    "highest-temperature-in-new-york-on-june-22-2026",
    "highest-temperature-in-madrid-on-june-23-2026"
]

default_routing = {
    "tokyo": "-1004312043313",
    "singapore": "-1004377611538",
    "new-york": "-1004317098765",
    "madrid": "-1004299539957",
    "default": "-1004312043313"
}

if "city_slugs" not in st.session_state:
    st.session_state.city_slugs = default_cities
if "whale_threshold" not in st.session_state:
    st.session_state.whale_threshold = 50
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"
if "channel_routing" not in st.session_state:
    st.session_state.channel_routing = default_routing

# --- 🛠️ SIDEBAR: CẤU HÌNH ĐƯỜNG TRUYỀN ---
with st.sidebar:
    with st.form(key="config_form"):
        st.header("🔌 Kết Nối Telegram Bot")
        tg_token_input = st.text_input("Telegram Bot Token:", value=st.session_state.tg_token, type="password")

        st.write("---")
        st.header("📁 PHÂN CHIA CHAT ID RIÊNG BIỆT")
        st.write("_Nhập ID phòng chat riêng (Để trống sẽ tự động dùng kênh dự phòng):_")
        id_tokyo = st.text_input("ID Kênh Tokyo:", value=st.session_state.channel_routing.get("tokyo", ""))
        id_sing = st.text_input("ID Kênh Singapore:", value=st.session_state.channel_routing.get("singapore", ""))
        id_ny = st.text_input("ID Kênh New York:", value=st.session_state.channel_routing.get("new-york", ""))
        id_london = st.text_input("ID Kênh London:", value=st.session_state.channel_routing.get("london", ""))
        id_def = st.text_input("ID Kênh Khác (Dự phòng):", value=st.session_state.channel_routing.get("default", ""))

        st.write("---")
        st.header("🛡️ Bộ lọc & Tốc độ")
        threshold_input = st.slider("Chỉ báo nếu Tiền biến động > ($):", 10, 2000, value=st.session_state.whale_threshold, step=10)
        refresh_input = st.slider("Tốc độ quét vòng lặp (giây):", 5, 60, value=st.session_state.refresh_rate)
        
        submit_button = st.form_submit_button(label="💾 LƯU CẤU HÌNH PHÂN KÊNH", use_container_width=True)
        
        if submit_button:
            st.session_state.whale_threshold = threshold_input
            st.session_state.refresh_rate = refresh_input
            st.session_state.tg_token = tg_token_input
            
            # GIẢI PHÁP SỬA LỖI: Điền an toàn (or "") chống gãy lỗi sập hệ thống khi ô nhập rỗng
            st.session_state.channel_routing = {
                "tokyo": (id_tokyo or "").strip(),
                "singapore": (id_sing or "").strip(),
                "new-york": (id_ny or "").strip(),
                "london": (id_london or "").strip(),
                "default": (id_def or "").strip()
            }
            st.toast("✅ Đã cập nhật và sửa lỗi định tuyến an toàn thành công!")

TELEGRAM_TOKEN = st.session_state.tg_token
whale_threshold_usd = st.session_state.whale_threshold
refresh_rate = st.session_state.refresh_rate

# --- 📝 KHU VỰC NHẬP LINK ĐỒNG THỜI (HỖ TRỢ 4 LINK TRỞ LÊN) ---
st.subheader("📋 Nhập danh sách 4 URL/Slug Polymarket chạy song song:")
cities_text = st.text_area(
    "Dán các đường dẫn vào đây (Mỗi dòng là một thành phố riêng biệt):", 
    value="\n".join([f"https://polymarket.com/event/{s}" for s in st.session_state.city_slugs]),
    height=150  # Tăng chiều cao để nhìn rõ 4 dòng
)

def extract_slug(url_str):
    try:
        cleaned_url = url_str.strip().rstrip('/')
        if not cleaned_url: return None
        parsed = urllib.parse.urlparse(cleaned_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if "event" in path_parts or "market" in path_parts: return path_parts[-1]
        return path_parts[-1]
    except: return None

# Bóc tách danh sách link người dùng dán vào
current_input_slugs = []
for line in cities_text.split("\n"):
    slug = extract_slug(line)
    if slug: current_input_slugs.append(slug)

if current_input_slugs and current_input_slugs != st.session_state.city_slugs:
    st.session_state.city_slugs = current_input_slugs
    st.toast("🔄 Đã ghi nhận danh sách 4 mốc thị trường mới!")

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
                    price_no = float(prices_arr[1]) * 100
                except: price_yes, price_no = 0.0, 0.0

                liquidity = float(m.get("liquidity", 0))
                est_volume = round(liquidity / 4, 2)

                raw_bins.append({
                    "Base_Name": base_name,
                    "YES_Price": price_yes,
                    "NO_Price": price_no,
                    "Volume": est_volume
                })
            
            df_raw = pd.DataFrame(raw_bins)
            hot_zones = df_raw.sort_values(by="Volume", ascending=False).head(3)

            final_data = []
            for _, row in hot_zones.iterrows():
                real_usd_yes = round((row['Volume'] * row['YES_Price']) / 100, 2)
                real_usd_no = round((row['Volume'] * row['NO_Price']) / 100, 2)

                final_data.append({"Bin": row['Base_Name'], "Side": "YES", "Giá (Cents)": round(row['YES_Price'], 2), "Giá trị lệnh thực ($)": real_usd_yes})
                final_data.append({"Bin": row['Base_Name'], "Side": "NO", "Giá (Cents)": round(row['NO_Price'], 2), "Giá trị lệnh thực ($)": real_usd_no})
                
            return {"title": market_title, "df": pd.DataFrame(final_data)}
        return None
    except: return None

# --- 🚀 HÀM TỰ ĐỘNG CHIA TIN NHẮN VỀ ĐÚNG KÊNH ---
def send_telegram_by_routing(slug, message):
    if not TELEGRAM_TOKEN: return
    
    # Mặc định chọn kênh dự phòng
    target_chat_id = st.session_state.channel_routing.get("default", "")
    slug_lower = slug.lower()
    
    # Kiểm tra từ khóa trong slug để điều hướng trúng đích
    if "tokyo" in slug_lower:
        target_chat_id = st.session_state.channel_routing.get("tokyo", target_chat_id)
    elif "singapore" in slug_lower:
        target_chat_id = st.session_state.channel_routing.get("singapore", target_chat_id)
    elif "new-york" in slug_lower or "nyc" in slug_lower:
        target_chat_id = st.session_state.channel_routing.get("new-york", target_chat_id)
    elif "london" in slug_lower:
        target_chat_id = st.session_state.channel_routing.get("london", target_chat_id)
        
    if not target_chat_id or not str(target_chat_id).strip(): return
    try: 
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": str(target_chat_id).strip(), "text": message, "parse_mode": "Markdown"}, 
                      timeout=5)
    except: 
        pass

# --- VÒNG LẶP QUÉT XOAY VÒNG 4 THÀNH PHỐ ---
current_now = time.time()
st.write("---")

for target_slug in st.session_state.city_slugs:
    data = get_polymarket_hot_zones(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    analysis_labels = []
    
    st.markdown(f'<div class="city-header">🏙️ ĐANG QUÉT: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_nhiệt = row["Bin"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Giá trị lệnh thực ($)"]
        
        history_key = f"{target_slug}_{mốc_nhiệt}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        
        flow_type = "⚪ Nhỏ lẻ"

        if real_usd >= whale_threshold_usd:
            # Nếu chênh lệch dòng tiền tĩnh dưới $5 -> Nhãn Bot giữ sàn
            if previous_usd is not None and abs(real_usd - previous_usd) <= 5.0:
                flow_type = "🤖 BOT REFILL"
            else:
                # Nếu có lệnh mới làm biến động trên $5 -> Người thật mua/bán
                flow_type = "🔥 CÓ NGƯỜI MUA"
                st.markdown(f'<div class="whale-real-alert">🟢 KHỚP LỆNH MỚI THỰC TẾ 🟢 Mốc: {mốc_nhiệt} ({hướng_cược}) | Số tiền: ${real_usd:,.2f}</div>', unsafe_allow_html=True)
                
                last_alert_time = st.session_state.last_whale_alert_v36.get(history_key, 0)
                if current_now - last_alert_time > 10:
                    side_icon = "🟢 MUA ĐỒNG Ý (YES)" if hướng_cược == "YES" else "🔴 MUA PHẢN ĐỐI (NO)"
                    
                    urgent_msg = (
                        f"📊 *BÁO ĐỘNG BIẾN ĐỘNG THỊ TRƯỜNG THỰC TẾ* 📊\n\n"
                        f"🏙️ *Thành phố:* {title}\n"
                        f"📌 *Vị thế mốc:* `{mốc_nhiệt}`\n"
                        f"🎯 *Hành động:* *{side_icon}*\n"
                        f"💵 *Mức giá:* `{price_cents}¢`\n"
                        f"💰 *Tổng tiền cửa hiện tại:* *${real_usd:,.2f}*\n"
                        f"📬 _Hệ thống: Đã chuyển phát tin nhắn này về nhóm chuyên biệt thành công._"
                    )
                    # Thực hiện phân luồng gửi về đúng kênh Telegram riêng
                    send_telegram_by_routing(target_slug, urgent_msg)
                    st.session_state.last_whale_alert_v36[history_key] = current_now
        
        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

st.info(f"⚙️ Radar V36 đang quét chu kỳ xoay vòng liên tục sau mỗi {refresh_rate} giây.")
time.sleep(refresh_rate)
st.rerun()
