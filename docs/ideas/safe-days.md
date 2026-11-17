# Ideas: Safe Days for Unprotected Sex

Theme: whether the product should answer "can I have unprotected sex today, and
when are the next safe days" — and how to state the uncertainty honestly.

---

### I-009: Dni bezpieczne dla seksu bez zabezpieczenia — status dnia, prognoza i pewność

- **Status:** idea
- **Problem:** Produkt pokazuje okno płodne i wartość pewności, ale nie odpowiada
  wprost na pytanie, które użytkownik faktycznie zadaje: czy dzisiaj można
  uprawiać seks bez zabezpieczenia i kiedy wypadną takie dni. Użytkownik musi sam
  interpretować okna i nie widzi różnicy między „dzień poza oknem płodnym" a
  „dzień, który przy obecnej niepewności naprawdę można uznać za bezpieczny".
- **Idea:** Wyliczać dni bezpieczne jako dopełnienie okna płodnego — dla
  bieżącego cyklu i dla prognozowanych kolejnych cykli — i pokazywać trzy rzeczy:
  (1) status dnia: bezpieczny / niebezpieczny / nieznany, (2) najbliższe zakresy
  bezpiecznych dni z datami, (3) pewność lub prawdopodobieństwo dla każdego
  zakresu, jeśli da się je policzyć z istniejącej zmienności cykli.
- **Value:** Użytkownik dostaje odpowiedź na jedno pytanie zamiast dwóch okien do
  interpretacji, może ją pokazać na dashboardzie i oprzeć na niej automatyzację,
  a niepewność jest widoczna, zamiast ukryta za pojedynczą datą.
- **Constraints / conflicts:** **Konflikt z BDR-0004**, który wymaga, by
  okno płodne nie było czytane jako gwarancja antykoncepcyjna, a spec
  `cycle-prediction` opisuje je jako „an estimate that is not a contraceptive
  guarantee". Ta idea opiera się wprost na zastosowaniu antykoncepcyjnym, więc jej
  promocja wymaga nowego BDR (obietnica produktu, odpowiedzialność, copy), który
  zawęzi lub zastąpi tę zasadę — być może jako osobny tryb/nazwa, a nie przez
  przemianowanie okna płodnego. Przy cyklach nieregularnych wynik „brak dni
  bezpiecznych" musi być poprawnym, pokazywalnym stanem. Funkcja zależy od
  prognozy: poniżej dwóch użytecznych cykli status musi być `unknown`, nigdy
  domyślnie „bezpieczny". Obecne okno płodne (5 dni przed owulacją do dnia
  owulacji) to heurystyka kalendarzowa, nie zwalidowana metoda antykoncepcyjna —
  brak danych o temperaturze i śluzie, więc nie wolno sugerować inaczej.
  Prawdopodobieństwo per dzień może obiecywać więcej, niż dane uzasadniają.
  ADR-0001 (lokalnie, bez chmury) i ADR-0005/ADR-0006 (czysty, testowalny
  domenowy model) oznaczają, że wyliczenie zostaje w domenie jako funkcja
  czysta z `Clock`, bez zewnętrznego przetwarzania.
- **Dependencies:**
  - BDR-0004 (okna predykcji, okno płodne, pewność) — known
  - `add-cycle-prediction`
    (`openspec/changes/archive/2026-11-16-add-cycle-prediction/`) — known
  - BDR dopuszczający obietnicę antykoncepcyjną i jej wording — dependency unknown;
    **wymagany do wykonania przed promocją**: taki rekord nie istnieje w `docs/bdr/`
    i musi zostać napisany, zanim idea przejdzie dalej (decyduje o zakresie,
    odpowiedzialności i copy funkcji).
- **Open questions:** Czym dokładnie jest „dzień bezpieczny" — dopełnieniem okna
  płodnego, czy okna owulacji z dodatkowym marginesem zależnym od σ? Czy liczyć
  prawdopodobieństwo per dzień (np. z rozkładu przewidywanego startu w oknie
  niepewności), czy wystarczy werbalny pas pewności z BDR-0004? Jak pokazywać
  cykle bez żadnych dni bezpiecznych, żeby wynik nie wyglądał na błąd? Czy produkt
  może w ogóle używać słowa „bezpieczne", czy potrzebna jest inna nazwa i jak
  mocne zastrzeżenie? Gdzie to eksponować: atrybut istniejących sensorów, osobny
  `binary_sensor` na „dziś", encja kalendarza, karta? Czy potrzebne są dodatkowe
  dane (temperatura, śluz), żeby wynik był metodą antykoncepcyjną, czy funkcja
  pozostaje wyłącznie szacunkiem kalendarzowym? Jaki minimalny staż danych
  uprawnia do pokazywania statusu dnia?
- **Decision:** —
