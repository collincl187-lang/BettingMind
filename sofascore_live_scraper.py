“””
╔══════════════════════════════════════════════════════════════════╗
║         BETTINGMIND – SofaScore Live Scraper v2.0               ║
║         Top-5 Ligen | Value Bet Engine | KI-Analyse             ║
╚══════════════════════════════════════════════════════════════════╝

Echte SofaScore API-Endpoints (verifiziert April 2025):
BASE: https://api.sofascore.com/api/v1

Tournament-IDs (aus SofaScore URLs extrahiert):
Bundesliga     → /35
Premier League → /17
La Liga        → /8
Serie A        → /23
Ligue 1        → /34
Champions Lgue → /7

Setup:
pip install requests rich schedule python-telegram-bot

Nutzung:
python sofascore_live_scraper.py          # Einmalig scannen
python sofascore_live_scraper.py –loop   # Alle 45 Sek. scannen
python sofascore_live_scraper.py –tg     # + Telegram Alerts
“””

import requests
import time
import json
import math
import argparse
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────

# KONFIGURATION

# ─────────────────────────────────────────────

BASE_URL = “https://api.sofascore.com/api/v1”

# Echte Tournament-IDs (aus SofaScore URLs)

TOP5_LEAGUES = {
“Bundesliga”:       35,
“Premier League”:   17,
“La Liga”:           8,
“Serie A”:          23,
“Ligue 1”:          34,
“Champions League”:  7,
}

# Anti-Ban: 30-45 Sek. zwischen Polling-Zyklen (Community-Empfehlung)

POLL_INTERVAL_SECONDS = 45

# Mindest-Edge für Value Bet Alert (5% = 0.05)

MIN_EDGE = 0.05

# Quarter-Kelly Faktor

KELLY_FRACTION = 0.25

# Telegram (optional) – Token und Chat-ID aus Umgebungsvariablen

TG_TOKEN   = os.getenv(“TG_TOKEN”, “”)
TG_CHAT_ID = os.getenv(“TG_CHAT_ID”, “”)

HEADERS = {
“User-Agent”: (
“Mozilla/5.0 (Windows NT 10.0; Win64; x64) “
“AppleWebKit/537.36 (KHTML, like Gecko) “
“Chrome/124.0.0.0 Safari/537.36”
),
“Accept”: “application/json”,
“Referer”: “https://www.sofascore.com/”,
“Origin”: “https://www.sofascore.com”,
}

# Delay zwischen einzelnen API-Calls (Cloudflare-Schutz)

REQUEST_DELAY = 1.5  # Sekunden

# ─────────────────────────────────────────────

# DATENSTRUKTUREN

# ─────────────────────────────────────────────

@dataclass
class MatchStats:
match_id:            int
home_team:           str
away_team:           str
home_score:          int
away_score:          int
minute:              int
league:              str
# Statistiken
xg_home:             float = 0.0
xg_away:             float = 0.0
momentum_home:       float = 50.0   # 0–100
momentum_away:       float = 50.0
shots_on_target_home: int = 0
shots_on_target_away: int = 0
possession_home:     float = 50.0
possession_away:     float = 50.0
corners_home:        int = 0
corners_away:        int = 0
dangerous_attacks_home: int = 0
dangerous_attacks_away: int = 0
yellow_cards_home:   int = 0
yellow_cards_away:   int = 0
red_cards_home:      int = 0
red_cards_away:      int = 0
# Odds (falls verfügbar)
odds_over25:         float = 0.0
odds_btts:           float = 0.0
odds_home_win:       float = 0.0
odds_draw:           float = 0.0
odds_away_win:       float = 0.0

@dataclass
class ValueBet:
market:      str
fair_prob:   float
break_even:  float
bookie_odds: float
edge:        float
kelly_pct:   float
confidence:  str
pattern:     str
match:       “MatchStats” = field(repr=False)

