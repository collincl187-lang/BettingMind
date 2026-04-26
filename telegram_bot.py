“””
╔══════════════════════════════════════════════════════════════════╗
║         BETTINGMIND – Telegram Alert Bot v1.0                   ║
║         Live Value Bet Alerts | Inline Buttons | Bankroll Log   ║
╚══════════════════════════════════════════════════════════════════╝

Setup:

1. Bot erstellen: @BotFather auf Telegram → /newbot
1. Token kopieren → TG_TOKEN=… in .env
1. Chat-ID holen: Bot anschreiben, dann:
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   → “chat”:{“id”: DEINE_ID}
1. pip install python-telegram-bot requests python-dotenv

Nutzung:
python telegram_bot.py              # Bot starten (blockiert)

Dann im Terminal parallel:
python sofascore_live_scraper.py –loop –tg

ODER alles-in-einem:
python telegram_bot.py –integrated  # Bot + Scraper zusammen
“””

import os
import time
import json
import logging
import asyncio
import argparse
import threading
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# python-telegram-bot v20+

from telegram import (
Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
)
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
ContextTypes
)
from telegram.constants import ParseMode

# Scraper importieren (gleicher Ordner)

try:
from sofascore_live_scraper import (
LiveScanner, ValueBet, MatchStats,
TOP5_LEAGUES, POLL_INTERVAL_SECONDS,
MIN_EDGE, KELLY_FRACTION
)
SCRAPER_AVAILABLE = True
except ImportError:
SCRAPER_AVAILABLE = False

# ─────────────────────────────────────────────

# KONFIGURATION

# ─────────────────────────────────────────────

load_dotenv()

TG_TOKEN   = os.getenv(“TG_TOKEN”, “”)
TG_CHAT_ID = os.getenv(“TG_CHAT_ID”, “”)

# Bankroll-Datei (persistent)

BANKROLL_FILE = Path(“bankroll.json”)

# Logging

logging.basicConfig(
format=”%(asctime)s [%(levelname)s] %(message)s”,
level=logging.INFO
)
log = logging.getLogger(**name**)

# ─────────────────────────────────────────────

# BANKROLL MANAGER (JSON-basiert)

# ─────────────────────────────────────────────

class BankrollManager:
def **init**(self):
self.data = self._load()

```
def _load(self) -> dict:
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

def get_balance(self) -> float:
    return self.data["current"]

def add_bet(self, bet_id: str, market: str, odds: float,
            kelly_pct: float, match_str: str) -> float:
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

def settle_bet(self, bet_id: str, won: bool):
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

def get_stats_text(self) -> str:
    s = self.data["stats"]
    current = self.data["current"]
    initial = self.data["initial"]
    roi = ((current - initial) / initial) * 100
    total_bets = s["wins"] + s["losses"]
    win_rate = (s["wins"] / total_bets * 100) if total_bets > 0 else 0

    return (
        f"💰 <b>Bankroll: {current:.2f}€</b> (Start: {initial:.2f}€)\n"
        f"📈 ROI: <b>{roi:+.1f}%</b>\n"
        f"✅ Gewonnen: {s['wins']} | ❌ Verloren: {s['losses']} "
        f"| ⏳ Offen: {s['pending']}\n"
        f"🎯 Trefferquote: {win_rate:.0f}%\n"
        f"💵 Gesamt-Profit: <b>{s['total_profit']:+.2f}€</b>"
    )

def get_pending_bets(self) -> list:
    return [b for b in self.data["bets"] if b["status"] == "pending"]
```

bankroll = BankrollManager()

# ─────────────────────────────────────────────

# NACHRICHTENFORMATIERUNG

# ─────────────────────────────────────────────

PATTERN_EMOJI = {
“LATE_PRESSURE”:  “🔥”,
“OPEN_GAME”:      “⚡”,
“TURBO_TRIGGER”:  “🚀”,
“HOME_DOMINANT”:  “💪”,
“AWAY_DOMINANT”:  “🔄”,
“DEAD_RUBBER”:    “😴”,
“NEUTRAL”:        “⚖️”,
}

CONFIDENCE_EMOJI = {
“SEHR HOCH”: “🟢”,
“HOCH”:      “🟡”,
“MITTEL”:    “🟠”,
“NIEDRIG”:   “🔴”,
}

