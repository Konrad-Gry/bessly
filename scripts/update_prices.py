#!/usr/bin/env python3
"""
Codzienna aktualizacja cen dla kalkulatora Bessly.

Co robi:
  1. Pobiera z publicznego API PSE (raporty.pse.pl) ceny RCE (PLN/MWh, co 15 min)
     tylko za brakujące dni i dopisuje je do data/rce_hourly.json (pamięć podręczna,
     średnie godzinowe pełnych dób).
  2. Dla każdego miesiąca kalendarzowego wybiera najnowszy "pełny" miesiąc z danymi
     i liczy kształt doby osobno dla dni roboczych (w) i weekendów/świąt (e).
  3. Poziom cen (rdn_avg) bierze z data/tge_monthly.json (średnie z komunikatów TGE),
     a gdy dla danego miesiąca nie ma wpisu TGE, używa średniej z RCE.
  4. Zapisuje wynik do data/prices.json, który wczytuje strona.

Tylko biblioteka standardowa Pythona (bez pip install).
Jeśli cokolwiek pójdzie nie tak, skrypt kończy się błędem i NIE nadpisuje prices.json,
więc strona dalej używa ostatnich dobrych danych.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

API = os.environ.get("PSE_API", "https://api.raporty.pse.pl/api/rce-pln")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "rce_hourly.json"
TGE = DATA / "tge_monthly.json"
OUT = DATA / "prices.json"

HISTORY_DAYS = 430      # tyle dni wstecz trzymamy (każdy miesiąc ma min. jeden pełny przebieg)
CHUNK_DAYS = 7          # tyle dni pobieramy jednym zapytaniem
REFETCH_DAYS = 3        # ostatnie dni pobieramy ponownie (PSE potrafi poprawiać dane)
MIN_WORKDAYS = 8        # miesiąc jest "pełny", gdy ma min. tyle dni roboczych...
MIN_OFFDAYS = 3         # ...i tyle dni wolnych
PRICE_MIN, PRICE_MAX = -1000.0, 6000.0   # zł/MWh, odrzucamy oczywiste błędy


# ---------- kalendarz (to samo co isWorkday w bessly-v2.html) ----------
def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(y, month, day)


def is_workday(d):
    if d.weekday() >= 5:
        return False
    if (d.month, d.day) in {(1, 1), (1, 6), (5, 1), (5, 3), (8, 15), (11, 1), (11, 11), (12, 25), (12, 26)}:
        return False
    e = easter(d.year)
    moving = {e, e + dt.timedelta(days=1), e + dt.timedelta(days=49), e + dt.timedelta(days=60)}
    return d not in moving


# ---------- pobieranie z PSE ----------
def get_json(url, tries=4):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url.replace(" ", "%20"), headers={
                "User-Agent": "bessly-price-updater/1.0 (+github actions)",
                "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as ex:
            last = ex
            time.sleep(2 * (n + 1))
    raise RuntimeError(f"Nie udało się pobrać {url}: {last}")


def fetch_range(start, end):
    """Zwraca listę rekordów {business_date, period, rce_pln} dla dni start..end (włącznie)."""
    flt = f"business_date ge '{start}' and business_date le '{end}'"
    url = f"{API}?$filter={quote(flt, safe=chr(39))}&$select=business_date,period,rce_pln&$first=5000"
    rows = []
    while url:
        page = get_json(url)
        rows.extend(page.get("value", []))
        url = page.get("nextLink")
        if url:
            time.sleep(0.3)
    return rows


def rows_to_days(rows):
    """Rekordy 15-minutowe -> {data: [24 średnie godzinowe]} tylko dla pełnych dób."""
    acc = {}
    for r in rows:
        try:
            price = float(r["rce_pln"])
            date = r["business_date"][:10]
            hour = int(r["period"][:2])      # początek okresu, czas lokalny
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= hour <= 23) or not (PRICE_MIN <= price <= PRICE_MAX):
            continue
        a = acc.setdefault(date, [[0.0, 0] for _ in range(24)])
        a[hour][0] += price
        a[hour][1] += 1
    days = {}
    for date, a in acc.items():
        if all(n > 0 for _, n in a):            # doba niepełna (np. wiosenna zmiana czasu) -> pomijamy
            days[date] = [round(s / n, 2) for s, n in a]
    return days


def update_cache(today):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    oldest = today - dt.timedelta(days=HISTORY_DAYS)
    newest = today + dt.timedelta(days=1)       # ceny na jutro są znane od ok. 14:00
    if cache:
        last = dt.date.fromisoformat(max(cache))
        start = max(oldest, last - dt.timedelta(days=REFETCH_DAYS))
    else:
        start = oldest
    d = start
    got = 0
    while d <= newest:
        end = min(d + dt.timedelta(days=CHUNK_DAYS - 1), newest)
        days = rows_to_days(fetch_range(d.isoformat(), end.isoformat()))
        cache.update(days)
        got += len(days)
        d = end + dt.timedelta(days=1)
    cache = {k: v for k, v in cache.items() if dt.date.fromisoformat(k) >= oldest}
    print(f"Pobrano {got} pełnych dób z PSE, w pamięci podręcznej: {len(cache)}")
    return dict(sorted(cache.items()))


# ---------- liczenie ----------
def mean(xs):
    return sum(xs) / len(xs)


def build_months(cache, tge):
    by_period = {}
    for date, hours in cache.items():
        d = dt.date.fromisoformat(date)
        by_period.setdefault((d.year, d.month), []).append((d, hours))

    months = []
    for m in range(1, 13):
        chosen = None
        for (y, mo) in sorted(k for k in by_period if k[1] == m):     # rosnąco, ostatni pełny wygrywa
            days = by_period[(y, mo)]
            nw = sum(1 for d, _ in days if is_workday(d))
            if nw >= MIN_WORKDAYS and len(days) - nw >= MIN_OFFDAYS:
                chosen = (y, mo, days, nw)
        if not chosen:
            raise RuntimeError(f"Brak pełnego miesiąca danych dla miesiąca {m}. Za mało danych z PSE.")
        y, mo, days, nw = chosen
        work = [h for d, h in days if is_workday(d)]
        off = [h for d, h in days if not is_workday(d)]
        w = [round(mean([h[i] for h in work]), 1) for i in range(24)]
        e = [round(mean([h[i] for h in off]), 1) for i in range(24)]
        rce_avg = round(mean([mean(h) for _, h in days]), 2)
        key = f"{y}-{mo:02d}"
        if key in tge:
            rdn, src = round(float(tge[key]), 2), "TGE"
        else:
            rdn, src = rce_avg, "PSE RCE"
        months.append({
            "month": m, "period": key, "days_work": nw, "days_off": len(days) - nw,
            "rdn_avg": rdn, "level_source": src, "rce_avg": rce_avg, "w": w, "e": e,
        })
    return months


def main():
    DATA.mkdir(exist_ok=True)
    today = dt.date.today()
    tge = json.loads(TGE.read_text()) if TGE.exists() else {}
    cache = update_cache(today)
    months = build_months(cache, tge)
    out = {
        "schema": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_through": max(cache),
        "sources": {
            "shape": "PSE, raport RCE (raporty.pse.pl/report/rce-pln), średnie godzinowe z cen 15-minutowych",
            "level": "TGE, średnie miesięczne z komunikatów (data/tge_monthly.json); bez wpisu: średnia z RCE",
        },
        "months": months,
    }
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    CACHE.write_text(json.dumps(cache, separators=(",", ":")) + "\n")
    tmp.replace(OUT)
    print(f"Zapisano {OUT} (dane do {out['data_through']})")
    for x in months:
        print(f"  {x['period']}  {x['rdn_avg']:>7.2f} zł/MWh ({x['level_source']})  dni rob./wolne: {x['days_work']}/{x['days_off']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:           # noqa: BLE001 - chcemy czytelny błąd i kod != 0
        print(f"BŁĄD: {ex}", file=sys.stderr)
        sys.exit(1)
