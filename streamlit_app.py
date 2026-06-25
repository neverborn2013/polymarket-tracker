# worker_radar.py
import json
import time
import urllib.parse
import requests

# --- CẤU HÌNH ENGINE CỐ ĐỊNH ---
TELEGRAM_TOKEN = "8805371373:AAGkYYnNqHPPdFy3kRiOGyT2-ZDyaewaa3M"
CHANNEL_VIP = "-1004312043313"
CHANNEL_NGACH = "-1004377611538"

WHALE_LIMIT = 150.0  # Ngưỡng lọc tiền cá voi ($)
REFRESH_TIME = 8     # Tần suất quét làm mới (giây)
REPORT_INTERVAL = 600 # Chu kỳ gửi báo cáo (10 phút = 600 giây)

RAW_URL_LIST = [
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
]

# Bộ nhớ lưu trữ trạng thái chạy nền
price_history = {}
last_whale_alert = {}
summary_data_accumulator = {}

def extract_slug(url_str):
    try:
        path_parts = [p for p in urllib.parse.urlparse(url_str.strip().rstrip('/')).path.split('/') if p]
        return path_parts[-1]
    except: return None

TARGET_SLUGS = [extract_slug(url) for url in RAW_URL_LIST if extract_slug(url)]

def send_telegram_direct(chat_id_str, message):
    if not TELEGRAM_TOKEN or not chat_id_str: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        chunks = [message[i:i+3500] for i in range(0, len(message), 3500)]
        for idx, chunk in enumerate(chunks):
            final_text = chunk
            if len(chunks) > 1:
                final_text = f" 📊 [Phần {idx+1}/{len(chunks)}]\n" + chunk
            requests.post(url, json={"chat_id": int(chat_id_str), "text": final_text, "parse_mode": "Markdown"}, timeout=8)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def get_polymarket_data(slug):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(f"https://gamma-api.polymarket.com/events?slug={slug}", headers=headers, timeout=10)
        if res.status_code == 200 and res.json():
            event_data = res.json()[0] if isinstance(res.json(), list) else res.json()
            return event_data
    except: return None
    return None

print("🚀 POLYMARKET RADAR BACKEND WORKER ĐANG KHỞI CHẠY KHÔNG NGỪNG...")
bot_start_time = time.time()
last_summary_time = time.time()
is_first_1min_sent = False

while True:
    current_now = time.time()
    elapsed_from_start = current_now - bot_start_time
    elapsed_from_last_summary = current_now - last_summary_time
    
    # Xác định chu kỳ báo cáo tổng kết
    target_wait = 60 if not is_first_1min_sent else REPORT_INTERVAL
    is_near_report = elapsed_from_last_summary >= (target_wait - 10)

    for slug in TARGET_SLUGS:
        event_data = get_polymarket_data(slug)
        if not event_data: continue
        
        market_title = event_data.get("title", "Sự Kiện")
        markets_list = event_data.get("markets", [])
        is_weather = "°c" in market_title.lower() or "temperature" in market_title.lower()
        asset_label = "THỜI TIẾT" if is_weather else "TIN TỨC CỘNG ĐỒNG"
        
        bins_data = []
        for m in markets_list:
            full_title = m.get("title", "")
            group_title = m.get("groupItemTitle", "")
            bin_name = group_title if group_title else (full_title if full_title else market_title)
            
            try:
                price_yes = float(json.loads(m.get("outcomePrices", "[0, 0]"))[0]) * 100
            except: price_yes = 0.0
            
            real_usd_yes = round((float(m.get("liquidity", 0)) / 4 * price_yes) / 100, 2)
            bins_data.append({"name": bin_name, "price": price_yes, "volume": real_usd_yes})
        
        # Sắp xếp lấy Top 6 để theo dõi biến động và Top 3 cho báo cáo tổng kết
        bins_data = sorted(bins_data, key=lambda x: x["volume"], reverse=True)
        
        # Kiểm tra Cá Voi Real-time (Top 6 Bins)
        for b in bins_data[:6]:
            history_key = f"{slug}_{b['name']}_YES"
            previous_usd = price_history.get(history_key, None)
            
            if previous_usd is not None:
                delta_cash = abs(b["volume"] - previous_usd)
                if delta_cash >= WHALE_LIMIT:
                    last_alert = last_whale_alert.get(history_key, 0)
                    if current_now - last_alert > 20:
                        urgent_msg = f"👑 *[CÁ VOI KHỦNG]* 👑\n\n🏆 *Thị trường:* {market_title}\n📌 *Mốc:* `{b['name']}`\n💵 *Giá:* `{b['price']:.2f}¢`\n💰 *Tiền ròng:* *${delta_cash:,.2f}*"
                        send_telegram_direct(CHANNEL_VIP, urgent_msg)
                        last_whale_alert[history_key] = current_now
            
            price_history[history_key] = b["volume"]

        # Gom dữ liệu nếu chuẩn bị xuất báo cáo
        if is_near_report:
            bin_strings = [f"  • Mốc {x['name']}: *{x['price']:.2f}¢* (Vốn: `${x['volume']:,.2f}`)" for x in bins_data[:3]]
            summary_data_accumulator[market_title] = {"label": asset_label, "bins_info": "\n".join(bin_strings)}

    # Kích hoạt bắn báo cáo tổng kết định kỳ
    if elapsed_from_last_summary >= target_wait:
        if summary_data_accumulator:
            header_label = "📊 [BÁO CÁO KIỂM TRA NHANH - 1 PHÚT ĐẦU CHẠY]" if not is_first_1min_sent else "📊 [BÁO CÁO TỔNG KẾT ĐỊNH KỲ 10 PHÚT]"
            summary_msg = f"{header_label} 📊\n====================================\n\n"
            for title, content in summary_data_accumulator.items():
                summary_msg += f"🏙️ *Thị trường:* {title.upper()}\n🏷️ *Phân loại:* `{content['label']}`\n🔥 *Top 3 Bins Vốn Lớn Nhất Thực Tế:*\n{content['bins_info']}\n------------------------------------\n\n"
            summary_msg += f"🕒 *Thời gian xuất vị thế:* {time.strftime('%H:%M:%S')}"
            
            send_telegram_direct(CHANNEL_NGACH, summary_msg)
            if not is_first_1min_sent: is_first_1min_sent = True
            
            last_summary_time = current_now
            summary_data_accumulator = {}

    time.sleep(REFRESH_TIME)
