name: Aktualizacja cen (PSE RCE)

on:
  schedule:
    - cron: "17 3 * * *"      # codziennie ok. 05:17 czasu polskiego (UTC 03:17)
  workflow_dispatch: {}        # przycisk "Run workflow" do ręcznego uruchomienia

permissions:
  contents: write              # potrzebne, żeby workflow mógł zapisać data/*.json

concurrency:
  group: update-prices
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Pobierz ceny i przelicz
        run: python scripts/update_prices.py
      - name: Zapisz zmiany w repozytorium
        run: |
          git config user.name "bessly-bot"
          git config user.email "actions@users.noreply.github.com"
          git add data/prices.json data/rce_hourly.json
          if git diff --cached --quiet; then
            echo "Brak zmian."
          else
            git commit -m "Aktualizacja cen PSE $(date -u +%F)"
            git push
          fi
