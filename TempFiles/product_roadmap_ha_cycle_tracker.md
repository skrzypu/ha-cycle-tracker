# Product Roadmap: Home Assistant Menstrual Cycle Tracker Integration

**Produkt:** Custom Component dla Home Assistant (`custom_components/cycle_tracker`)  
**Architektura:** Open Spec Kit + HACS  
**Rola:** Product Owner / Home Assistant Integration Specialist  

---

## 1. Wizja Produktu & Cel
Stworzenie prywatnej, lokalnej i w pełni zintegrowanej z ekosystemem Home Assistant wtyczki do śledzenia cyklu menstruacyjnego. Wtyczka ma nie tylko gromadzić dane i przewidywać fazy cyklu, ale również wykorzystywać możliwości inteligentnego domu do podnoszenia komfortu życia użytkowniczki.

---

## 2. Architektura Open Spec Kit
Projekt prowadzony jest w oparciu o Open Spec Kit w repozytorium GitHub.

### Struktura Repozytorium:
```text
ha-cycle-tracker/
├── .github/
│   └── workflows/          # CI/CD (HACS validation, pytest, linting)
├── custom_components/
│   └── cycle_tracker/      # Kod źródłowy komponentu
│       ├── __init__.py
│       ├── manifest.json
│       ├── sensor.py
│       ├── calendar.py
│       └── services.yaml
├── specs/                  # Open Spec Kit
│   ├── core_entities.spec.yaml
│   ├── prediction_engine.spec.yaml
│   ├── integrations.spec.yaml
│   └── automations_api.spec.yaml
├── hacs.json
└── README.md
```

---

## 3. Fazy Wdrożenia (Roadmap)

### Faza 1: Core Integration & MVP (HACS & Podstawowe Logowanie)
**Cel:** Stworzenie stabilnego fundamentu wtyczki działającego w HACS oraz natywnej możliwości rejestrowania startu i końca menstruacji.

* **Integracja z HACS & Repozytorium GitHub:**
  * Wdrożenie wymogów HACS (`hacs.json`, `manifest.json`, repozytorium GitHub z odpowiednimi tagami wersji).
  * Konfiguracja przepływu konfiguracji (Config Flow) z poziomu UI Home Assistant.
* **Model Danych & Encje HA:**
  * `sensor.cycle_day` – obecny dzień cyklu (wartość numeryczna).
  * `sensor.cycle_phase` – aktualna faza (`menstrual`, `follicular`, `ovulatory`, `luteal`).
  * `sensor.next_period_date` – prognozowana data kolejnej menstruacji.
  * `calendar.menstrual_cycle` – natywna integracja z kalendarzem HA do wizualizacji przeszłych i przyszłych zdarzeń.
* **Proste Logowanie (UI & Usługi):**
  * Usługi wtyczki: `cycle_tracker.log_start` oraz `cycle_tracker.log_end`.
  * Dedykowany szablon karty Lovelace (Custom Dashboard Card) pozwalający na jedno-kliknięciowe oznaczanie początku/końca krwawienia.

---

### Faza 2: Algorytmy Predykcji & Rozszerzony Tracking
**Cel:** Wdrożenie zaawansowanych metod matematycznych do przewidywania cyklu oraz zbieranie dodatkowych wskaźników zdrowotnych.

* **Metodologie Predykcji:**
  * **Średnia arytmetyczna ($\mu$):**
    $$\mu = \frac{1}{N} \sum_{i=1}^{N} L_i$$
    gdzie $L_i$ to długość $i$-tego cyklu z ostatnich $N$ cykli (domyślnie $N=6$).
  * **Ważona średnia ruchoma (WMA):** Nadanie wyższej wagi nowszym cyklom w celu szybszej reakcji na zmiany w organizmie.
  * **Odchylenie standardowe ($\sigma$):**
    $$\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (L_i - \mu)^2}$$
    Wyznaczanie okna niepewności (np. $\pm \sigma$ dni od przewidywanego startu).
