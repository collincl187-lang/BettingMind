import os
import time
import json
import logging
import asyncio
import argparse
import threading
from datetime import datetime
from pathlib import Path

try:
from dotenv import load_dotenv
load_dotenv()
except Exception:
pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

try:
from sofascore_live_scraper import LiveScanner, ValueBet, MatchStats, POLL_INTERVAL_SECONDS
SCRAPER_AVAILABLE = True
except ImportError:
SCRAPER_AVAILABLE = False

TG_TOKEN = os.getenv(“TG_TOKEN”, “”)
TG_CHAT_ID = os.getenv(“TG_CHAT_ID”, “”)
MIN_EDGE = float(os.getenv(“MIN_EDGE”, “0.05”))
KELLY_FRACTION = float(os.getenv(“KELLY_FRACTION”, “0.25”))
POLL_INTERVAL_SECONDS = int(os.getenv(“POLL_INTERVAL”, “45”))

BANKROLL_FILE = Path(“bankroll.json”)

logging.basicConfig(format=”%(asctime)s [%(levelname)s] %(message)s”, level=logging.INFO)
log = logging.getLogger(**name**)

class BankrollManager:
def **init**(self):
self.data = self._load()

```
def _load(self):
    if BANKROLL_FILE.exists():
        with open(BANKROLL_FILE) as f:
            return json.load(f)
    return {
        "initial": 200.0,
        "current": 200.0,
        "bets": [],
        "stats": {"wins": 0, "losses": 0, "pending": 0, "total_profit": 0.0}
    }

def _save(self):
    with open(BANKROLL_FILE, "w") as f:
        json.dump(self.data, f, indent=2, ensure_ascii=False)

def get_balance(self):
    return self.data["current"]

def add_bet(self, bet_id, market, odds, kelly_pct, match_str):
    stake = round(self.data["current"] * kelly_pct, 2)
    entry = {
        "id": bet_id,
        "match": match_str,
        "market": market,
        "odds": odds,
        "stake": stake,
        "kelly_pct": kelly_pct,
        "status": "pending",
        "placed_at": datetime.now().isoformat(),
        "profit": 0.0
    }
    self.data["bets"].append(entry)
    self.data["stats"]["pending"] += 1
    self._save()
    return stake

def settle_bet(self, bet_id, won):
    for bet in self.data["bets"]:
        if bet["id"] == bet_id and bet["status"] == "pending":
            if won:
                profit = bet["stake"] * (bet["odds"] - 1)
                bet["profit"] = profit
                bet["status"] = "won"
                self.data["current"] += profit
                self.data["stats"]["wins"] += 1
            else:
                bet["profit"] = -bet["stake"]
                bet["status"] = "lost"
                self.data["current"] -= bet["stake"]
                self.data["stats"]["losses"] += 1
            self.data["stats"]["pending"] -= 1
            self.data["stats"]["total_profit"] += bet["profit"]
            self._save()
            return bet
    return None

def get_stats_text(self):
    s = self.data["stats"]
    current = self.data["current"]
    initial = self.data["initial"]
    roi = ((current - initial) / initial) * 100
    total_bets = s["wins"] + s["losses"]
    win_rate = (s["wins"] / total_bets * 100) if total_bets > 0 else 0
    return (
        f"<b>Bankroll: {current:.2f}EUR</b> (Start: {initial:.2f}EUR)\n"
        f"ROI: <b>{roi:+.1f}%</b>\n"
        f"Gewonnen: {s['wins']} | Verloren: {s['losses']} | Offen: {s['pending']}\n"
        f"Trefferquote: {win_rate:.0f}%\n"
        f"Gesamt-Profit: <b>{s['total_profit']:+.2f}EUR</b>"
    )

def get_pending_bets(self):
    return [b for b in self.data["bets"] if b["status"] == "pending"]
```

bankroll = BankrollManager()