def format_value_bet_message(vb: “ValueBet”) -> str:
m = vb.match
pattern_icon = PATTERN_EMOJI.get(vb.pattern, “📊”)
conf_icon    = CONFIDENCE_EMOJI.get(vb.confidence, “⚪”)
stake        = round(bankroll.get_balance() * vb.kelly_pct, 2)

```
return (
    f"🤖 <b>BETTINGMIND · VALUE BET ALERT</b>\n"
    f"{'─' * 30}\n"
    f"⚽ <b>{m.home_team}</b> vs <b>{m.away_team}</b>\n"
    f"🏆 {m.league} · ⏱ {m.minute}'\n"
    f"📋 Stand: <b>{m.home_score} : {m.away_score}</b>\n"
    f"\n"
    f"{pattern_icon} Muster: <b>{vb.pattern.replace('_', ' ')}</b>\n"
    f"\n"
    f"🎯 <b>Markt: {vb.market}</b>\n"
    f"{'─' * 30}\n"
    f"📊 Fair Prob:   <b>{vb.fair_prob:.0%}</b>\n"
    f"⚖️  Break-Even:  <b>@{vb.break_even:.2f}</b>\n"
    f"💎 Bookie Quote: <b>@{vb.bookie_odds:.2f}</b>\n"
    f"💰 Edge:        <b>+{vb.edge:.1%}</b>\n"
    f"{'─' * 30}\n"
    f"📈 xG: {m.xg_home:.2f} – {m.xg_away:.2f}\n"
    f"⚡ Momentum: {m.momentum_home:.0f}% – {m.momentum_away:.0f}%\n"
    f"🎯 Schüsse: {m.shots_on_target_home} – {m.shots_on_target_away}\n"
    f"{'─' * 30}\n"
    f"{conf_icon} Konfidenz: <b>{vb.confidence}</b>\n"
    f"💵 Empf. Einsatz (Kelly): <b>{stake:.2f}€</b> "
    f"({vb.kelly_pct:.1%} Bankroll)\n"
    f"💰 Aktuell: {bankroll.get_balance():.2f}€"
)
```

def format_alert_keyboard(bet_id: str) -> InlineKeyboardMarkup:
return InlineKeyboardMarkup([
[
InlineKeyboardButton(“✅ Bet platziert”, callback_data=f”placed_{bet_id}”),
InlineKeyboardButton(“❌ Skip”, callback_data=f”skip_{bet_id}”),
],
[
InlineKeyboardButton(“📊 Bankroll”, callback_data=“bankroll”),
InlineKeyboardButton(“📋 Offene Bets”, callback_data=“pending”),
]
])

# ─────────────────────────────────────────────

# BOT COMMANDS

# ─────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“🤖 <b>BettingMind Bot aktiv!</b>\n\n”
“Verfügbare Befehle:\n”
“/bankroll – Kontostand & Statistiken\n”
“/pending  – Offene Wetten\n”
“/history  – Letzte 10 Wetten\n”
“/scan     – Manuell jetzt scannen\n”
“/setbank  – Bankroll setzen (z.B. /setbank 500)\n”
“/help     – Diese Hilfe”,
parse_mode=ParseMode.HTML
)

async def cmd_bankroll(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
bankroll.get_stats_text(),
parse_mode=ParseMode.HTML
)

async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
pending = bankroll.get_pending_bets()
if not pending:
await update.message.reply_text(“⏳ Keine offenen Wetten.”)
return

```
lines = ["📋 <b>Offene Wetten:</b>\n"]
for i, bet in enumerate(pending[-10:], 1):
    lines.append(
        f"{i}. {bet['match']}\n"
        f"   {bet['market']} @{bet['odds']:.2f} · "
        f"Einsatz: {bet['stake']:.2f}€\n"
        f"   <code>ID: {bet['id'][:8]}</code>"
    )

keyboard = []
for bet in pending[-5:]:
    keyboard.append([
        InlineKeyboardButton(
            f"✅ Gewonnen: {bet['match'][:20]}",
            callback_data=f"won_{bet['id']}"
        ),
        InlineKeyboardButton(
            f"❌ Verloren",
            callback_data=f"lost_{bet['id']}"
        ),
    ])

await update.message.reply_text(
    "\n".join(lines),
    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    parse_mode=ParseMode.HTML
)
```

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
bets = [b for b in bankroll.data[“bets”] if b[“status”] != “pending”]
if not bets:
await update.message.reply_text(“📜 Noch keine abgeschlossenen Wetten.”)
return