* **Dodatkowe Wskaźniki do Śledzenia:**
  * **Symptomy fizyczne:** Natężenie krwawienia (`spotting`, `light`, `medium`, `heavy`), poziom bólu (skala 1–5), skurcze, bóle głowy, zmiany skórne.
  * **Samopoczucie & Emocje:** Poziom energii, nastrój, jakość snu, poziom stresu.
  * **Biomarkery:** Bazalna temperatura ciała (BBT – współpraca z termometrami BLE/smart pierścieniami), jakość śluzu szyjkowego, wyniki testów LH (OPK).
  * **Leki i Antykoncepcja:** Rejestracja przyjmowania pigułek antykoncepcyjnych lub leków przeciwbólowych.

---

### Faza 3: Eksport Danych & Alertyzacja
**Cel:** Zapewnienie bezpieczeństwa danych poprzez kopie zapasowe oraz wdrożenie elastycznego systemu powiadomień.

* **Eksport do Google Drive:**
  * Automatyczny, szyfrowany backup danych historycznych w formacie `.json` lub `.csv` do wskazanego folderu na Dysk Google (integracja z Google Drive API / OAuth2).
  * Generator raportów w formacie PDF/CSV przygotowany pod kątem konsultacji lekarskich.
* **System Powiadomień i Alertyzacji:**
  * Zdarzenie HA (`cycle_tracker_period_upcoming`) emitowane na 3, 2 i 1 dzień przed prognozowanym dniem rozpoczęcia.
  * Wykorzystanie natywnego interfejsu `notify` (e-mail/SMTP, aplikacja mobilna HA, Telegram, Signal).
  * **Actionable Notifications (Powiadomienia interaktywne):**
    * Wysyłanie powiadomienia na telefon z pytaniem: *"Czy krwawienie się rozpoczęło?"* i przyciskami do szybkiej odpowiedzi (*Tak*, *Nie*, *Przesuń o 1 dzień*).

---

### Faza 4: Quality of Life (Automatyzacja & Ekosystem HA)
**Cel:** Wykorzystanie unikalnych możliwości Home Assistant do poprawy codziennego komfortu życia użytkowniczki.

| Obszar | Funkcja / Przypadek Użycia w Home Assistant |
| :--- | :--- |
| **Komfort Termiczny (HVAC)** | Automatyczne dostosowanie temperatury w sypialni (np. obniżenie o 1°C w fazie lutealnej/podczas uderzeń gorąca dla lepszego snu). |
| **Oświetlenie & Klimat** | Uruchamianie scen świetlnych w trybie relaksacyjnym (ciepłe, przyciemnione światło) przy wysoki poziomie bólu/zmęczenia. |
| **Integracja z Partnerem** | Dyskretny sensor statusu (np. `sensor.cycle_support_needed`) pozwalający na automatyczną zmianę przypomnień lub powiadomień dla partnera z zachowaniem prywatności. |
| **Treningi & Aktywność** | Rekomendacje treningowe zależne od fazy (np. faza pęcherzykowa = trening siłowy, faza lutealna/menstruacyjna = joga i regeneracja). |
| **Integracja ze Health Kit** | Dwukierunkowa synchronizacja z Apple Health / Google Fit poprzez aplikację mobilną Companion HA. |

---

## 4. Kryteria Akceptacji MVP (Definition of Done dla Fazy 1)
1. Repozytorium na GitHub posiada pełną strukturę specyfikacji Open Spec Kit.
2. Integrację można dodać do Home Assistant za pomocą własnego repozytorium HACS.
3. Użytkownik może wywołać usługi `log_start` oraz `log_end`, a dane zapisują się w lokalnej bazie HA.
4. Sensor `sensor.next_period_date` poprawnie kalkuluje datę na podstawie przynajmniej średniej z ostatnich 3 cykli.