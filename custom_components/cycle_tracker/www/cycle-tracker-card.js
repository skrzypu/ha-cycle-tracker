const DEFAULT_TITLE = "Cycle Tracker";
const NOT_TRACKED_TEXT = "brak danych";
const CONFIRM_END_TIMEOUT_MS = 5000;

const DEFAULT_ENTITIES = Object.freeze({
  cycle_day: "sensor.cycle_tracker_cycle_day",
  cycle_start: "sensor.cycle_tracker_cycle_start_date",
  cycle_phase: "sensor.cycle_tracker_cycle_phase",
  next_period: "sensor.cycle_tracker_next_period_date",
  next_ovulation: "sensor.cycle_tracker_next_ovulation_date",
  days_until_period: "sensor.cycle_tracker_days_until_period",
  days_until_ovulation: "sensor.cycle_tracker_days_until_ovulation",
  statistics: "sensor.cycle_tracker_statistics",
  fertility_estimate: "sensor.cycle_tracker_fertility_estimate",
  period_open: "binary_sensor.cycle_tracker_period_open",
});

const CT_DOMAIN = "cycle_tracker";

//: Stable suffix of each entity's ``unique_id`` (``<entry_id>_<suffix>``). The
//: card matches on it when a bound entity was renamed, so no entity_id string
//: has to be known by the user.
const CT_UNIQUE_SUFFIX = Object.freeze({
  cycle_day: "cycle_day",
  cycle_start: "cycle_start_date",
  cycle_phase: "cycle_phase",
  next_period: "next_period_date",
  next_ovulation: "next_ovulation_date",
  days_until_period: "days_until_period",
  days_until_ovulation: "days_until_ovulation",
  statistics: "statistics",
  fertility_estimate: "fertility_estimate",
  period_open: "period_open",
});

const ENTITY_LABELS = Object.freeze({
  cycle_day: "Dzień cyklu",
  cycle_start: "Początek cyklu",
  cycle_phase: "Faza cyklu",
  next_period: "Następny okres",
  next_ovulation: "Następna owulacja",
  days_until_period: "Dni do okresu",
  days_until_ovulation: "Dni do owulacji",
  statistics: "Statystyki",
  fertility_estimate: "Szacunek płodności",
  period_open: "Otwarty okres",
});

const MSG_CHOOSE_DEVICE =
  "Wybierz urządzenie Cycle Tracker w edytorze karty, aby karta wyświetliła dane.";
const MSG_NO_DEVICES =
  "Nie znaleziono urządzenia Cycle Tracker. Skonfiguruj najpierw integrację dla tej osoby.";

//: Small helpers shared by the card and its editor. hass.devices /
//: hass.entities may be undefined on older Home Assistant versions, so every
//: access is guarded and the config/device_registry / config/entity_registry /
//: config/area_registry websocket commands are used as a fallback.
function _collectionValues(collection) {
  if (Array.isArray(collection)) {
    return collection;
  }
  if (collection && typeof collection.values === "function") {
    return [...collection.values()];
  }
  return Object.values(collection || {});
}

//: ``config/*_registry/list`` answers with a bare array on current Home
//: Assistant versions and with a wrapped object on some older ones.
function _wsList(result, key) {
  if (Array.isArray(result)) {
    return result;
  }
  if (result && Array.isArray(result[key])) {
    return result[key];
  }
  return [];
}

async function _loadRegistries(hass) {
  const out = { devices: [], entities: [], areas: [] };
  if (!hass || typeof hass.callWS !== "function") {
    return out;
  }
  try {
    out.devices = hass.devices
      ? _collectionValues(hass.devices)
      : _wsList(
          await hass.callWS({ type: "config/device_registry/list" }),
          "devices"
        );
    out.entities = hass.entities
      ? _collectionValues(hass.entities)
      : _wsList(
          await hass.callWS({ type: "config/entity_registry/list" }),
          "entities"
        );
    out.areas = hass.areas
      ? _collectionValues(hass.areas)
      : _wsList(
          await hass.callWS({ type: "config/area_registry/list" }),
          "areas"
        );
  } catch (err) {
    // Registries are optional helpers. With them unavailable the card keeps
    // working with explicit overrides and legacy suffix matching.
  }
  return out;
}

function _cycleTrackerDevices(devices) {
  return (devices || []).filter(
    (device) =>
      device &&
      Array.isArray(device.identifiers) &&
      device.identifiers.some(
        (identifier) =>
          Array.isArray(identifier) && identifier[0] === CT_DOMAIN
      )
  );
}

function _areaMap(areas) {
  const map = {};
  for (const area of areas || []) {
    if (area && area.area_id) {
      map[area.area_id] = area.name;
    }
  }
  return map;
}

function _deviceDisplayName(device) {
  return (device && (device.name_by_user || device.name)) || "Cycle Tracker";
}

function _deviceLabel(device, areas) {
  const name = _deviceDisplayName(device);
  const areaId = device && device.area_id;
  const areaName = areaId && areas[areaId];
  return areaName ? `${name} — ${areaName}` : name;
}

function _deviceEntitiesMap(entities) {
  const map = {};
  for (const entry of entities || []) {
    if (!entry || !entry.device_id || !entry.entity_id) {
      continue;
    }
    if (!map[entry.device_id]) {
      map[entry.device_id] = [];
    }
    map[entry.device_id].push({
      entity_id: entry.entity_id,
      unique_id: entry.unique_id || "",
    });
  }
  return map;
}

const CONFIDENCE_BANDS = Object.freeze({
  low: "niska",
  medium: "średnia",
  high: "wysoka",
});