def format_value_bet_message(vb):
m = vb.match
stake = round(bankroll.get_balance() * vb.kelly_pct, 2)
return (
f”BETTINGMIND - VALUE BET ALERT\n”
f”—\n”
f”<b>{m.home_team}</b> vs <b>{m.away_team}</b>\n”
f”{m.league} - {m.minute}’\n”
f”Stand: <b>{m.home_score}:{m.away_score}</b>\n\n”
f”Muster: <b>{vb.pattern}</b>\n\n”
f”Markt: <b>{vb.market}</b>\n”
f”—\n”
f”Fair Prob:     <b>{vb.fair_prob:.0%}</b>\n”
f”Break-Even:   <b>@{vb.break_even:.2f}</b>\n”
f”Bookie Quote: <b>@{vb.bookie_odds:.2f}</b>\n”
f”Edge:         <b>+{vb.edge:.1%}</b>\n”
f”—\n”
f”xG: {m.xg_home:.2f} - {m.xg_away:.2f}\n”
f”Momentum: {m.momentum_home:.0f}% - {m.momentum_away:.0f}%\n”
f”Schuesse: {m.shots_on_target_home} - {m.shots_on_target_away}\n”
f”—\n”
f”Konfidenz: <b>{vb.confidence}</b>\n”
f”Empf. Einsatz: <b>{stake:.2f}EUR</b> ({vb.kelly_pct:.1%} Bankroll)\n”
f”Aktuell: {bankroll.get_balance():.2f}EUR”
)

def format_alert_keyboard(bet_id):
return InlineKeyboardMarkup([
[
InlineKeyboardButton(“Bet platziert”, callback_data=f”placed_{bet_id}”),
InlineKeyboardButton(“Skip”, callback_data=f”skip_{bet_id}”),
],
[
InlineKeyboardButton(“Bankroll”, callback_data=“bankroll”),
InlineKeyboardButton(“Offene Bets”, callback_data=“pending”),
]
])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“<b>BettingMind Bot aktiv!</b>\n\n”
“Befehle:\n”
“/bankroll - Kontostand\n”
“/pending  - Offene Wetten\n”
“/history  - Letzte Wetten\n”
“/scan     - Jetzt scannen\n”
“/setbank 200 - Kapital setzen”,
parse_mode=ParseMode.HTML
)