```
def summary(self) -> str:
    return (
        f"⚽ {self.match.home_team} vs {self.match.away_team} "
        f"[{self.match.score_str()}] · {self.match.minute}' · {self.match.league}\n"
        f"🎯 Markt: {self.market}\n"
        f"📊 Fair: {self.fair_prob:.0%} | Break-Even: @{self.break_even:.2f} | "
        f"Quote: @{self.bookie_odds:.2f}\n"
        f"💰 Edge: +{self.edge:.1%} | Kelly: {self.kelly_pct:.1%} Bankroll\n"
        f"🔍 Muster: {self.pattern} | Konfidenz: {self.confidence}"
    )
```

# Erweiterung der MatchStats um Hilfsmethode

def score_str(self):
return f”{self.home_score}:{self.away_score}”

MatchStats.score_str = score_str

# ─────────────────────────────────────────────

# API-CLIENT

# ─────────────────────────────────────────────

class SofaScoreClient:
“”“Wrapper um SofaScore’s inoffizielle API.”””

```
def __init__(self):
    self.session = requests.Session()
    self.session.headers.update(HEADERS)

def _get(self, endpoint: str) -> Optional[dict]:
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = self.session.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            print(f"  [RATE LIMIT] Warte 60 Sekunden...")
            time.sleep(60)
            return None
        elif resp.status_code == 403:
            print(f"  [403] Cloudflare-Block für {endpoint}")
            return None
        else:
            print(f"  [HTTP {resp.status_code}] {endpoint}")
            return None
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {endpoint}")
        return None
    except Exception as e:
        print(f"  [ERROR] {endpoint}: {e}")
        return None

def get_live_events(self, sport: str = "football") -> list:
    """Alle aktuell laufenden Spiele holen."""
    data = self._get(f"/sport/{sport}/events/live")
    if data and "events" in data:
        return data["events"]
    return []

def get_event_statistics(self, event_id: int) -> Optional[dict]:
    """xG, Schüsse, Possession etc. für ein Spiel."""
    time.sleep(REQUEST_DELAY)
    return self._get(f"/event/{event_id}/statistics")

def get_event_momentum(self, event_id: int) -> Optional[dict]:
    """Angriffsmomentum-Timeline."""
    time.sleep(REQUEST_DELAY)
    return self._get(f"/event/{event_id}/momentum")

def get_event_odds(self, event_id: int) -> Optional[dict]:
    """Pre-match / Live Quoten."""
    time.sleep(REQUEST_DELAY)
    return self._get(f"/event/{event_id}/odds/1/all")

def get_h2h(self, event_id: int) -> Optional[dict]:
    """Head-to-Head Historie."""
    time.sleep(REQUEST_DELAY)
    return self._get(f"/event/{event_id}/h2h/events")
```

# ─────────────────────────────────────────────

# STATISTIK-PARSER

# ─────────────────────────────────────────────

def parse_statistics(stats_data: dict, match: MatchStats) -> MatchStats:
“””
SofaScore Statistiken-Response parsen.
Struktur: data[“statistics”] → Liste von Perioden
→ jede Periode hat “groups” → “statisticsItems”
“””
if not stats_data or “statistics” not in stats_data:
return match

```
# Gesamt-Statistiken bevorzugen (period = "ALL")
periods = stats_data["statistics"]
target_period = None

for period in periods:
    if period.get("period") == "ALL":
        target_period = period
        break

if not target_period and periods:
    target_period = periods[-1]  # Fallback: letzte verfügbare

if not target_period:
    return match

for group in target_period.get("groups", []):
    for item in group.get("statisticsItems", []):
        name = item.get("name", "").lower()
        home_val = item.get("home", "0") or "0"
        away_val = item.get("away", "0") or "0"

        # Werte bereinigen (können "45%" oder "1.23" sein)
        def clean(v):
            try:
                return float(str(v).replace("%", "").strip())
            except:
                return 0.0

        h, a = clean(home_val), clean(away_val)

        if "expected goals" in name or "xg" in name:
            match.xg_home = h
            match.xg_away = a
        elif "shots on target" in name or "torschüsse" in name:
            match.shots_on_target_home = int(h)
            match.shots_on_target_away = int(a)
        elif "ball possession" in name or "possession" in name or "ballbesitz" in name:
            match.possession_home = h
            match.possession_away = a
        elif "corner" in name or "ecken" in name:
            match.corners_home = int(h)
            match.corners_away = int(a)
        elif "dangerous attack" in name or "gefährliche" in name:
            match.dangerous_attacks_home = int(h)
            match.dangerous_attacks_away = int(a)
        elif "yellow card" in name or "gelbe" in name:
            match.yellow_cards_home = int(h)
            match.yellow_cards_away = int(a)
        elif "red card" in name or "rote" in name:
            match.red_cards_home = int(h)
            match.red_cards_away = int(a)

return match
```

