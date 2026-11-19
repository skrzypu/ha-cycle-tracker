#!/usr/bin/env python3
"""Build clean zip and tar.gz packages of the Cycle Tracker integration.

Run from anywhere: python3 .opencode/skills/ha-package/scripts/build.py
The version is read from the integration manifest; this script never edits it.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[4]
SRC = ROOT / "custom_components" / "cycle_tracker"
OUT = Path("/tmp/opencode")

# The archive root is the integration directory itself: the documented install
# command extracts with `tar -xzf ... -C /config/custom_components`.
PREFIX = "cycle_tracker/"
REQUIRED = (
    "cycle_tracker/manifest.json",
    "cycle_tracker/www/cycle-tracker-card.js",
    "cycle_tracker/translations/en.json",
    "cycle_tracker/translations/pl.json",
    "cycle_tracker/brand/icon.png",
)


def members() -> list[tuple[Path, str]]:
    files = [
        p
        for p in SRC.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
        and p.name != ".DS_Store"
    ]
    return sorted((p, PREFIX + p.relative_to(SRC).as_posix()) for p in files)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(archive: zipfile.ZipFile | tarfile.TarFile, names: set[str], files: list[tuple[Path, str]]) -> None:
    missing = set(REQUIRED) - names
    assert not missing, f"missing required entries: {sorted(missing)}"
    assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)
    if isinstance(archive, zipfile.ZipFile):
        for path, name in files:
            assert archive.read(name) == path.read_bytes(), name
    else:
        for path, name in files:
            assert archive.extractfile(name).read() == path.read_bytes(), name


def main() -> None:
    version = json.loads((SRC / "manifest.json").read_text())["version"]
    files = members()
    names = {name for _, name in files}
    zip_path = OUT / f"ha-cycle-tracker-{version}.zip"
    tar_path = OUT / f"ha-cycle-tracker-{version}.tar.gz"
    note_path = OUT / f"INSTALL_{version}.md"
    OUT.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, name in files:
            zf.write(path, name)
        check(zf, set(zf.namelist()), files)

    with tarfile.open(tar_path, "w:gz") as tf:
        for path, name in files:
            tf.add(path, name, recursive=False)
    with tarfile.open(tar_path, "r:gz") as tf:
        check(tf, set(tf.getnames()), files)

    note = f"""# Cycle Tracker {version} — paczka testowa

**Zip:** `{zip_path}`
**SHA-256 (zip):** `{sha256(zip_path)}`

**Tar:** `{tar_path}`
**SHA-256 (tar.gz):** `{sha256(tar_path)}`

**Wersja:** `{version}` (z `custom_components/cycle_tracker/manifest.json`)

## Instalacja

Archiwum zawiera tylko katalog `cycle_tracker/` (bez prefiksu
`custom_components/`), więc rozpakowanie trafia prosto do
`/config/custom_components/cycle_tracker/`.

1. Zatrzymaj Home Assistant i zrób kopię
   `/config/custom_components/cycle_tracker/`.
2. Kopiowanie:

   ```
   scp -O {tar_path} hassio@192.168.0.215:/tmp/
   ```

3. Rozpakowanie na HA:

   ```
   tar -xzf /tmp/ha-cycle-tracker-{version}.tar.gz -C /config/custom_components
   ```

4. Uruchom HA i sprawdź log pod kątem `cycle_tracker`.

Rollback: przywróć kopię z kroku 1 i zrestartuj HA. Dane w arkuszu Google
nie są modyfikowane przez paczkę.

## Karta i cache

Zasób karty ma adres `/cycle_tracker/cycle-tracker-card.js?v={version}`.
Jeśli HA miał już tę samą wersję, przeglądarka może pokazać starą kartę —
zrób twarde odświeżenie (Ctrl+Shift+R) albo wyczyść dane witryny.

## Co sprawdzić

- opcje istniejącego wpisu: „Okno historii" domyślnie 6, zakres 6–24;
- nowy wpis: okno historii domyślnie 12 w `entry.data`;
- wartości 5 i 25 są odrzucane;
- atrybut `lifetime_average_cycle_length` (28/10/30 → 29), outliery
  wykluczone, cykle sprzed gapy włączone;
- dwa wiersze w sekcji statystyk karty: „(okno)" i „(cała historia)";
- konfidencja ≈0.96 przy N=6 i ≈0.48 przy N=12;
- brak trzeciego serwisu i drugiego elementu karty.
"""
    note_path.write_text(note)

    print(f"version: {version}")
    print(f"files: {len(files)}")
    print(f"zip: {zip_path}  {sha256(zip_path)}")
    print(f"tar: {tar_path}  {sha256(tar_path)}")
    print(f"note: {note_path}")


if __name__ == "__main__":
    main()