async def cmd_bankroll(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(bankroll.get_stats_text(), parse_mode=ParseMode.HTML)

async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
pending = bankroll.get_pending_bets()
if not pending:
await update.message.reply_text(“Keine offenen Wetten.”)
return
lines = [”<b>Offene Wetten:</b>\n”]
for i, bet in enumerate(pending[-10:], 1):
lines.append(f”{i}. {bet[‘match’]}\n   {bet[‘market’]} @{bet[‘odds’]:.2f} - {bet[‘stake’]:.2f}EUR”)
keyboard = []
for bet in pending[-5:]:
keyboard.append([
InlineKeyboardButton(f”Gewonnen: {bet[‘match’][:15]}”, callback_data=f”won_{bet[‘id’]}”),
InlineKeyboardButton(“Verloren”, callback_data=f”lost_{bet[‘id’]}”),
])
await update.message.reply_text(
“\n”.join(lines),
reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
parse_mode=ParseMode.HTML
)

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
bets = [b for b in bankroll.data[“bets”] if b[“status”] != “pending”]
if not bets:
await update.message.reply_text(“Noch keine abgeschlossenen Wetten.”)
return
recent = bets[-10:][::-1]
lines = [”<b>Letzte Wetten:</b>\n”]
for bet in recent:
icon = “+” if bet[“status”] == “won” else “-”
lines.append(f”{icon} {bet[‘match’]}\n   {bet[‘market’]} @{bet[‘odds’]:.2f} - {bet[‘profit’]:+.2f}EUR”)
await update.message.reply_text(”\n”.join(lines), parse_mode=ParseMode.HTML)

async def cmd_setbank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
try:
amount = float(ctx.args[0])
bankroll.data[“current”] = amount
bankroll.data[“initial”] = amount
bankroll._save()
await update.message.reply_text(
f”Bankroll auf <b>{amount:.2f}EUR</b> gesetzt.”,
parse_mode=ParseMode.HTML
)
except (IndexError, ValueError):
await update.message.reply_text(“Nutzung: /setbank 500”)

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not SCRAPER_AVAILABLE:
await update.message.reply_text(“sofascore_live_scraper.py nicht gefunden.”)
return
msg = await update.message.reply_text(“Scanne SofaScore…”)
try:
scanner = LiveScanner(send_telegram=False)
value_bets = await asyncio.get_event_loop().run_in_executor(None, scanner.scan)
if value_bets:
await msg.edit_text(f”{len(value_bets)} Value Bets gefunden!”)
for vb in value_bets:
await send_value_bet_alert(ctx.bot, vb)
else:
await msg.edit_text(“Scan abgeschlossen - kein Value erkannt.”)
except Exception as e:
await msg.edit_text(f”Fehler: {e}”)

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data

```
if data == "bankroll":
    await query.message.reply_text(bankroll.get_stats_text(), parse_mode=ParseMode.HTML)
elif data == "pending":
    pending = bankroll.get_pending_bets()
    if pending:
        text = f"<b>{len(pending)} offene Wetten</b>\n"
        for b in pending[-5:]:
            text += f"\n- {b['match']}: {b['market']} @{b['odds']:.2f} ({b['stake']:.2f}EUR)"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await query.message.reply_text("Keine offenen Wetten.")
elif data.startswith("placed_"):
    bet_id = data.replace("placed_", "")
    stake = bankroll.add_bet(bet_id, "Value Bet", 2.0, 0.02, "Match")
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Gewonnen", callback_data=f"won_{bet_id}"),
            InlineKeyboardButton("Verloren", callback_data=f"lost_{bet_id}"),
        ]])
    )
    await query.message.reply_text(
        f"<b>Bet gespeichert!</b>\nEinsatz: <b>{stake:.2f}EUR</b>",
        parse_mode=ParseMode.HTML
    )
elif data.startswith("skip_"):
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("Uebersprungen.")
elif data.startswith("won_"):
    bet_id = data.replace("won_", "")
    bet = bankroll.settle_bet(bet_id, won=True)
    if bet:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"<b>GEWONNEN!</b>\n{bet['match']} @{bet['odds']:.2f}\n"
            f"Profit: <b>+{bet['profit']:.2f}EUR</b>\n"
            f"Neue Bankroll: <b>{bankroll.get_balance():.2f}EUR</b>",
            parse_mode=ParseMode.HTML
        )
elif data.startswith("lost_"):
    bet_id = data.replace("lost_", "")
    bet = bankroll.settle_bet(bet_id, won=False)
    if bet:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"<b>Verloren</b>\n{bet['match']} @{bet['odds']:.2f}\n"
            f"Verlust: <b>-{bet['stake']:.2f}EUR</b>\n"
            f"Neue Bankroll: <b>{bankroll.get_balance():.2f}EUR</b>",
            parse_mode=ParseMode.HTML
        )
```

async def send_value_bet_alert(bot: Bot, vb):
if not TG_CHAT_ID:
return
bet_id = f”{vb.match.match_id}_{int(time.time())}”
text = format_value_bet_message(vb)
kb = format_alert_keyboard(bet_id)
try:
await bot.send_message(chat_id=TG_CHAT_ID, text=text, reply_markup=kb, parse_mode=ParseMode.HTML)
except Exception as e:
log.error(f”Telegram Fehler: {e}”)

def scraper_thread_func(loop, bot):
asyncio.set_event_loop(loop)
if not SCRAPER_AVAILABLE:
return
scanner = LiveScanner(send_telegram=False)
seen = set()
while True:
try:
value_bets = scanner.scan()
for vb in value_bets:
key = f”{vb.match.match_id}*{vb.market}*{vb.match.minute // 5}”
if key not in seen:
seen.add(key)
asyncio.run_coroutine_threadsafe(send_value_bet_alert(bot, vb), loop)
except Exception as e:
log.error(f”Scraper Fehler: {e}”)
time.sleep(POLL_INTERVAL_SECONDS)

def main():
parser = argparse.ArgumentParser()
parser.add_argument(”–integrated”, action=“store_true”)
args = parser.parse_args()

```
if not TG_TOKEN:
    print("TG_TOKEN nicht gesetzt!")
    return

print("BettingMind Telegram Bot startet...")

app = Application.builder().token(TG_TOKEN).build()

app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CommandHandler("bankroll", cmd_bankroll))
app.add_handler(CommandHandler("pending", cmd_pending))
app.add_handler(CommandHandler("history", cmd_history))
app.add_handler(CommandHandler("setbank", cmd_setbank))
app.add_handler(CommandHandler("scan", cmd_scan))
app.add_handler(CallbackQueryHandler(callback_handler))

if args.integrated and SCRAPER_AVAILABLE:
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=scraper_thread_func, args=(loop, app.bot), daemon=True)
    t.start()
    print("Scraper-Thread aktiv")

print("Bot laeuft...")
app.run_polling(allowed_updates=Update.ALL_TYPES)
```

if **name** == “**main**”:
main()