def parse_momentum(momentum_data: dict) -> tuple:
“””
Momentum-Timeline parsen → aktuellen Heim/Gast-Wert berechnen.
Nimmt den Durchschnitt der letzten 5 Datenpunkte.
“””
if not momentum_data or “momentum” not in momentum_data:
return 50.0, 50.0

```
points = momentum_data["momentum"]
if not points:
    return 50.0, 50.0

# Letzte 5 Punkte für aktuellen Trend
recent = points[-5:] if len(points) >= 5 else points

home_vals = [p.get("home", 0) for p in recent if "home" in p]
away_vals = [p.get("away", 0) for p in recent if "away" in p]

# Alternativ: value > 0 = Heim, value < 0 = Gast (SofaScore Format)
if not home_vals and "value" in (recent[0] if recent else {}):
    values = [p.get("value", 0) for p in recent]
    avg = sum(values) / len(values) if values else 0
    # Normalisieren auf 0–100
    home_pct = min(100, max(0, 50 + avg * 5))
    away_pct = 100 - home_pct
    return home_pct, away_pct

if home_vals:
    home_avg = sum(home_vals) / len(home_vals)
    away_avg = sum(away_vals) / len(away_vals) if away_vals else 100 - home_avg
    total = home_avg + away_avg or 100
    return (home_avg / total) * 100, (away_avg / total) * 100

return 50.0, 50.0
```

def parse_odds(odds_data: dict, match: MatchStats) -> MatchStats:
“”“Quoten aus SofaScore parsen (1X2 + Over/Under).”””
if not odds_data:
return match

```
markets = odds_data.get("markets", [])
for market in markets:
    market_name = market.get("marketName", "").lower()
    choices = market.get("choices", [])

    if "full time" in market_name and "1x2" in market_name:
        for choice in choices:
            name = choice.get("name", "").lower()
            fractional = choice.get("fractionalValue", "")
            # Manchmal als Dezimal
            decimal = choice.get("decimalValue")
            if decimal:
                val = float(decimal)
                if name == "1" or name == "home":
                    match.odds_home_win = val
                elif name == "x" or name == "draw":
                    match.odds_draw = val
                elif name == "2" or name == "away":
                    match.odds_away_win = val

    elif "over/under" in market_name and "2.5" in market_name:
        for choice in choices:
            name = choice.get("name", "").lower()
            decimal = choice.get("decimalValue")
            if decimal:
                val = float(decimal)
                if "over" in name:
                    match.odds_over25 = val
                # BTTS separat, aber oft im gleichen Format
    elif "both teams" in market_name or "btts" in market_name:
        for choice in choices:
            name = choice.get("name", "").lower()
            decimal = choice.get("decimalValue")
            if decimal and "yes" in name:
                match.odds_btts = float(decimal)

return match
```

# ─────────────────────────────────────────────

# MUSTER-ERKENNUNG

# ─────────────────────────────────────────────

def detect_pattern(m: MatchStats) -> str:
“”“Spielmuster anhand von Statistiken klassifizieren.”””
xg_diff = m.xg_home - m.xg_away
total_xg = m.xg_home + m.xg_away
score_diff = m.home_score - m.away_score
momentum_home = m.momentum_home