const PHASE_MAP = Object.freeze({
  menstrual: Object.freeze({
    name: "miesiączka",
    description:
      'dni krwawienia — to, co logujesz jako „okres" (od 1. dnia, przez 5 dni, domyślnie 5)',
  }),
  follicular: Object.freeze({
    name: "folikularna",
    description:
      "po krwawieniu, przed owulacją; organizm przygotowuje się do owulacji",
  }),
  ovulatory: Object.freeze({
    name: "owulacyjna",
    description:
      "okno płodne, wokół owulacji (środek 14 dni przed następnym okresem, ±2 dni)",
  }),
  luteal: Object.freeze({
    name: "lutealna",
    description: "po owulacji do następnego okresu",
  }),
});

//: Technical state tokens stay in the domain; all fertility wording lives here.
const FERTILITY_TEXT = Object.freeze({
  heading: "Szacunek płodności",
  state: Object.freeze({
    outside_estimated_fertile_window: "poza szacowanym oknem płodnym",
    within_estimated_fertile_window: "w szacowanym oknie płodnym",
    unknown: "brak danych",
  }),
  bandLabel: "pas szacunku",
  previousBandLabel: "poprzedni pas szacunku",
  nextBandLabel: "następny pas szacunku",
  endedLabel: "zakończył się",
  daysAgo: Object.freeze({
    singular: "dzień temu",
    plural: "dni temu",
  }),
  marginLabel: "margines",
  disclaimer:
    "Oparty na długościach Twoich cykli szacunek kalendarzowy. Nie jest metodą antykoncepcyjną i nie gwarantuje płodności ani jej braku. Decyzję o współżyciu podejmij samodzielnie, nie opierając się wyłącznie na tym szacunku.",
});

function _formatFertilityBand(band, marginDays) {
  if (!Array.isArray(band) || band.length !== 2) {
    return null;
  }
  if (typeof band[0] !== "string" || typeof band[1] !== "string") {
    return null;
  }
  const margin =
    typeof marginDays === "number" && Number.isFinite(marginDays)
      ? `, ${FERTILITY_TEXT.marginLabel} ${marginDays}`
      : "";
  return `${band[0]} — ${band[1]}${margin}`;
}

function _formatDaysAgo(days) {
  if (
    typeof days !== "number" ||
    !Number.isInteger(days) ||
    days < 0
  ) {
    return null;
  }
  // Prosta reguła: 1 (oraz 21, 31, …) → „dzień”, reszta → „dni”.
  const unit =
    days === 1 || (days % 10 === 1 && days % 100 !== 11)
      ? FERTILITY_TEXT.daysAgo.singular
      : FERTILITY_TEXT.daysAgo.plural;
  return `${FERTILITY_TEXT.endedLabel} ${days} ${unit}`;
}

const CARD_STYLES = `
  :host {
    display: block;
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
  }

  ha-card {
    background: var(--card-background-color, var(--ha-card-background));
    color: var(--primary-text-color);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .card-header {
    margin: 0;
    padding: 0;
    font-size: 1.25rem;
    font-weight: 600;
    line-height: 1.3;
    letter-spacing: -0.01em;
    color: var(--primary-text-color);
  }

  .card-header-caption {
    display: block;
    margin-top: 4px;
    font-size: 0.85rem;
    line-height: 1.35;
    color: var(--secondary-text-color);
  }

  .headlines {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .headline-box {
    background: var(--secondary-background-color);
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    padding: 12px 10px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 6px;
  }

  .headline-label {
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.25;
    min-height: 2.5em;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--secondary-text-color);
  }

  .headline-value {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .headline-value.not-tracked {
    font-size: 1rem;
    font-weight: 500;
    color: var(--secondary-text-color);
  }

  .headline-caption {
    font-size: 0.75rem;
    line-height: 1.3;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .headline-caption[hidden] {
    display: none;
  }

  .phase-box {
    padding: 12px 14px;
    border-radius: var(--ha-card-border-radius, 12px);
    border: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .phase-header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px;
    font-size: 0.95rem;
    line-height: 1.4;
  }

  .phase-label {
    font-weight: 500;
    color: var(--secondary-text-color);
  }

  .phase-name {
    font-weight: 600;
    color: var(--primary-color);
  }

  .phase-name.not-tracked {
    font-weight: 400;
    color: var(--secondary-text-color);
  }

  .phase-description {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.45;
    color: var(--secondary-text-color);
  }

  .phase-description[hidden] {
    display: none;
  }

  .dates-list {
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--divider-color);
    border-bottom: 1px solid var(--divider-color);
  }

  .date-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    padding: 10px 0;
    font-size: 0.925rem;
    line-height: 1.4;
  }

  .date-row + .date-row {
    border-top: 1px solid var(--divider-color);
  }

  .date-label {
    color: var(--secondary-text-color);
  }

  .date-value {
    font-weight: 600;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .date-value.not-tracked {
    font-weight: 400;
    color: var(--secondary-text-color);
  }

  .fertility-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 14px;
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--secondary-background-color);
  }

  .fertility-section[hidden] {
    display: none;
  }

  .fertility-heading {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1.3;
    color: var(--primary-text-color);
  }

  .fertility-fact {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 10px;
    font-size: 0.925rem;
    line-height: 1.4;
  }

  .fertility-state {
    font-weight: 600;
    color: var(--primary-color);
  }

  .fertility-band {
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  /* Each gap edge occupies its own line in the outside state. */
  .fertility-band.fertility-band-edge {
    flex-basis: 100%;
  }

  .fertility-state.not-tracked,
  .fertility-band.not-tracked {
    font-weight: 400;
    color: var(--secondary-text-color);
  }

  .fertility-disclaimer {
    margin: 0;
    padding-top: 8px;
    border-top: 1px solid var(--divider-color);
    font-size: 0.85rem;
    line-height: 1.45;
    color: var(--secondary-text-color);
  }

  /* Akordeon sekcji płodności — wzorzec na sekcji „Statystyki” (<details>/<summary>). */
  .fertility-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 0;
    margin: 0;
    font: inherit;
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1.3;
    color: var(--primary-text-color);
    background: transparent;
    border: none;
    cursor: pointer;
    user-select: none;
    text-align: left;
    list-style: none;
  }

  .fertility-summary::-webkit-details-marker {
    display: none;
  }

  .fertility-summary:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .fertility-summary-icon {
    display: inline-block;
    width: 1em;
    height: 1em;
    line-height: 1;
    transition: transform 0.2s ease;
    flex-shrink: 0;
  }

  .fertility-section[open] > .fertility-summary .fertility-summary-icon {
    transform: rotate(180deg);
  }

  .fertility-section[open] > .fertility-summary {
    border-bottom: 1px solid var(--divider-color);
    padding-bottom: 8px;
    margin-bottom: 8px;
  }

  .fertility-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 0 12px;
  }

  .actions-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .actions-section[hidden] {
    display: none;
  }

  .actions-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .action-btn {
    appearance: none;
    border: 1px solid var(--primary-color);
    border-radius: var(--ha-card-border-radius, 12px);
    padding: 10px 12px;
    font: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.3;
    cursor: pointer;
    background: var(--primary-color);
    color: var(--text-primary-color, var(--card-background-color));
    transition: opacity 0.15s ease, transform 0.1s ease;
    text-align: center;
  }

  .action-btn.secondary {
    background: transparent;
    color: var(--primary-color);
  }

  .action-btn.confirming {
    border-color: var(--error-color, var(--primary-color));
    background: var(--error-color, var(--primary-color));
    color: var(--text-primary-color, var(--card-background-color));
  }

  .action-btn:hover:not(:disabled) {
    opacity: 0.92;
  }

  .action-btn:active:not(:disabled) {
    transform: scale(0.99);
  }

  .action-btn:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .action-btn:disabled {
    cursor: not-allowed;
    border-color: var(--divider-color);
    background: var(--secondary-background-color);
    color: var(--disabled-text-color, var(--secondary-text-color));
    opacity: 0.65;
  }

  .status-region {
    min-height: 0;
    font-size: 0.85rem;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }

  .status-region:empty {
    display: none;
  }

  .status-region.error {
    color: var(--error-color, var(--primary-color));
    font-weight: 500;
  }

  .status-region.success {
    color: var(--success-color, var(--primary-color));
    font-weight: 500;
  }

  .stats-disclosure {
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--secondary-background-color);
    overflow: hidden;
  }

  .stats-summary {
    padding: 10px 14px;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--primary-text-color);
    cursor: pointer;
    user-select: none;
    list-style: disclosure-closed inside;
  }

  .stats-disclosure[open] > .stats-summary {
    list-style: disclosure-open inside;
    border-bottom: 1px solid var(--divider-color);
  }

  .stats-summary:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .stats-content {
    padding: 8px 14px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    font-size: 0.85rem;
    line-height: 1.4;
    padding: 4px 0;
  }

  .stat-label {
    color: var(--secondary-text-color);
  }

  .stat-value {
    font-weight: 600;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .stat-value.not-tracked,
  .stats-empty {
    font-weight: 400;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin: 0;
  }

  @media (max-width: 360px) {
    .headlines {
      grid-template-columns: 1fr;
    }

    .headline-label {
      min-height: 0;
    }

    .headline-value {
      font-size: 1.65rem;
    }

    .actions-row {
      grid-template-columns: 1fr;
    }

    .date-row,
    .stat-row {
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
    }

    .date-value,
    .stat-value {
      text-align: left;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .action-btn {
      transition: none;
    }

    .action-btn:active:not(:disabled) {
      transform: none;
    }
  }
`;