```
recent = bets[-10:][::-1]
lines = ["📜 <b>Letzte Wetten:</b>\n"]
for bet in recent:
    icon = "✅" if bet["status"] == "won" else "❌"
    profit_str = f"{bet['profit']:+.2f}€"
    lines.append(
        f"{icon} {bet['match']}\n"
        f"   {bet['market']} @{bet['odds']:.2f} · "
        f"Einsatz: {bet['stake']:.2f}€ → <b>{profit_str}</b>"
    )

await update.message.reply_text(
    "\n".join(lines),
    parse_mode=ParseMode.HTML
)
```

async def cmd_setbank(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
try:
amount = float(ctx.args[0])
bankroll.data[“current”] = amount
bankroll.data[“initial”] = amount
bankroll._save()
await update.message.reply_text(
f”✅ Bankroll auf <b>{amount:.2f}€</b> gesetzt.”,
parse_mode=ParseMode.HTML
)
except (IndexError, ValueError):
await update.message.reply_text(“❌ Nutzung: /setbank 500”)

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not SCRAPER_AVAILABLE:
await update.message.reply_text(
“❌ sofascore_live_scraper.py nicht gefunden.\n”
“Stelle sicher dass beide Dateien im gleichen Ordner sind.”
)
return

```
msg = await update.message.reply_text("🔍 Scanne SofaScore...")
try:
    scanner = LiveScanner(send_telegram=False)
    value_bets = await asyncio.get_event_loop().run_in_executor(
        None, scanner.scan
    )
    if value_bets:
        await msg.edit_text(f"✅ {len(value_bets)} Value Bets gefunden! Sende Alerts...")
        for vb in value_bets:
            await send_value_bet_alert(ctx.bot, vb)
    else:
        await msg.edit_text("📊 Scan abgeschlossen – kein Value erkannt.")
except Exception as e:
    await msg.edit_text(f"❌ Fehler beim Scan: {e}")
```

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await cmd_start(update, ctx)

# ─────────────────────────────────────────────

# CALLBACK HANDLER (Inline Buttons)

# ─────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data

```
# ── Bankroll anzeigen ──
if data == "bankroll":
    await query.message.reply_text(
        bankroll.get_stats_text(),
        parse_mode=ParseMode.HTML
    )

# ── Offene Bets ──
elif data == "pending":
    pending = bankroll.get_pending_bets()
    if pending:
        text = f"⏳ <b>{len(pending)} offene Wetten</b>\n"
        for b in pending[-5:]:
            text += f"\n• {b['match']}: {b['market']} @{b['odds']:.2f} ({b['stake']:.2f}€)"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await query.message.reply_text("⏳ Keine offenen Wetten.")

# ── Bet platziert ──
elif data.startswith("placed_"):
    bet_id = data.replace("placed_", "")
    # Aus der Nachricht Daten lesen und speichern
    msg_text = query.message.text or ""
    market = _extract_field(msg_text, "Markt:")
    odds   = _extract_odds(msg_text, "Bookie Quote:")
    match_str = _extract_match(msg_text)

    stake = bankroll.add_bet(bet_id, market, odds,
                             _extract_kelly(msg_text), match_str)

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "✅ Gewonnen", callback_data=f"won_{bet_id}"
            ),
            InlineKeyboardButton(
                "❌ Verloren", callback_data=f"lost_{bet_id}"
            ),
        ]])
    )
    await query.message.reply_text(
        f"✅ <b>Bet gespeichert!</b>\n"
        f"Einsatz: <b>{stake:.2f}€</b>\n"
        f"Bankroll danach (nach Ergebnis): {bankroll.get_balance():.2f}€\n\n"
        f"Sobald das Ergebnis feststeht, bitte ✅/❌ drücken.",
        parse_mode=ParseMode.HTML
    )

# ── Skip ──
elif data.startswith("skip_"):
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("⏭ Übersprungen.")

# ── Gewonnen ──
elif data.startswith("won_"):
    bet_id = data.replace("won_", "")
    bet = bankroll.settle_bet(bet_id, won=True)
    if bet:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"🎉 <b>GEWONNEN!</b>\n"
            f"{bet['match']} · {bet['market']} @{bet['odds']:.2f}\n"
            f"Einsatz: {bet['stake']:.2f}€ → "
            f"<b>+{bet['profit']:.2f}€ Gewinn</b>\n\n"
            f"💰 Neue Bankroll: <b>{bankroll.get_balance():.2f}€</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await query.message.reply_text("❓ Bet nicht gefunden.")

# ── Verloren ──
elif data.startswith("lost_"):
    bet_id = data.replace("lost_", "")
    bet = bankroll.settle_bet(bet_id, won=False)
    if bet:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"😔 <b>Verloren</b>\n"
            f"{bet['match']} · {bet['market']} @{bet['odds']:.2f}\n"
            f"Verlust: <b>-{bet['stake']:.2f}€</b>\n\n"
            f"💰 Neue Bankroll: <b>{bankroll.get_balance():.2f}€</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await query.message.reply_text("❓ Bet nicht gefunden.")
```

# ─────────────────────────────────────────────

# ALERT SENDER (aus Scraper aufrufbar)

# ─────────────────────────────────────────────

async def send_value_bet_alert(bot: Bot, vb: “ValueBet”):
“”“Value Bet Alert an Telegram schicken.”””
if not TG_CHAT_ID:
log.warning(“TG_CHAT_ID nicht gesetzt!”)
return

```
bet_id = f"{vb.match.match_id}_{vb.market[:4]}_{int(time.time())}"
text   = format_value_bet_message(vb)
kb     = format_alert_keyboard(bet_id)

try:
    await bot.send_message(
        chat_id=TG_CHAT_ID,
        text=text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML
    )
    log.info(f"Alert gesendet: {vb.match.home_team} vs {vb.match.away_team} · {vb.market}")
except Exception as e:
    log.error(f"Telegram-Fehler: {e}")
```

def send_alert_sync(vb: “ValueBet”):
“”“Synchroner Wrapper für send_value_bet_alert (aus Scraper-Thread).”””
import asyncio
bot = Bot(token=TG_TOKEN)
asyncio.run(send_value_bet_alert(bot, vb))

# ─────────────────────────────────────────────

# HILFSFUNKTIONEN (Text-Parsing)

# ─────────────────────────────────────────────

def _extract_field(text: str, label: str) -> str:
for line in text.split(”\n”):
if label in line:
return line.split(label)[-1].strip()
return “Unbekannt”

def _extract_odds(text: str, label: str) -> float:
raw = _extract_field(text, label).replace(”@”, “”).strip()
try:
return float(raw)
except:
return 2.0

def _extract_kelly(text: str) -> float:
for line in text.split(”\n”):
if “Kelly” in line and “%” in line:
for part in line.split():
if “%” in part:
try:
return float(part.replace(”%”, “”).replace(”(”, “”)) / 100
except:
pass
return 0.02

def _extract_match(text: str) -> str:
for line in text.split(”\n”):
if “ vs “ in line:
return line.strip().replace(”<b>”, “”).replace(”</b>”, “”).replace(“⚽”, “”).strip()
return “Unbekannt”

# ─────────────────────────────────────────────

# INTEGRIERTER SCRAPER-LOOP (Thread)

# ─────────────────────────────────────────────

def scraper_thread(app: Application):
“”“Scraper im Hintergrund laufen lassen.”””
if not SCRAPER_AVAILABLE:
log.warning(“Scraper nicht verfügbar – nur manuelle /scan Befehle möglich”)
return

```
log.info("Scraper-Thread gestartet")
scanner = LiveScanner(send_telegram=False)
seen = set()

while True:
    try:
        value_bets = scanner.scan()
        for vb in value_bets:
            key = f"{vb.match.match_id}_{vb.market}_{vb.match.minute // 5}"
            if key not in seen:
                seen.add(key)
                # Alert über Bot senden
                asyncio.run_coroutine_threadsafe(
                    send_value_bet_alert(app.bot, vb),
                    app.bot._application.event_loop
                        if hasattr(app.bot, '_application') else asyncio.get_event_loop()
                )
    except Exception as e:
        log.error(f"Scraper-Thread Fehler: {e}")

    time.sleep(POLL_INTERVAL_SECONDS)
```

# ─────────────────────────────────────────────

# MAIN

# ─────────────────────────────────────────────

def main():
parser = argparse.ArgumentParser(description=“BettingMind Telegram Bot”)
parser.add_argument(”–integrated”, action=“store_true”,
help=“Scraper + Bot zusammen starten”)
args = parser.parse_args()

```
if not TG_TOKEN:
    print("❌ TG_TOKEN nicht gesetzt!")
    print("   Export: export TG_TOKEN='dein_token_hier'")
    print("   Oder:   .env Datei erstellen mit TG_TOKEN=...")
    return

print("🤖 BettingMind Telegram Bot startet...")
print(f"   Token: {TG_TOKEN[:10]}...")
print(f"   Chat-ID: {TG_CHAT_ID or 'NICHT GESETZT – /start senden um ID zu holen'}")

# Application aufbauen
app = (
    Application.builder()
    .token(TG_TOKEN)
    .build()
)

# Commands registrieren
app.add_handler(CommandHandler("start",    cmd_start))
app.add_handler(CommandHandler("bankroll", cmd_bankroll))
app.add_handler(CommandHandler("pending",  cmd_pending))
app.add_handler(CommandHandler("history",  cmd_history))
app.add_handler(CommandHandler("setbank",  cmd_setbank))
app.add_handler(CommandHandler("scan",     cmd_scan))
app.add_handler(CommandHandler("help",     cmd_help))

# Callback-Handler für Inline-Buttons
app.add_handler(CallbackQueryHandler(callback_handler))

# Scraper-Thread (optional)
if args.integrated and SCRAPER_AVAILABLE:
    t = threading.Thread(target=scraper_thread, args=(app,), daemon=True)
    t.start()
    print("   Scraper-Thread: aktiv")

print("   Bot läuft – Ctrl+C zum Stoppen\n")
app.run_polling(allowed_updates=Update.ALL_TYPES)
```

if **name** == “**main**”:
main()

# ─────────────────────────────────────────────

# SCHNELLSTART-ANLEITUNG

# ─────────────────────────────────────────────

“””
SCHRITT-FÜR-SCHRITT SETUP:

1. TELEGRAM BOT ERSTELLEN
   ─────────────────────────
   • Telegram öffnen → @BotFather suchen
   • /newbot → Namen eingeben (z.B. “BettingMind”)
   • Bot-Nutzernamen eingeben (z.B. “bettingmind_bot”)
   • TOKEN kopieren (sieht aus wie: 123456:ABC-DEF…)
1. CHAT-ID HERAUSFINDEN
   ─────────────────────────
   • Bot in Telegram anschreiben: /start
   • Browser öffnen:
   https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates
   • In der Antwort: “chat”:{“id”: DEINE_CHAT_ID}
1. .env DATEI ERSTELLEN
   ─────────────────────────
   Datei “.env” im gleichen Ordner:
   
   TG_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TG_CHAT_ID=987654321
1. ABHÄNGIGKEITEN INSTALLIEREN
   ─────────────────────────
   pip install python-telegram-bot requests python-dotenv
1. STARTEN
   ─────────────────────────
   
   # Nur Bot (manuelle Scans mit /scan):
   
   python telegram_bot.py
   
   # Bot + Automatischer Scraper:
   
   python telegram_bot.py –integrated

VERFÜGBARE BOT-BEFEHLE:
/start      → Bot aktivieren
/bankroll   → Kontostand & Statistiken
/pending    → Offene Wetten
/history    → Letzte 10 Wetten
/scan       → Jetzt manuell scannen
/setbank 200 → Startkapital auf 200€ setzen
/help       → Hilfe

INLINE BUTTONS BEI JEDEM ALERT:
✅ Bet platziert → speichert den Einsatz
❌ Skip          → ignorieren
✅ Gewonnen      → Profit buchen
❌ Verloren      → Verlust buchen
📊 Bankroll      → aktueller Stand
📋 Offene Bets   → alle pending
“””