```
# LATE PRESSURE: Team liegt zurück, hohes Momentum, Minute > 60
if (m.minute >= 60 and
        abs(score_diff) == 1 and
        ((score_diff < 0 and momentum_home > 65) or
         (score_diff > 0 and momentum_home < 35))):
    return "LATE_PRESSURE"

# OPEN GAME: Beide Teams hohes xG
if total_xg >= 1.5 and m.xg_home >= 0.6 and m.xg_away >= 0.6:
    return "OPEN_GAME"

# TURBO TRIGGER: Massiv dominant aber kein Tor mehr als erwartet
if (abs(xg_diff) >= 1.0 and
        abs(score_diff) <= 1 and
        m.shots_on_target_home >= 5):
    return "TURBO_TRIGGER"

# DEAD RUBBER: Wenig Intensität, ausgeglichen, Minute > 70
if (m.minute >= 70 and
        total_xg < 1.0 and
        abs(score_diff) <= 1 and
        40 <= momentum_home <= 60):
    return "DEAD_RUBBER"

# Standard
if xg_diff >= 0.8:
    return "HOME_DOMINANT"
elif xg_diff <= -0.8:
    return "AWAY_DOMINANT"

return "NEUTRAL"
```

# ─────────────────────────────────────────────

# WAHRSCHEINLICHKEITS-MODELL

# ─────────────────────────────────────────────

def calc_fair_probability(m: MatchStats) -> dict:
“””
Regelbasiertes Wahrscheinlichkeitsmodell.
Inputs: xG, Momentum, Schüsse, Muster, Spielzeit
Output: Dict mit Märkten und Fair-Probabilities
“””
pattern = detect_pattern(m)
xg_diff = m.xg_home - m.xg_away
total_xg = m.xg_home + m.xg_away
momentum_h = m.momentum_home / 100.0
minutes_left = max(1, 90 - m.minute)
time_factor = minutes_left / 90.0   # 0 = Spielende, 1 = Anfang

```
probs = {}

# ── ÜBER 2.5 Tore ──
total_goals = m.home_score + m.away_score
if total_goals >= 3:
    probs["over25"] = 0.97
elif total_goals == 2:
    # Brauchen noch 1 Tor
    base = 0.45 + total_xg * 0.08 + momentum_h * 0.05
    probs["over25"] = min(0.92, base + time_factor * 0.1)
elif total_goals == 1:
    base = 0.30 + total_xg * 0.09 + momentum_h * 0.04
    probs["over25"] = min(0.80, base)
else:
    base = 0.20 + total_xg * 0.10
    probs["over25"] = min(0.75, base)

# ── BTTS (Beide treffen) ──
both_scored = m.home_score > 0 and m.away_score > 0
if both_scored:
    probs["btts"] = 0.97
elif m.home_score > 0 or m.away_score > 0:
    # Nur ein Team hat getroffen
    if m.xg_away >= 0.5 and m.home_score > 0:
        probs["btts"] = min(0.75, 0.30 + m.xg_away * 0.15 + time_factor * 0.08)
    elif m.xg_home >= 0.5 and m.away_score > 0:
        probs["btts"] = min(0.75, 0.30 + m.xg_home * 0.15 + time_factor * 0.08)
    else:
        probs["btts"] = 0.15
else:
    probs["btts"] = min(0.60, 0.20 + total_xg * 0.07)

# ── HEIMSIEG ──
score_diff = m.home_score - m.away_score
if score_diff >= 2:
    probs["home_win"] = 0.92
elif score_diff == 1:
    base = 0.70 + momentum_h * 0.10
    probs["home_win"] = min(0.88, base - time_factor * 0.05)
elif score_diff == 0:
    base = 0.33 + xg_diff * 0.06 + momentum_h * 0.08
    probs["home_win"] = min(0.70, max(0.10, base))
elif score_diff == -1:
    base = 0.15 + xg_diff * 0.04 + momentum_h * 0.12
    probs["home_win"] = min(0.55, max(0.05, base))
else:
    probs["home_win"] = max(0.03, 0.08 + momentum_h * 0.05)

# ── UNENTSCHIEDEN ──
if score_diff == 0:
    base = 0.28 + (1 - abs(xg_diff)) * 0.05
    probs["draw"] = min(0.45, base + time_factor * 0.05)
elif abs(score_diff) == 1 and m.minute >= 70:
    probs["draw"] = min(0.35, 0.15 + (1 - momentum_h if score_diff > 0 else momentum_h) * 0.15)
else:
    probs["draw"] = 0.10

# Muster-Bonus / Malus
if pattern == "LATE_PRESSURE":
    probs["home_win"] = min(0.80, probs.get("home_win", 0.33) * 1.15)
    probs["over25"]   = min(0.90, probs.get("over25", 0.40) * 1.10)
elif pattern == "OPEN_GAME":
    probs["over25"] = min(0.95, probs.get("over25", 0.50) * 1.12)
    probs["btts"]   = min(0.88, probs.get("btts", 0.40) * 1.10)
elif pattern == "TURBO_TRIGGER":
    probs["home_win"] = min(0.92, probs.get("home_win", 0.50) * 1.18)
elif pattern == "DEAD_RUBBER":
    probs["over25"] = max(0.10, probs.get("over25", 0.30) * 0.80)
    probs["draw"]   = min(0.55, probs.get("draw", 0.30) * 1.15)

# Rote Karte → dramatisch mehr Druck
if m.red_cards_away >= 1:
    probs["home_win"] = min(0.90, probs.get("home_win", 0.33) * 1.25)
if m.red_cards_home >= 1:
    probs["away_win"] = probs.get("away_win", 0.25)
    probs["away_win"] = min(0.85, probs["away_win"] * 1.25)

return probs
```

