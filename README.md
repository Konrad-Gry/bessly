# Bessly: kalkulator opłacalności magazynu energii (BESS) dla firm

**Strona:** https://konrad-gry.github.io/bessly/

Narzędzie do wstępnej oceny, czy magazyn energii opłaci się małej lub średniej firmie. Podajesz zużycie prądu, instalację PV i taryfę, a kalkulator pokazuje zwrot inwestycji, NPV i porównanie scenariuszy.

> To wstępna ocena, nie oferta. Wyniki zależą od założeń, które są jawne i opisane na stronie. Przed decyzją o zakupie sprawdź ceny i opłaty na własnej fakturze i w ofercie wykonawcy.

## Co potrafi
- Liczy oszczędności z arbitrażu cenowego (ładowanie, gdy prąd jest tani, oddawanie, gdy jest drogi) i z optymalizacji opłat.
- Uwzględnia PV, taryfy operatorów, opłatę mocową 2026 i degradację baterii przez 15 lat.
- Pokazuje wynik jako zwrot, NPV i IRR, a także porównuje trzy scenariusze cen prądu.
- Opcjonalnie liczy finansowanie (gotówka, kredyt, leasing), podatek CIT z amortyzacją oraz usługi dla sieci (aFRR, rynek mocy, DSR).
- Szuka optymalnego rozmiaru baterii.
- Pozwala wgrać własne ceny i własny profil zużycia z licznika (CSV lub XLSX) i pobrać wyniki do CSV.

## Skąd są dane
| Dane | Źródło |
|---|---|
| Kształt doby cen prądu | PSE, raport RCE (raporty.pse.pl) |
| Średnie miesięczne ceny RDN | TGE, komunikaty miesięczne |
| Opłaty regulowane i taryfy | URE, taryfy operatorów |
| Opłata mocowa i współczynniki dla magazynów | Rozporządzenia i obwieszczenia, opisane w sekcji „Źródła” na stronie |

Założenia bez potwierdzonego źródła (np. część stawek dla usług dla sieci) są na stronie oznaczone.

## Automatyczna aktualizacja cen
Raz na dobę uruchamia się GitHub Actions (`.github/workflows/update-prices.yml`). Skrypt `scripts/update_prices.py` pobiera ceny RCE z API PSE i zapisuje `data/prices.json`, który wczytuje strona. Jeśli PSE nie odpowie albo dane są nieprawidłowe, strona zostaje przy ostatnich dobrych danych.

Poziom cen (średnie miesięczne) pochodzi z `data/tge_monthly.json`, który uzupełniam ręcznie z komunikatów TGE, bo TGE nie udostępnia darmowego API.

## Czego nie uwzględnia
Opłat za przekroczenie mocy zamówionej, kosztu zmiany mocy w trakcie roku, strefowych taryf poza prostą dopłatą szczytową, zmiennej pogody w poszczególnych dniach, wymiany baterii po okresie analizy i wartości końcowej magazynu. Cena RCE to nie dokładnie cena giełdowa RDN. Kwoty są netto, bez VAT.

## Technologia
Czysty HTML, CSS i JavaScript (jeden plik, bez serwera), skrypt aktualizujący w Pythonie (tylko biblioteka standardowa), GitHub Actions i GitHub Pages.

## O projekcie
Zbudowałem to z pomocą AI (Claude). Zakres modelu, źródła danych i założenia wybierałem i sprawdzałem sam, a aktualizację cen utrzymuję samodzielnie. Projekt powstał jako część mojej nauki branży OZE i magazynów energii.


