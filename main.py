import os
import pandas as pd
import yfinance as yf
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Konfigurasi ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Daftar saham IDX
TICKERS = ["BBCA.JK", "TLKM.JK", "ADRO.JK", "UNTR.JK", "ASII.JK", "BBRI.JK", "BMRI.JK", "GOTO.JK", "BBCA.JK", "KEEN.JK"]


def get_stock_data():
    data = []
    for t in TICKERS:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="5d")
            if len(hist) < 2:
                continue
            price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[0]
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close != 0 else 0

            info = stock.info
            data.append({
                "symbol": t.replace(".JK", ""),
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "pe": round(info.get("trailingPE", 0), 1),
                "roe": round(info.get("returnOnEquity", 0), 3),
            })
        except Exception as e:
            logger.warning(f"Gagal proses {t}: {e}")
            continue
    return pd.DataFrame(data)


def generate_report():
    df = get_stock_data()
    if df.empty:
        return "⚠️ Tidak ada data saham hari ini. Coba lagi besok."

    # Filter: PE < 20 & ROE > 0.10
    candidates = df[(df["pe"] < 20) & (df["roe"] > 0.10)].copy()
    candidates = candidates.sort_values("change_pct", ascending=False)

    if candidates.empty:
        return "🔍 Tidak ada saham yang memenuhi kriteria hari ini:\n• PE < 20\n• ROE > 10%"

    msg = "📈 <b>Signal Saham IDX — Screening Harian</b>\n\n"
    msg += "✅ Saham memenuhi kriteria (PE &gt; 20 &amp; ROE &gt; 10%):\n"
    for _, r in candidates.iterrows():
        msg += f"• <b>{r['symbol']}</b>: Rp{r['price']} (<code>{r['change_pct']}%</code>) | PE {r['pe']} | ROE {r['roe']:.1%}\n"
    msg += "\nℹ️ Data delayed 15 menit. Untuk keputusan trading, gunakan platform resmi."
    return msg


async def send_report():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("TELEGRAM_TOKEN atau CHAT_ID belum diset.")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=generate_report(), parse_mode="HTML")
        logger.info("✅ Laporan dikirim ke Telegram.")
    except TelegramError as e:
        logger.error(f"❌ Gagal kirim ke Telegram: {e}")
    except Exception as e:
        logger.error(f"❌ Error tak terduga: {e}")


if __name__ == "__main__":
    asyncio.run(send_report())