# ─────────────────────────────────────────────

# VALUE BET KALKULATOR

# ─────────────────────────────────────────────

def calc_value_bets(m: MatchStats) -> list:
“””
Value Bets für ein Spiel berechnen.
Returns: Liste von ValueBet-Objekten.
“””
fair_probs = calc_fair_probability(m)
pattern    = detect_pattern(m)
value_bets = []

```
market_map = {
    "over25":    ("Über 2.5 Tore",    m.odds_over25),
    "btts":      ("Beide treffen",    m.odds_btts),
    "home_win":  ("Heimsieg",         m.odds_home_win),
    "draw":      ("Unentschieden",    m.odds_draw),
    "away_win":  ("Auswärtssieg",     m.odds_away_win),
}

confidence_map = {
    "LATE_PRESSURE":  "HOCH",
    "OPEN_GAME":      "MITTEL",
    "TURBO_TRIGGER":  "SEHR HOCH",
    "HOME_DOMINANT":  "MITTEL",
    "AWAY_DOMINANT":  "MITTEL",
    "DEAD_RUBBER":    "NIEDRIG",
    "NEUTRAL":        "NIEDRIG",
}

for key, (label, bookie_odds) in market_map.items():
    if key not in fair_probs:
        continue
    if not bookie_odds or bookie_odds < 1.05:
        continue  # Keine Odds verfügbar

    fair_p = fair_probs[key]
    if fair_p <= 0 or fair_p >= 1:
        continue

    break_even = 1 / fair_p
    edge = (fair_p * bookie_odds) - 1

    if edge >= MIN_EDGE:
        # Kelly-Kriterium (Quarter Kelly)
        b = bookie_odds - 1
        q = 1 - fair_p
        kelly_raw = (fair_p * b - q) / b
        kelly = max(0, kelly_raw * KELLY_FRACTION)

        value_bets.append(ValueBet(
            market=label,
            fair_prob=fair_p,
            break_even=break_even,
            bookie_odds=bookie_odds,
            edge=edge,
            kelly_pct=kelly,
            confidence=confidence_map.get(pattern, "NIEDRIG"),
            pattern=pattern,
            match=m,
        ))

# Sortieren nach Edge (höchster zuerst)
value_bets.sort(key=lambda x: x.edge, reverse=True)
return value_bets
```

