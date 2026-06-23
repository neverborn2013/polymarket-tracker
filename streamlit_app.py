import json
import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Polymarket Radar V48.6 Hybrid", layout="wide")

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
        background-color: #1a252f;
        color: #f39c12;
        padding: 10px 15px;
        border-radius: 6px;
        margin-top: 18px;
        margin-bottom: 8px;
        font-weight: bold;
        font-size: 14px;
        border-left: 5px solid #9b59b6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ POLYMARKET RADAR V48.6 - LOGIC GÁC CỔNG LAI (HYBRID STOP-LOSS)")

# Khởi tạo bộ nhớ đệm hệ thống
if "last_whale_alert_v47" not in st.session_state:
    st.session_state.last_whale_alert_v47 = {}
if "price_history" not in st.session_state:
    st.session_state.price_history = {}
if "cents_price_history" not in st.session_state:
    st.session_state.cents_price_history = {}
if "entry_price_history" not in st.session_state:
    st.session_state.entry_price_history = {}  # 🔥 Lưu mức giá tại thời điểm phát tin Tele làm mốc gốc
if "last_signal_time" not in st.session_state:
    st.session_state.last_signal_time = {}
if "reported_tele_keys" not in st.session_state:
    st.session_state.reported_tele_keys = []

RAW_URL_LIST = """
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-24-2026 
  https://polymarket.com/event/highest-temperature-in-madrid-on-june-24-2026
  https://polymarket.com/event/highest-temperature-in-singapore-on-june-24-2026  
 https://polymarket.com/event/highest-temperature-in-new-york-on-june-24-2026 
  https://polymarket.com/vi/event/highest-temperature-in-london-on-june-24-2026   
 https://polymarket.com/vi/event/highest-temperature-in-hong-kong-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-seoul-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-taipei-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-beijing-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-chongqing-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-wuhan-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-lucknow-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-qingdao-on-june-24-2026
  https://polymarket.com/vi/event/highest-temperature-in-shanghai-on-june-24-2026 
  https://polymarket.com/vi/event/highest-temperature-in-shenzhen-on-june-24-2026 
  https://polymarket.com/vi/event/highest-temperature-in-chengdu-on-june-24-2026  
 https://polymarket.com/vi/event/highest-temperature-in-guangzhou-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-kuala-lumpur-on-june-24-2026  
 https://polymarket.com/vi/event/highest-temperature-in-manila-on-june-24-2026  
  https://polymarket.com/vi/event/highest-temperature-in-busan-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-karachi-on-june-24-20226 
 https://polymarket.com/vi/event/highest-temperature-in-cape-town-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-tel-aviv-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-wellington-on-june-24-2026  
 https://polymarket.com/vi/event/highest-temperature-in-paris-on-june-24-2026
https://polymarket.com/vi/event/highest-temperature-in-munich-on-june-24-2026   
 https://polymarket.com/vi/event/highest-temperature-in-istanbul-on-june-24-2026 
  https://polymarket.com/vi/event/highest-temperature-in-ankara-on-june-24-2026    
https://polymarket.com/vi/event/highest-temperature-in-warsaw-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-helsinki-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-amsterdam-on-june-24-20226
 https://polymarket.com/vi/event/highest-temperature-in-moscow-on-june-24-2026
 https://polymarket.com/vi/event/highest-temperature-in-nyc-on-june-24-2026   
 https://polymarket.com/vi/event/highest-temperature-in-atlanta-on-june-24-2026  
 https://polymarket.com/vi/event/highest-temperature-in-chicago-on-june-24-2026   
 https://polymarket.com/vi/event/highest-temperature-in-houston-on-june-24-2026   
 https://polymarket.com/vi/event/highest-temperature-in-miami-on-june-24-2026   
https://polymarket.com/vi/event/highest-temperature-in-los-angeles-on-june-24-2026 
 https://polymarket.com/vi/event/highest-temperature-in-san-francisco-on-june-24-2026    
https://polymarket.com/vi/event/highest-temperature-in-seattle-on-june-24-2026   
https://polymarket.com/vi/event/highest-temperature-in-denver-on-june-24-2026    
https://polymarket.com/vi/event/highest-temperature-in-dallas-on-june-24-2026  
 https://polymarket.com/vi/event/highest-temperature-in-austin-on-june-24-202   
https://polymarket.com/vi/event/highest-temperature-in-toronto-on-june-24-2026 
https://polymarket.com/vi/sports/world-cup/fifwc-arg-aut-2026-06-22
https://polymarket.com/vi/sports/world-cup/fifwc-fra-irq-2026-06-22
https://polymarket.com/vi/sports/world-cup/fifwc-nor-sen-2026-06-22
https://polymarket.com/vi/sports/world-cup/fifwc-jor-alg-2026-06-22
https://polymarket.com/vi/sports/world-cup/fifwc-prt-uzb-2026-06-23
https://polymarket.com/vi/sports/world-cup/fifwc-eng-gha-2026-06-23
https://polymarket.com/vi/sports/world-cup/fifwc-pan-hrv-2026-06-23
https://polymarket.com/vi/sports/world-cup/fifwc-col-cdr-2026-06-23
https://polymarket.com/vi/esports/valorant/vcl/val-ucam-pl-2026-06-22
https://polymarket.com/vi/esports/cs2/united21/cs2-cls1-mil-2026-06-23
https://polymarket.com/vi/esports/valorant/vcl/val-ep1-bar-2026-06-22
https://polymarket.com/vi/esports/cs2/draculan/cs2-sashi-9ine-2026-06-23
https://polymarket.com/vi/sports/atp/atp-collign-cerund-2026-06-22
https://polymarket.com/vi/sports/mlb/mlb-tex-mia-2026-06-22
https://polymarket.com/event/bitcoin-above-105k-on-june-26-2026
https://polymarket.com/event/ethereum-above-4200-on-june-26-2026
https://polymarket.com/event/us-gdp-q1-2026-final-reading
https://polymarket.com/event/solana-ath-in-june-2026
https://polymarket.com/vi/esports/dota-2/the-international/dota2-rnx-grind-2026-06-23
https://polymarket.com/vi/event/what-price-will-bitcoin-hit-june-22-28-2026
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
https://polymarket.com/event/euro-2026-winner
https://polymarket.com/event/copa-america-2026-winner
https://polymarket.com/event/nba-championship-2026
https://polymarket.com/event/presidential-election-2026
https://polymarket.com/event/republican-nominee-2026
https://polymarket.com/event/democratic-nominee-2026
https://polymarket.com/event/us-initial-jobless-claims-june-25-2026
https://polymarket.com/event/highest-temperature-in-tokyo-on-june-24-2026
https://polymarket.com/event/highest-temperature-in-madrid-on-june-24-2026
https://polymarket.com/event/highest-temperature-in-new-york-on-june-24-2026
https://polymarket.com/event/bitcoin-above-105k-on-june-26-2026
https://polymarket.com/event/ethereum-above-4200-on-june-26-2026
https://polymarket.com/event/solana-above-210-on-june-26-2026
https://polymarket.com/vi/event/what-price-will-ethereum-hit-on-june-24
https://polymarket.com/vi/event/what-price-will-bitcoin-hit-on-june-24
https://polymarket.com/vi/event/what-price-will-xrp-hit-on-june-24
https://polymarket.com/vi/sports/wta/wta-sonmez-dart-2026-06-23
https://polymarket.com/vi/sports/wta/wta-krueger-knutson-2026-06-23
https://polymarket.com/vi/sports/wta/wta-bejlek-siegemu-2026-06-22
https://polymarket.com/vi/sports/wta/wta-sonmez-dart-2026-06-23
https://polymarket.com/vi/sports/mlb/mlb-bos-col-2026-06-23
https://polymarket.com/vi/event/elon-musk-of-tweets-june-19-june-26
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
    st.session_state.whale_threshold = 2000  
if "refresh_rate" not in st.session_state:
    st.session_state.refresh_rate = 8
if "tg_token" not in st.session_state:
    st.session_state.tg_token = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"

if "channel_vip" not in st.session_state:
    st.session_state.channel_vip = "-1004312043313"
if "channel_ngach" not in st.session_state:
    st.session_state.channel_ngach = "-1004377611538"

with st.sidebar:
    with st.form(key="config_form_v48_6"):
        st.header("🔌 Cấu hình Hệ thống V48.6")
        tg_token_input = st.text_input("Bot Token chung:", value=st.session_state.tg_token, type="password")
        
        st.write("---")
        st.header("📢 Định tuyến Kênh")
        id_vip_input = st.text_input("ID Kênh VIP (Lệnh Lớn):", value=st.session_state.channel_vip)
        id_ngach_input = st.text_input("ID Kênh Ngách (Gom Sớm):", value=st.session_state.channel_ngach)

        st.write("---")
        st.header("🛡️ Bộ lọc")
        threshold_input = st.slider("Ngưỡng Cá Mập ($):", 1000, 5000, value=st.session_state.whale_threshold, step=100)
        refresh_input = st.slider("Tốc độ quét (giây):", 5, 60, value=st.session_state.refresh_rate)
        
        submit_button = st.form_submit_button(label="🚀 ĐỒNG BỘ LOGIC HYBRID", use_container_width=True)
        
        if submit_button:
            st.session_state.whale_threshold = threshold_input
            st.session_state.refresh_rate = refresh_input
            st.session_state.tg_token = tg_token_input
            st.session_state.channel_vip = id_vip_input.strip()
            st.session_state.channel_ngach = id_ngach_input.strip()
            st.toast("✅ Đã kích hoạt luật cắt lỗ linh hoạt cửa trên/cửa dưới!")

TELEGRAM_TOKEN = st.session_state.tg_token
whale_threshold_usd = st.session_state.whale_threshold
refresh_rate = st.session_state.refresh_rate

st.subheader(f"📋 Radar đang bảo vệ {len(st.session_state.city_slugs)} thị trường chủ lực:")
cities_text = st.text_area(
    "Đường dẫn sự kiện nâng cao:", 
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
                full_title = m.get("title", "")
                group_title = m.get("groupItemTitle", "")
                base_name = f"{full_title} ({group_title})" if group_title else (full_title if full_title else market_title)
                
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

def send_telegram(chat_id, message):
    if not TELEGRAM_TOKEN or not chat_id: return
    try: 
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, 
                      timeout=5)
    except: pass

current_now = time.time()
st.write("---")

for target_slug in st.session_state.city_slugs:
    data = get_polymarket_hot_zones(target_slug)
    if data is None: continue
        
    title = data["title"]
    df = data["df"]
    analysis_labels = []
    
    st.markdown(f'<div class="city-header">🛡️ GÁC CỔNG THỊ TRƯỜNG: {title.upper()}</div>', unsafe_allow_html=True)
    
    for _, row in df.iterrows():
        mốc_đấu = row["Bin"]
        hướng_cược = row["Side"]
        price_cents = row["Giá (Cents)"]
        real_usd = row["Giá trị lệnh thực ($)"]
        
        history_key = f"{target_slug}_{mốc_đấu}_{hướng_cược}"
        previous_usd = st.session_state.price_history.get(history_key, None)
        previous_cents = st.session_state.cents_price_history.get(history_key, None)
        
        flow_type = "⚪ Nhỏ lẻ"

        # --- 🛡️ THUẬT TOÁN GÁC CỔNG LAI HYBRID V48.6 ---
        if previous_cents is not None:
            if 1.0 < price_cents < 99.0 and 1.0 < previous_cents < 99.0:
                
                # Kiểm tra xem kèo này có nằm trong danh mục ĐÃ BÁO TELEGRAM không
                if history_key in st.session_state.reported_tele_keys:
                    
                    # Lấy giá gốc lúc phát tin ra để làm điểm neo tính toán phần trăm
                    entry_price = st.session_state.entry_price_history.get(history_key, previous_cents)
                    
                    last_sig_time = st.session_state.last_signal_time.get(history_key, 0)
                    allow_send_signal = (current_now - last_sig_time) > 120 # Khóa chống trùng tin 2 phút
                    
                    # 1. TÍN HIỆU CHỐT LỜI (Khi giá bứt phá vượt mốc tâm lý 50¢)
                    if previous_cents < 50.0 <= price_cents:
                        if allow_send_signal:
                            alert_tp = (
                                f"💰 *[CẢNH BÁO: CHỐT LỜI TRONG NGÀY]* 💰\n\n"
                                f"🏆 *Thị trường:* {title}\n"
                                f"📌 *Nhánh cược mục tiêu:* `{mốc_đấu}`\n"
                                f"📈 *Biến động:* Giá từ `{previous_cents}¢` ➡️ bứt phá vượt mốc `{price_cents}¢`\n"
                                f"🔔 *Hành động:* Vị thế theo dòng tiền đã đạt lợi nhuận tốt, cân nhắc bấm SELL!"
                            )
                            send_telegram(st.session_state.channel_vip, alert_tp)
                            send_telegram(st.session_state.channel_ngach, alert_tp)
                            st.session_state.last_signal_time[history_key] = current_now

                    # 2. TÍN HIỆU CẮT LỖ KHẨN CẤP (Áp dụng bộ luật phân mảnh thông minh)
                    is_trigger_sl = False
                    reason_sl = ""
                    
                    # Phân khúc A: Giá lúc gom thuộc Cửa Trên (> 50¢) -> Giữ nguyên quy tắc sụt 10 giá
                    if entry_price > 50.0:
                        if previous_cents > price_cents and (previous_cents - price_cents) >= 10.0:
                            is_trigger_sl = True
                            reason_sl = f"Cửa trên gãy xu hướng (Sụt giảm -{previous_cents - price_cents:.1f} giá so với chu kỳ trước)"
                    
                    # Phân khúc B: Giá lúc gom thuộc Cửa Dưới (< 30¢) -> Cho không gian thở, chỉ cắt khi giảm 45% giá trị gốc
                    elif entry_price < 30.0:
                        drop_percent = ((entry_price - price_cents) / entry_price) * 100
                        if drop_percent >= 45.0:
                            is_trigger_sl = True
                            reason_sl = f"Cửa dưới vỡ trận phòng thủ (Đã sập -{drop_percent:.1f}% từ giá gốc {entry_price}¢ về {price_cents}¢)"
                    
                    # Phân khúc C: Vùng trung dung (Từ 30¢ đến 50¢) -> Cắt lỗ khi giảm 10 giá
                    else:
                        if previous_cents > price_cents and (previous_cents - price_cents) >= 10.0:
                            is_trigger_sl = True
                            reason_sl = f"Vùng trung dung sụt sâu (Giảm -{previous_cents - price_cents:.1f} giá)"

                    # Tiến hành bắn tin khẩn cấp nếu vi phạm luật an toàn danh mục
                    if is_trigger_sl and allow_send_signal:
                        alert_sl = (
                            f"⚠️ *[CẢNH BÁO: CẮT LỖ KHẨN CẤP V48.6]* ⚠️\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Nhánh cược mục tiêu:* `{mốc_đấu}`\n"
                            f"📉 *Trạng thái:* {reason_sl}\n"
                            f"💵 *Mức giá hiện tại:* `{price_cents}¢` (Giá neo gốc: `{entry_price}¢`)\n"
                            f"🚨 *Hành động:* Diễn biến thị trường đã vi phạm chốt chặn an toàn, hãy kiểm tra ngay vị thế!"
                        )
                        send_telegram(st.session_state.channel_vip, alert_sl)
                        send_telegram(st.session_state.channel_ngach, alert_sl)
                        st.session_state.last_signal_time[history_key] = current_now

        st.session_state.cents_price_history[history_key] = price_cents

        # --- 💰 QUÉT DÒNG TIỀN VÀ KHÓA MỐC GIÁ GỐC ĐỂ CẮT LỖ ---
        if previous_usd is None:
            flow_type = "🔄 KHỞI TẠO NỀN (BỎ QUA)"
        else:
            delta_cash = abs(real_usd - previous_usd)
            cent_part = round(real_usd - int(real_usd), 2)
            
            is_price_too_high_or_low = price_cents > 93.0 or price_cents < 4.0
            is_invalid_delta = delta_cash < 350.0 or delta_cash > 35000.0
            is_bot_pattern = cent_part not in [0.0, 0.5] or is_invalid_delta or is_price_too_high_or_low
            
            if is_bot_pattern:
                if is_price_too_high_or_low and delta_cash >= 350.0:
                    flow_type = "🤖 BOT TẤT TOÁN SÀN (ĐÃ CHẶN)"
                else:
                    flow_type = "🤖 BOT MARKET MAKER (ĐÃ KHÓA)"
            else:
                last_alert_time = st.session_state.last_whale_alert_v47.get(history_key, 0)
                
                # Phân loại 1: Cá Voi Khủng VIP
                if delta_cash >= whale_threshold_usd:
                    flow_type = "👑 [VIP] CÁ VOI KHỦNG"
                    st.markdown(f'<div class="whale-real-alert">👑 CÁ VOI VIP GOM HÀNG KHỦNG 👑 Vị thế: {mốc_đấu} | Tiền ròng: ${delta_cash:,.2f}</div>', unsafe_allow_html=True)
                    
                    if current_now - last_alert_time > 20:
                        urgent_msg = (
                            f"👑 *[CÁ VOI KHỦNG VIP] BÁO CÁO DÒNG TIỀN V48.6* 👑\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Chi tiết nhánh cược:* `{mốc_đấu}`\n"
                            f"🎯 *Hành động:* *🟢 MUA ĐỒNG Ý (YES)*\n"
                            f"💵 *Mức giá gom hợp lý:* `{price_cents}¢`\n"
                            f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                            f"📊 *Tổng vốn vị thế:* `${real_usd:,.2f}`"
                        )
                        send_telegram(st.session_state.channel_vip, urgent_msg)
                        st.session_state.last_whale_alert_v47[history_key] = current_now
                        
                        # 🎯 Ghi nhận vào bộ nhớ gác cổng và KHÓA mốc giá gốc
                        if history_key not in st.session_state.reported_tele_keys:
                            st.session_state.reported_tele_keys.append(history_key)
                            st.session_state.entry_price_history[history_key] = price_cents
                        
                # Phân loại 2: Gom Sớm Ngách
                elif delta_cash >= 400.0:
                    flow_type = "🐟 [NGÁCH] TÍN HIỆU GOM SỚM"
                    if current_now - last_alert_time > 20:
                        ngach_msg = (
                            f"🐟 *[TÍN HIỆU GOM SỚM] BÁO CÁO DÒNG TIỀN V48.6* 🐟\n\n"
                            f"🏆 *Thị trường:* {title}\n"
                            f"📌 *Chi tiết nhánh cược:* `{mốc_đấu}`\n"
                            f"🎯 *Hành động:* *🟢 MUA ĐỒNG Ý (YES)*\n"
                            f"💵 *Mức giá gom hợp lý:* `{price_cents}¢`\n"
                            f"💰 *Lượng tiền vào ròng:* *${delta_cash:,.2f}*\n"
                            f"📊 *Tổng vốn vị thế:* `${real_usd:,.2f}`"
                        )
                        send_telegram(st.session_state.channel_ngach, ngach_msg)
                        st.session_state.last_whale_alert_v47[history_key] = current_now
                        
                        # 🎯 Ghi nhận vào bộ nhớ gác cổng và KHÓA mốc giá gốc
                        if history_key not in st.session_state.reported_tele_keys:
                            st.session_state.reported_tele_keys.append(history_key)
                            st.session_state.entry_price_history[history_key] = price_cents
                else:
                    flow_type = f"⚪ Nhỏ lẻ quá bé (${delta_cash:.2f})"
        
        st.session_state.price_history[history_key] = real_usd
        analysis_labels.append(flow_type)

    df["Phân Loại Dòng Tiền"] = analysis_labels
    st.dataframe(df, width="stretch", hide_index=True)

# Hiển thị trạng thái bộ gác cổng lai thông minh
st.info(f"⚙️ Bản V48.6 Hybrid: Đang bảo vệ {len(st.session_state.reported_tele_keys)} kèo chiến lược bằng cơ chế cắt lỗ phân tầng Độc quyền.")
time.sleep(refresh_rate)
st.rerun()