const EDITOR_STYLES = `
  :host {
    display: block;
    padding: 16px;
    font-family: var(--paper-font-body1_-_font-family, inherit);
    color: var(--primary-text-color);
    max-width: 640px;
  }

  .ct-editor {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .ct-editor-intro {
    margin: 0;
    font-size: 0.95rem;
    line-height: 1.5;
    color: var(--secondary-text-color);
  }

  .ct-editor-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ct-editor-field label {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .ct-editor-field select,
  .ct-editor-field input {
    font: inherit;
    font-size: 0.95rem;
    padding: 8px 10px;
    border-radius: 4px;
    border: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
  }

  .ct-hint {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.4;
    color: var(--secondary-text-color);
  }

  .ct-hint.warn {
    color: var(--error-color, var(--primary-color));
  }

  .ct-hint[hidden] {
    display: none;
  }

  summary {
    font: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    padding: 6px 0;
    color: var(--primary-text-color);
  }

  .ct-entity-overrides {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 8px;
  }

  .ct-entity-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ct-entity-row label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--secondary-text-color);
  }
`;

class CycleTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._entities = { ...DEFAULT_ENTITIES };
    this._hass = null;
    this._inFlight = false;
    this._confirmingEnd = false;
    this._confirmEndTimer = null;
    this._statusMessage = "";
    this._statusKind = "";
    this._deviceId = null;
    this._deviceName = null;
    this._ctDevices = [];
    this._areas = {};
    this._deviceEntities = {};
    this._explicitEntities = {};
    this._needsDeviceChoice = false;
    this._registriesLoaded = false;
    this._loadingRegistries = false;
    this._devicesRef = null;
    this._entitiesRef = null;
    this._domReady = false;
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid Cycle Tracker card configuration.");
    }

    const rawEntities =
      config.entities && typeof config.entities === "object"
        ? config.entities
        : {};

    this._explicitEntities = {};
    for (const key of Object.keys(DEFAULT_ENTITIES)) {
      const candidate = rawEntities[key];
      if (typeof candidate === "string" && candidate.trim() !== "") {
        this._explicitEntities[key] = candidate.trim();
      }
    }

    const deviceId =
      typeof config.device_id === "string" && config.device_id.trim() !== ""
        ? config.device_id.trim()
        : null;

    const title =
      typeof config.title === "string" && config.title.trim() !== ""
        ? config.title
        : DEFAULT_TITLE;

    const showActions = config.show_actions !== false;

    this._config = {
      ...config,
      title,
      show_actions: showActions,
      device_id: deviceId,
      entities: {},
    };
    this._deviceId = deviceId;
    this._entities = { ...DEFAULT_ENTITIES };
    this._deviceName = null;
    this._needsDeviceChoice = false;
    this._clearEndConfirmation();
    this._ensureDom();
    this._render();
    this._loadRegistries();
  }

  getConfigElement() {
    const editor = document.createElement("cycle-tracker-card-editor");
    if (this._hass) {
      editor.hass = this._hass;
    }
    editor.setConfig(
      this._config
        ? {
            device_id: this._config.device_id || null,
            entities: { ...this._explicitEntities },
          }
        : {}
    );
    return editor;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) {
      return;
    }
    this._ensureDom();
    this._render();
    // ``hass`` is replaced on every state change, so the registries are read
    // only on the first run and when Home Assistant swaps the registry
    // objects themselves (a device or area was added, renamed or moved).
    if (
      !this._registriesLoaded ||
      hass.devices !== this._devicesRef ||
      hass.entities !== this._entitiesRef
    ) {
      this._loadRegistries();
    }
  }

  get hass() {
    return this._hass;
  }

  getCardSize() {
    return 4;
  }

  disconnectedCallback() {
    this._clearEndConfirmation();
  }

  _ensureDom() {
    if (this._domReady) {
      return;
    }

    const style = document.createElement("style");
    style.textContent = CARD_STYLES;

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <h2 class="card-header" data-ref="title"></h2>
      <p class="card-header-caption" data-ref="deviceCaption" hidden></p>

      <div class="headlines">
        <div class="headline-box" data-field="cycle_day">
          <span class="headline-label">Dzień cyklu</span>
          <span class="headline-value" data-ref="cycleDayValue"></span>
          <span class="headline-caption" data-ref="cycleStartCaption" hidden></span>
        </div>
        <div class="headline-box" data-field="days_until_period">
          <span class="headline-label">Do okresu</span>
          <span class="headline-value" data-ref="daysUntilPeriodValue"></span>
        </div>
        <div class="headline-box" data-field="prediction_confidence">
          <span class="headline-label">Pewność prognozy</span>
          <span class="headline-value" data-ref="confidenceValue"></span>
          <span class="headline-caption" data-ref="confidenceBandCaption" hidden></span>
        </div>
      </div>

      <div class="phase-box" data-field="cycle_phase">
        <div class="phase-header">
          <span class="phase-label">Faza:</span>
          <span class="phase-name" data-ref="phaseName"></span>
        </div>
        <p class="phase-description" data-ref="phaseDescription" hidden></p>
      </div>

      <div class="dates-list">
        <div class="date-row" data-field="next_period">
          <span class="date-label">Następny okres (przewidywany)</span>
          <span class="date-value" data-ref="nextPeriodValue"></span>
        </div>
        <div class="date-row" data-field="next_ovulation">
          <span class="date-label">Następna owulacja (przewidywana)</span>
          <span class="date-value" data-ref="nextOvulationValue"></span>
        </div>
      </div>

      <div class="actions-section" data-ref="actionsSection">
        <div class="actions-row">
          <button
            type="button"
            class="action-btn primary"
            data-ref="startBtn"
          >
            Rozpocznij okres
          </button>
          <button
            type="button"
            class="action-btn secondary"
            data-ref="endBtn"
          >
            Zakończ okres
          </button>
        </div>
      </div>

      <div
        class="status-region"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        data-ref="statusRegion"
      ></div>

      <details class="stats-disclosure" data-ref="statsDetails">
        <summary class="stats-summary">Statystyki</summary>
        <div class="stats-content" data-ref="statsContent"></div>
      </details>

      <details
        class="fertility-section"
        data-field="fertility_estimate"
        data-ref="fertilitySection"
        hidden
      ></details>
    `;

    this.shadowRoot.replaceChildren(style, card);

    this._refs = {};
    for (const el of card.querySelectorAll("[data-ref]")) {
      this._refs[el.getAttribute("data-ref")] = el;
    }

    this._refs.startBtn.addEventListener("click", () => {
      this._handleStartClick();
    });

    this._refs.endBtn.addEventListener("click", () => {
      this._handleEndClick();
    });

    // Akordeon płodności: zsynchronizuj atrybut dostępności z natywnym stanem
    // <details> po przełączeniu przez użytkownika (klik/Enter/Space).
    this._refs.fertilitySection.addEventListener("toggle", () => {
      const summary = this._refs.fertilitySection.querySelector("summary");
      if (summary) {
        summary.setAttribute(
          "aria-expanded",
          String(this._refs.fertilitySection.open)
        );
      }
    });

    this._domReady = true;
  }

  _getEntityStateObj(key) {
    if (!this._hass || !this._hass.states) {
      return null;
    }
    const entityId = this._resolveEntityId(key);
    if (!entityId) {
      return null;
    }
    return this._hass.states[entityId] || null;
  }

  _resolveEntityId(key) {
    return this._entities[key] || null;
  }

  async _loadRegistries() {
    if (!this._hass || this._loadingRegistries) {
      return;
    }
    this._loadingRegistries = true;
    const hass = this._hass;
    try {
      const registries = await _loadRegistries(hass);
      this._ctDevices = _cycleTrackerDevices(registries.devices);
      this._areas = _areaMap(registries.areas);
      this._deviceEntities = _deviceEntitiesMap(registries.entities);
      this._registriesLoaded = true;
      this._devicesRef = hass.devices;
      this._entitiesRef = hass.entities;
      this._bindEntities();
      this._render();
    } finally {
      this._loadingRegistries = false;
    }
  }

  _bindEntities() {
    const devices = this._ctDevices;
    this._needsDeviceChoice = false;

    if (!this._deviceId) {
      if (devices.length === 1) {
        this._deviceId = devices[0].id;
        this._deviceName = _deviceDisplayName(devices[0]);
      } else if (devices.length > 1) {
        this._needsDeviceChoice = true;
      }
    } else {
      const selected = devices.find((device) => device.id === this._deviceId);
      this._deviceName = selected ? _deviceDisplayName(selected) : null;
      // A saved device_id that no longer resolves (device removed, registry
      // unavailable) must ask for a choice instead of rendering nothing.
      this._needsDeviceChoice = !selected;
    }

    const states = this._hass && this._hass.states;
    for (const key of Object.keys(DEFAULT_ENTITIES)) {
      this._entities[key] = this._resolveOne(key, states);
    }
  }

  _resolveOne(key, states) {
    const explicit = this._explicitEntities[key];
    if (explicit) {
      return explicit;
    }

    const deviceId = this._deviceId;
    if (deviceId) {
      const match = this._matchDeviceEntity(deviceId, key);
      if (match) {
        return match;
      }
      return null;
    }

    if (this._needsDeviceChoice) {
      return null;
    }

    const configured = DEFAULT_ENTITIES[key];
    if (states && states[configured]) {
      return configured;
    }

    // An entity_id can gain a prefix (an area or device name) when it is
    // created through the UI, so fall back to a suffix match in the same
    // domain and prefer the shortest match when several fit.
    const separator = configured.indexOf(".");
    if (separator < 0) {
      return configured;
    }
    const domain = configured.slice(0, separator + 1);
    const suffix = configured.slice(separator + 1);
    const candidates = Object.keys(states || {}).filter(
      (id) => id.startsWith(domain) && id.endsWith(suffix)
    );
    if (candidates.length === 0) {
      return configured;
    }
    candidates.sort(
      (left, right) => left.length - right.length || left.localeCompare(right)
    );
    return candidates[0];
  }

  _matchDeviceEntity(deviceId, key) {
    const candidates = this._deviceEntities[deviceId] || [];
    const configured = DEFAULT_ENTITIES[key];
    const separator = configured.indexOf(".");
    const suffix = separator < 0 ? configured : configured.slice(separator + 1);
    const byId = candidates.find((entry) =>
      entry.entity_id.endsWith(suffix)
    );
    if (byId) {
      return byId.entity_id;
    }
    // The entity may have been renamed arbitrarily. Its ``unique_id`` still
    // ends with the integration's stable suffix, which is what makes the
    // device binding independent of the visible name.
    const uniqueSuffix = CT_UNIQUE_SUFFIX[key];
    const byUniqueId = candidates.find(
      (entry) =>
        uniqueSuffix &&
        entry.unique_id &&
        entry.unique_id.endsWith(`_${uniqueSuffix}`)
    );
    return byUniqueId ? byUniqueId.entity_id : null;
  }

  _readTrackedState(key) {
    const stateObj = this._getEntityStateObj(key);
    if (!stateObj) {
      return { tracked: false, value: NOT_TRACKED_TEXT, stateObj: null };
    }
    const raw = stateObj.state;
    if (
      raw === undefined ||
      raw === null ||
      raw === "" ||
      raw === "unknown" ||
      raw === "unavailable"
    ) {
      return { tracked: false, value: NOT_TRACKED_TEXT, stateObj };
    }
    return { tracked: true, value: String(raw), stateObj };
  }

  _isPeriodOpen() {
    const stateObj = this._getEntityStateObj("period_open");
    return Boolean(stateObj && stateObj.state === "on");
  }

  _getLocalTodayDate() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  _clearEndConfirmation() {
    if (this._confirmEndTimer !== null) {
      clearTimeout(this._confirmEndTimer);
      this._confirmEndTimer = null;
    }
    this._confirmingEnd = false;
  }

  _setStatus(message, kind) {
    this._statusMessage = message || "";
    this._statusKind = kind || "";
    if (this._refs && this._refs.statusRegion) {
      this._renderStatus();
    }
  }

  _extractErrorMessage(err) {
    if (!err) {
      return "Nie udało się zapisać zmiany.";
    }
    if (typeof err === "string" && err.trim() !== "") {
      return err.trim();
    }
    if (typeof err.message === "string" && err.message.trim() !== "") {
      return err.message.trim();
    }
    if (
      err.body &&
      typeof err.body.message === "string" &&
      err.body.message.trim() !== ""
    ) {
      return err.body.message.trim();
    }
    return "Nie udało się zapisać zmiany.";
  }

  async _handleStartClick() {
    if (this._inFlight || !this._hass || this._isPeriodOpen()) {
      return;
    }
    this._clearEndConfirmation();
    const date = this._getLocalTodayDate();
    await this._callCycleService("log_start", date, "Zapisano początek okresu.");
  }

  async _handleEndClick() {
    if (this._inFlight || !this._hass || !this._isPeriodOpen()) {
      return;
    }

    if (!this._confirmingEnd) {
      this._confirmingEnd = true;
      this._setStatus("Kliknij ponownie w ciągu 5 sekund, aby potwierdzić zakończenie okresu.", "");
      this._renderActions();
      this._confirmEndTimer = setTimeout(() => {
        this._confirmEndTimer = null;
        this._confirmingEnd = false;
        if (
          this._statusMessage ===
          "Kliknij ponownie w ciągu 5 sekund, aby potwierdzić zakończenie okresu."
        ) {
          this._setStatus("", "");
        }
        this._renderActions();
      }, CONFIRM_END_TIMEOUT_MS);
      return;
    }

    this._clearEndConfirmation();
    const date = this._getLocalTodayDate();
    await this._callCycleService("log_end", date, "Zapisano koniec okresu.");
  }

  async _callCycleService(serviceName, date, successText) {
    this._inFlight = true;
    this._renderActions();

    try {
      await this._hass.callService("cycle_tracker", serviceName, { date });
      this._setStatus(successText, "success");
    } catch (err) {
      const message = this._extractErrorMessage(err);
      this._setStatus(`Błąd: ${message}`, "error");
    } finally {
      this._inFlight = false;
      this._render();
    }
  }

  _render() {
    if (!this._domReady || !this._config) {
      return;
    }

    this._refs.title.textContent = this._config.title;

    // The seeded multi-person dashboard already titles each card with the
    // device name, so the caption only adds information when the title differs.
    const showDeviceCaption =
      Boolean(this._deviceName) && this._deviceName !== this._config.title;
    this._refs.deviceCaption.textContent = showDeviceCaption
      ? this._deviceName
      : "";
    this._refs.deviceCaption.hidden = !showDeviceCaption;

    const cycleDay = this._readTrackedState("cycle_day");
    this._refs.cycleDayValue.textContent = cycleDay.value;
    this._refs.cycleDayValue.classList.toggle("not-tracked", !cycleDay.tracked);

    const cycleStart = this._readTrackedState("cycle_start");
    if (cycleStart.tracked) {
      this._refs.cycleStartCaption.textContent = `od ${cycleStart.value}`;
      this._refs.cycleStartCaption.hidden = false;
    } else {
      this._refs.cycleStartCaption.textContent = "";
      this._refs.cycleStartCaption.hidden = true;
    }

    const daysUntilPeriod = this._readTrackedState("days_until_period");
    this._refs.daysUntilPeriodValue.textContent = daysUntilPeriod.value;
    this._refs.daysUntilPeriodValue.classList.toggle(
      "not-tracked",
      !daysUntilPeriod.tracked
    );

    const statsState = this._readTrackedState("statistics");
    const statsAttrs =
      statsState.tracked && statsState.stateObj
        ? statsState.stateObj.attributes || {}
        : {};
    const rawConfidence = statsAttrs.prediction_confidence;
    const hasConfidence =
      statsState.tracked &&
      rawConfidence !== undefined &&
      rawConfidence !== null &&
      rawConfidence !== "" &&
      rawConfidence !== "unknown" &&
      rawConfidence !== "unavailable" &&
      !Number.isNaN(Number(rawConfidence));

    if (hasConfidence) {
      this._refs.confidenceValue.textContent = `${Math.round(Number(rawConfidence) * 100)}%`;
      this._refs.confidenceValue.classList.remove("not-tracked");
      const rawBand = statsAttrs.confidence_band;
      const bandLabel =
        typeof rawBand === "string" ? CONFIDENCE_BANDS[rawBand] : null;
      if (bandLabel) {
        this._refs.confidenceBandCaption.textContent = bandLabel;
        this._refs.confidenceBandCaption.hidden = false;
      } else {
        this._refs.confidenceBandCaption.textContent = "";
        this._refs.confidenceBandCaption.hidden = true;
      }
    } else {
      this._refs.confidenceValue.textContent = NOT_TRACKED_TEXT;
      this._refs.confidenceValue.classList.add("not-tracked");
      this._refs.confidenceBandCaption.textContent = "";
      this._refs.confidenceBandCaption.hidden = true;
    }

    const phaseState = this._readTrackedState("cycle_phase");
    const phaseInfo = phaseState.tracked ? PHASE_MAP[phaseState.value] : null;
    if (phaseInfo) {
      this._refs.phaseName.textContent = phaseInfo.name;
      this._refs.phaseName.classList.remove("not-tracked");
      this._refs.phaseDescription.textContent = phaseInfo.description;
      this._refs.phaseDescription.hidden = false;
    } else {
      this._refs.phaseName.textContent = NOT_TRACKED_TEXT;
      this._refs.phaseName.classList.add("not-tracked");
      this._refs.phaseDescription.textContent = "";
      this._refs.phaseDescription.hidden = true;
    }

    const nextPeriod = this._readTrackedState("next_period");
    this._refs.nextPeriodValue.textContent = nextPeriod.value;
    this._refs.nextPeriodValue.classList.toggle(
      "not-tracked",
      !nextPeriod.tracked
    );

    const nextOvulation = this._readTrackedState("next_ovulation");
    this._refs.nextOvulationValue.textContent = nextOvulation.value;
    this._refs.nextOvulationValue.classList.toggle(
      "not-tracked",
      !nextOvulation.tracked
    );

    this._renderActions();
    this._renderStatus();
    this._renderStatistics();
    this._renderFertility();
  }

  _renderActions() {
    if (!this._refs) {
      return;
    }

    const showActions = this._config ? this._config.show_actions !== false : true;
    this._refs.actionsSection.hidden = !showActions;
    if (!showActions) {
      return;
    }

    const hasHass = Boolean(this._hass);
    const periodOpen = this._isPeriodOpen();

    if (!periodOpen && this._confirmingEnd) {
      this._clearEndConfirmation();
    }

    const startDisabled = !hasHass || this._inFlight || periodOpen;
    const endDisabled = !hasHass || this._inFlight || !periodOpen;

    this._refs.startBtn.disabled = startDisabled;
    this._refs.endBtn.disabled = endDisabled;

    this._refs.endBtn.textContent = this._confirmingEnd
      ? "Na pewno zakończyć?"
      : "Zakończ okres";
    this._refs.endBtn.classList.toggle("confirming", this._confirmingEnd);
  }

  _renderStatus() {
    if (!this._refs || !this._refs.statusRegion) {
      return;
    }
    const region = this._refs.statusRegion;
    if (this._needsDeviceChoice) {
      region.textContent = MSG_CHOOSE_DEVICE;
      region.className = "status-region error";
      return;
    }
    region.textContent = this._statusMessage;
    region.classList.toggle("error", this._statusKind === "error");
    region.classList.toggle("success", this._statusKind === "success");
  }

  _renderStatistics() {
    if (!this._refs || !this._refs.statsContent) {
      return;
    }

    const statsState = this._readTrackedState("statistics");
    const container = this._refs.statsContent;
    container.replaceChildren();

    if (!statsState.tracked || !statsState.stateObj) {
      const empty = document.createElement("p");
      empty.className = "stats-empty";
      empty.textContent = NOT_TRACKED_TEXT;
      container.appendChild(empty);
      return;
    }

    const attrs = statsState.stateObj.attributes || {};

    const formatNumeric = (val, digits = 0) => {
      if (val === undefined || val === null || val === "") {
        return { text: NOT_TRACKED_TEXT, tracked: false };
      }
      const num = Number(val);
      if (Number.isNaN(num)) {
        return { text: NOT_TRACKED_TEXT, tracked: false };
      }
      return {
        text: num.toLocaleString(undefined, {
          minimumFractionDigits: 0,
          maximumFractionDigits: digits,
        }),
        tracked: true,
      };
    };

    const rows = [
      {
        key: "average_cycle_length",
        label: "Średnia długość cyklu (okno)",
        formatted: formatNumeric(attrs.average_cycle_length, 1),
      },
      {
        key: "lifetime_average_cycle_length",
        label: "Średnia długość cyklu (cała historia)",
        formatted: formatNumeric(attrs.lifetime_average_cycle_length, 1),
      },
      {
        key: "average_period_length",
        label: "Średnia długość okresu",
        formatted: formatNumeric(attrs.average_period_length, 1),
      },
      {
        key: "total_cycles_tracked",
        label: "Liczba śledzonych cykli",
        formatted: formatNumeric(attrs.total_cycles_tracked, 0),
      },
    ];

    for (const item of rows) {
      const row = document.createElement("div");
      row.className = "stat-row";
      row.setAttribute("data-stat", item.key);

      const labelEl = document.createElement("span");
      labelEl.className = "stat-label";
      labelEl.textContent = item.label;

      const valueEl = document.createElement("span");
      valueEl.className = item.formatted.tracked
        ? "stat-value"
        : "stat-value not-tracked";
      valueEl.textContent = item.formatted.text;

      row.appendChild(labelEl);
      row.appendChild(valueEl);
      container.appendChild(row);
    }
  }

  _renderFertility() {
    if (!this._refs || !this._refs.fertilitySection) {
      return;
    }
    const section = this._refs.fertilitySection;
    const entityId = this._resolveEntityId("fertility_estimate");
    const stateObj =
      entityId && this._hass && this._hass.states
        ? this._hass.states[entityId] || null
        : null;

    // The entity is only created when the option is on. Without a bound entity
    // there is no section at all, never an empty or "unavailable" block.
    if (!entityId || !stateObj) {
      section.replaceChildren();
      section.hidden = true;
      return;
    }

    section.hidden = false;
    section.replaceChildren();

    const summary = document.createElement("summary");
    summary.className = "fertility-summary";
    summary.setAttribute("aria-expanded", String(section.open));
    summary.setAttribute("aria-controls", "fertility-estimate-panel");

    const heading = document.createElement("span");
    heading.className = "fertility-heading";
    heading.textContent = FERTILITY_TEXT.heading;
    summary.appendChild(heading);

    const icon = document.createElement("span");
    icon.className = "fertility-summary-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "▾";
    summary.appendChild(icon);

    const content = document.createElement("div");
    content.className = "fertility-content";
    content.id = "fertility-estimate-panel";

    const label = FERTILITY_TEXT.state[stateObj.state];
    const attrs = stateObj.attributes || {};
    const isOutside = stateObj.state === "outside_estimated_fertile_window";
    // "unknown" implies no window and no band, so none is shown beside it.
    // In "outside" the two gap edges replace the single unlabelled band; a
    // missing edge produces no line at all rather than an empty row.
    const band =
      label && !isOutside && stateObj.state !== "unknown"
        ? _formatFertilityBand(attrs.margin_band, attrs.margin_days)
        : null;
    const gapEdges = isOutside
      ? [
          {
            key: "previous_margin_band",
            label: FERTILITY_TEXT.previousBandLabel,
            band: attrs.previous_margin_band,
            daysAgo: _formatDaysAgo(attrs.previous_band_days_ago),
          },
          {
            key: "next_margin_band",
            label: FERTILITY_TEXT.nextBandLabel,
            band: attrs.next_margin_band,
          },
        ]
      : [];

    const fact = document.createElement("div");
    fact.className = "fertility-fact";
    fact.setAttribute("data-field", "fertility_state");

    const stateEl = document.createElement("span");
    stateEl.className = label
      ? "fertility-state"
      : "fertility-state not-tracked";
    stateEl.textContent = label || FERTILITY_TEXT.state.unknown;
    fact.appendChild(stateEl);

    if (isOutside) {
      for (const edge of gapEdges) {
        const formatted = _formatFertilityBand(edge.band, attrs.margin_days);
        if (!formatted) {
          continue;
        }
        const edgeEl = document.createElement("div");
        edgeEl.className = "fertility-band fertility-band-edge";
        edgeEl.setAttribute("data-field", edge.key);
        const suffix = edge.daysAgo ? `, ${edge.daysAgo}` : "";
        edgeEl.textContent = `${edge.label}: ${formatted}${suffix}`;
        fact.appendChild(edgeEl);
      }
    } else if (band) {
      const bandEl = document.createElement("span");
      bandEl.className = "fertility-band";
      bandEl.textContent = `${FERTILITY_TEXT.bandLabel}: ${band}`;
      fact.appendChild(bandEl);
    }
    content.appendChild(fact);

    const disclaimer = document.createElement("p");
    disclaimer.className = "fertility-disclaimer";
    disclaimer.textContent = FERTILITY_TEXT.disclaimer;
    content.appendChild(disclaimer);

    section.appendChild(summary);
    section.appendChild(content);
  }
}

if (!customElements.get("cycle-tracker-card")) {
  customElements.define("cycle-tracker-card", CycleTrackerCard);
}

class CycleTrackerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._rawConfig = {};
    this._config = { device_id: null, entities: {} };
    this._domReady = false;
    this._devicesLoaded = false;
    this._loadingDevices = false;
    this._devicesRef = null;
    this._entitiesRef = null;
    this._ctDevices = [];
    this._areas = {};
    this._commitTimer = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  get hass() {
    return this._hass;
  }

  setConfig(config) {
    this._rawConfig = { ...(config || {}) };
    this._config = {
      device_id:
        config &&
        typeof config.device_id === "string" &&
        config.device_id.trim() !== ""
          ? config.device_id.trim()
          : null,
      entities: {
        ...(config && typeof config.entities === "object" ? config.entities : {}),
      },
    };
    this._update();
  }

  _setConfig(config) {
    this.setConfig(config);
  }

  _update() {
    if (!this._hass) {
      return;
    }
    this._ensureDom();
    this._render();
    if (
      !this._devicesLoaded ||
      this._hass.devices !== this._devicesRef ||
      this._hass.entities !== this._entitiesRef
    ) {
      this._loadDevices();
    }
  }

  _ensureDom() {
    if (this._domReady) {
      return;
    }

    const style = document.createElement("style");
    style.textContent = EDITOR_STYLES;

    const container = document.createElement("div");
    container.className = "ct-editor";
    container.innerHTML = `
      <p class="ct-editor-intro">
        Karta pokazuje dane jednego urządzenia Cycle Tracker. Wybierz
        urządzenie, do którego należy osoba — encje dobierają się same.
      </p>

      <div class="ct-editor-field">
        <label>Urządzenie</label>
        <select data-ref="deviceSelect">
          <option value="">— wybierz urządzenie —</option>
        </select>
      </div>
      <p class="ct-hint" data-ref="deviceHint"></p>

      <details class="ct-editor-field ct-editor-advanced">
        <summary>Zaawansowane — ręczny wybór encji</summary>
        <div class="ct-entity-overrides" data-ref="overridesContainer"></div>
      </details>
    `;

    this.shadowRoot.replaceChildren(style, container);

    this._refs = {};
    for (const el of container.querySelectorAll("[data-ref]")) {
      this._refs[el.getAttribute("data-ref")] = el;
    }

    this._refs.deviceSelect.addEventListener("change", () => {
      this._commit();
    });

    this._buildOverrides();
    this._domReady = true;
  }

  _buildOverrides() {
    const container = this._refs.overridesContainer;
    if (!container) {
      return;
    }
    container.replaceChildren();
    this._overrideInputs = {};

    for (const key of Object.keys(DEFAULT_ENTITIES)) {
      const row = document.createElement("div");
      row.className = "ct-entity-row";

      const label = document.createElement("label");
      label.textContent = ENTITY_LABELS[key];
      row.appendChild(label);

      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = DEFAULT_ENTITIES[key];
      input.value = this._config.entities[key] || "";
      input.addEventListener("input", () => {
        const value = input.value.trim();
        if (value !== "") {
          this._config.entities[key] = value;
        } else {
          delete this._config.entities[key];
        }
        this._commit();
      });
      row.appendChild(input);
      container.appendChild(row);
      this._overrideInputs[key] = input;
    }
  }

  _syncOverrides() {
    // The rows are built once: rebuilding them on every state change would
    // recreate the focused input and swallow keystrokes.
    for (const key of Object.keys(DEFAULT_ENTITIES)) {
      const input = this._overrideInputs && this._overrideInputs[key];
      if (!input || input === this.shadowRoot.activeElement) {
        continue;
      }
      const value = this._config.entities[key] || "";
      if (input.value !== value) {
        input.value = value;
      }
    }
  }

  async _loadDevices() {
    if (!this._hass || this._loadingDevices) {
      return;
    }
    this._loadingDevices = true;
    const hass = this._hass;
    try {
      const registries = await _loadRegistries(hass);
      this._ctDevices = _cycleTrackerDevices(registries.devices);
      this._areas = _areaMap(registries.areas);
      this._devicesLoaded = true;
      this._devicesRef = hass.devices;
      this._entitiesRef = hass.entities;
      this._render();
    } finally {
      this._loadingDevices = false;
    }
  }

  _render() {
    if (!this._domReady || !this._hass) {
      return;
    }

    const select = this._refs.deviceSelect;
    const current = this._config.device_id || null;

    select.innerHTML = '<option value="">— wybierz urządzenie —</option>';
    for (const device of this._ctDevices) {
      const option = document.createElement("option");
      option.value = device.id;
      option.textContent = _deviceLabel(device, this._areas);
      if (device.id === current) {
        option.selected = true;
      }
      select.appendChild(option);
    }

    const hint = this._refs.deviceHint;
    if (this._ctDevices.length === 0) {
      hint.textContent = MSG_NO_DEVICES;
      hint.className = "ct-hint warn";
      hint.hidden = false;
    } else if (this._ctDevices.length > 1 && !current) {
      hint.textContent =
        "Jest kilka urządzeń Cycle Tracker — wybierz jedno, aby karta wiedziała, czyje dane pokazywać.";
      hint.className = "ct-hint warn";
      hint.hidden = false;
    } else {
      hint.hidden = true;
    }

    this._syncOverrides();
  }

  _commit() {
    const select = this._refs.deviceSelect;
    this._config.device_id = select.value || null;
    clearTimeout(this._commitTimer);
    this._commitTimer = setTimeout(() => {
      // Emit the whole configuration so that options the visual editor does not
      // expose (title, show_actions, ...) survive an edit.
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: {
            config: {
              ...this._rawConfig,
              device_id: this._config.device_id,
              entities: { ...this._config.entities },
            },
          },
          bubbles: true,
          composed: true,
        })
      );
    }, 300);
  }
}

if (!customElements.get("cycle-tracker-card-editor")) {
  customElements.define("cycle-tracker-card-editor", CycleTrackerCardEditor);
}

window.customCards = window.customCards || [];
if (
  !window.customCards.some((card) => card && card.type === "cycle-tracker-card")
) {
  window.customCards.push({
    type: "cycle-tracker-card",
    name: "Cycle Tracker Card",
    description:
      "Polish menstrual cycle stat card with one-tap period start and end logging.",
    preview: false,
  });
}