# ─────────────────────────────────────────────

# HAUPT-SCANNER

# ─────────────────────────────────────────────

class LiveScanner:
def **init**(self, send_telegram: bool = False):
self.client = SofaScoreClient()
self.send_tg = send_telegram and bool(TG_TOKEN) and bool(TG_CHAT_ID)
self.seen_alerts: set = set()  # Duplikate vermeiden

```
def scan(self) -> list:
    """Einmal alle Live-Spiele der Top-5-Ligen scannen."""
    print(f"\n{'═' * 60}")
    print(f"  BETTINGMIND SCAN · {datetime.now().strftime('%H:%M:%S')} Uhr")
    print(f"{'═' * 60}")

    live_events = self.client.get_live_events("football")
    if not live_events:
        print("  ⚠ Keine Live-Events gefunden (API blockiert oder keine Spiele)")
        return []

    # Nur Top-5-Ligen filtern
    top5_ids = set(TOP5_LEAGUES.values())
    filtered = []
    for event in live_events:
        tid = (event.get("tournament", {})
                   .get("uniqueTournament", {})
                   .get("id"))
        if tid in top5_ids:
            filtered.append(event)

    print(f"  📡 {len(live_events)} Live-Spiele gefunden · "
          f"{len(filtered)} in Top-5-Ligen")

    if not filtered:
        print("  ℹ Gerade keine Top-5-Liga-Spiele live")
        return []

    all_value_bets = []

    for event in filtered:
        match = self._process_event(event)
        if match is None:
            continue

        value_bets = calc_value_bets(match)

        # Output
        pattern = detect_pattern(match)
        print(f"\n  ⚽ {match.home_team} {match.score_str()} {match.away_team} "
              f"· {match.minute}' · {match.league}")
        print(f"     xG: {match.xg_home:.2f}–{match.xg_away:.2f} | "
              f"Momentum: {match.momentum_home:.0f}% | "
              f"Muster: {pattern}")

        if value_bets:
            for vb in value_bets:
                print(f"     ✅ VALUE: {vb.market} @{vb.bookie_odds:.2f} | "
                      f"Fair: {vb.fair_prob:.0%} | "
                      f"Edge: +{vb.edge:.1%} | "
                      f"Kelly: {vb.kelly_pct:.1%}")
                all_value_bets.append(vb)

                # Telegram Alert (nur neue Bets)
                alert_key = f"{match.match_id}_{vb.market}"
                if self.send_tg and alert_key not in self.seen_alerts:
                    self._send_telegram(vb.summary())
                    self.seen_alerts.add(alert_key)
        else:
            print(f"     ─ Kein Value erkannt")

    print(f"\n{'═' * 60}")
    print(f"  GESAMT: {len(all_value_bets)} Value Bets gefunden")
    print(f"{'═' * 60}\n")

    return all_value_bets

def _process_event(self, event: dict) -> Optional[MatchStats]:
    """Ein einzelnes Event vollständig aufbereiten."""
    try:
        event_id = event["id"]

        # Liga-Name aus Tournament-Daten
        league_name = (event.get("tournament", {})
                           .get("uniqueTournament", {})
                           .get("name", "Unknown"))

        home_name = event.get("homeTeam", {}).get("name", "?")
        away_name = event.get("awayTeam", {}).get("name", "?")

        home_score = (event.get("homeScore", {}).get("current") or
                     event.get("homeScore", {}).get("display", 0))
        away_score = (event.get("awayScore", {}).get("current") or
                     event.get("awayScore", {}).get("display", 0))

        # Spielminute
        status = event.get("status", {})
        minute = status.get("minuteExpanded") or status.get("minute", 0)

        match = MatchStats(
            match_id=event_id,
            home_team=home_name,
            away_team=away_name,
            home_score=int(home_score or 0),
            away_score=int(away_score or 0),
            minute=int(minute or 0),
            league=league_name,
        )

        # Statistiken laden
        stats_data = self.client.get_event_statistics(event_id)
        if stats_data:
            match = parse_statistics(stats_data, match)

        # Momentum laden
        mom_data = self.client.get_event_momentum(event_id)
        if mom_data:
            match.momentum_home, match.momentum_away = parse_momentum(mom_data)

        # Odds laden (optional, falls verfügbar)
        odds_data = self.client.get_event_odds(event_id)
        if odds_data:
            match = parse_odds(odds_data, match)

        return match

    except Exception as e:
        print(f"     [ERROR] Event verarbeiten: {e}")
        return None

def _send_telegram(self, text: str):
    """Telegram-Nachricht senden."""
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHAT_ID,
            "text": f"🤖 BETTINGMIND ALERT\n\n{text}",
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"     📲 Telegram-Alert gesendet")
    except Exception as e:
        print(f"     [TG ERROR] {e}")

def run_loop(self):
    """Dauerhafter Scan-Loop."""
    print(f"🚀 BETTINGMIND gestartet · Polling alle {POLL_INTERVAL_SECONDS}s")
    print(f"   Ligen: {', '.join(TOP5_LEAGUES.keys())}")
    print(f"   Min. Edge: {MIN_EDGE:.0%} | Kelly-Faktor: {KELLY_FRACTION}")
    if self.send_tg:
        print(f"   📲 Telegram-Alerts: aktiv")
    print("\n   Stoppen mit Ctrl+C\n")

    while True:
        try:
            self.scan()
            print(f"  ⏳ Nächster Scan in {POLL_INTERVAL_SECONDS} Sekunden...")
            time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n  ✋ Gestoppt.")
            break
        except Exception as e:
            print(f"  [LOOP ERROR] {e} · Retry in 60s")
            time.sleep(60)
```

# ─────────────────────────────────────────────

# HILFSFUNKTIONEN

# ─────────────────────────────────────────────

def demo_without_api():
“””
Zeigt die Value-Bet-Engine mit Beispieldaten –
für Tests ohne aktive Internetverbindung / API-Zugang.
“””
print(”\n” + “═” * 60)
print(”  DEMO MODUS (keine echte API-Verbindung)”)
print(“═” * 60)

```
demos = [
    MatchStats(
        match_id=1, home_team="Bayern München",
        away_team="Borussia Dortmund",
        home_score=1, away_score=1, minute=67, league="Bundesliga",
        xg_home=2.1, xg_away=0.8,
        momentum_home=78, momentum_away=22,
        shots_on_target_home=8, shots_on_target_away=3,
        possession_home=64, possession_away=36,
        corners_home=7, corners_away=2,
        odds_over25=1.85, odds_btts=1.95,
        odds_home_win=1.90, odds_draw=3.60, odds_away_win=4.20,
    ),
    MatchStats(
        match_id=2, home_team="Real Madrid",
        away_team="Atlético Madrid",
        home_score=0, away_score=1, minute=72, league="La Liga",
        xg_home=1.9, xg_away=0.6,
        momentum_home=82, momentum_away=18,
        shots_on_target_home=9, shots_on_target_away=2,
        possession_home=71, possession_away=29,
        corners_home=9, corners_away=1,
        odds_over25=2.30, odds_btts=2.40,
        odds_home_win=2.10, odds_draw=3.20, odds_away_win=3.40,
    ),
    MatchStats(
        match_id=3, home_team="Arsenal",
        away_team="Chelsea",
        home_score=1, away_score=1, minute=55, league="Premier League",
        xg_home=1.4, xg_away=1.2,
        momentum_home=55, momentum_away=45,
        shots_on_target_home=5, shots_on_target_away=4,
        possession_home=53, possession_away=47,
        corners_home=4, corners_away=5,
        odds_over25=1.75, odds_btts=1.65,
        odds_home_win=2.40, odds_draw=3.40, odds_away_win=2.80,
    ),
]

total_value = []
for match in demos:
    pattern = detect_pattern(match)
    value_bets = calc_value_bets(match)

    print(f"\n  ⚽ {match.home_team} {match.score_str()} {match.away_team} "
          f"· {match.minute}' · {match.league}")
    print(f"     xG: {match.xg_home:.2f}–{match.xg_away:.2f} | "
          f"Momentum: {match.momentum_home:.0f}% | Muster: {pattern}")

    if value_bets:
        for vb in value_bets:
            print(f"     ✅ {vb.market} @{vb.bookie_odds:.2f} | "
                  f"Fair: {vb.fair_prob:.0%} | Break-Even: @{vb.break_even:.2f} | "
                  f"Edge: +{vb.edge:.1%} | Kelly: {vb.kelly_pct:.1%} | "
                  f"Konfidenz: {vb.confidence}")
        total_value.extend(value_bets)
    else:
        print(f"     ─ Kein Value erkannt")

print(f"\n{'═' * 60}")
print(f"  {len(total_value)} Value Bets total")
print(f"  Ø Edge: +{sum(v.edge for v in total_value) / len(total_value):.1%}" if total_value else "")
print(f"{'═' * 60}\n")
```

# ─────────────────────────────────────────────

# ENTRY POINT

# ─────────────────────────────────────────────

if **name** == “**main**”:
parser = argparse.ArgumentParser(
description=“BettingMind – SofaScore Live Value Bet Scanner”
)
parser.add_argument(
“–loop”, action=“store_true”,
help=f”Dauerhafter Scan alle {POLL_INTERVAL_SECONDS}s”
)
parser.add_argument(
“–tg”, action=“store_true”,
help=“Telegram-Alerts aktivieren (TG_TOKEN + TG_CHAT_ID in ENV)”
)
parser.add_argument(
“–demo”, action=“store_true”,
help=“Demo-Modus mit Beispieldaten (kein Internet nötig)”
)
parser.add_argument(
“–edge”, type=float, default=MIN_EDGE,
help=f”Mindest-Edge (default: {MIN_EDGE})”
)
parser.add_argument(
“–kelly”, type=float, default=KELLY_FRACTION,
help=f”Kelly-Faktor (default: {KELLY_FRACTION})”
)
args = parser.parse_args()

```
# Parameter übernehmen
MIN_EDGE = args.edge
KELLY_FRACTION = args.kelly

if args.demo:
    demo_without_api()
elif args.loop:
    scanner = LiveScanner(send_telegram=args.tg)
    scanner.run_loop()
else:
    scanner = LiveScanner(send_telegram=args.tg)
    scanner.scan()
```

# ─────────────────────────────────────────────

# ANHANG: WICHTIGE SOFASCORE API-ENDPOINTS

# ─────────────────────────────────────────────

“””
VERIFIZIERTE ENDPOINTS (Stand April 2025):

GET /sport/football/events/live
→ Alle laufenden Fußballspiele

GET /event/{id}/statistics
→ xG, Schüsse, Possession, Ecken, Karten

GET /event/{id}/momentum
→ Angriffsmomentum-Timeline (30-Sek-Intervalle)

GET /event/{id}/odds/1/all
→ Quoten (1X2, Over/Under, BTTS)

GET /event/{id}/h2h/events
→ Head-to-Head Historik

GET /unique-tournament/{id}/season/{season_id}/events/live
→ Live-Events einer bestimmten Liga

TOURNAMENT IDs (aus URL-Analyse):
17  Premier League
8   La Liga
35  Bundesliga
23  Serie A
34  Ligue 1
7   UEFA Champions League
13  UEFA Europa League

RATE LIMITS (Community-Erfahrungen):
• Max ~100 Calls / 5 Minuten pro IP
• Empfehlung: 30-45s zwischen Zyklen
• Bei 429: 60s warten
• User-Agent MUSS gesetzt sein
“””
