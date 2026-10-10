"""Load ad/page pairs from CSV/Excel, validate them and match them to HTML snapshots.

The input schema is configurable: column names are matched case-insensitively against the
alias lists below, so ``Headline 1``, ``ad_headlines`` or ``headlines`` all work.
Multiple headlines/descriptions in one cell are separated by ``|`` or a newline.
Numbered columns (``headline_1``, ``headline_2``, ...) are also supported.
"""
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import pandas as pd

from schemas import AdPair

logger = logging.getLogger(__name__)

COLUMN_ALIASES: Dict[str, List[str]] = {
    "pair_id": ["pair_id", "pairid", "id", "pair"],
    "headlines": ["ad_headlines", "headlines", "headline", "ad_headline"],
    "descriptions": ["ad_descriptions", "descriptions", "description", "ad_description", "ad_text", "body"],
    "landing_page_url": ["landing_page_url", "landing_page", "url", "final_url", "page_url"],
    "snapshot_file": ["snapshot_file", "snapshot", "html_file", "snapshot_path", "html"],
}
REQUIRED = {"headlines": "at least one ad headline column"}


class DataValidationError(Exception):
    pass


@dataclass
class LoadResult:
    pairs: List[AdPair] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)      # rows that were rejected / fatal problems
    warnings: List[str] = field(default_factory=list)
    column_map: Dict[str, str] = field(default_factory=dict)


def _norm_col(name) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def split_multi(value) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [p.strip() for p in re.split(r"\r?\n|\|", str(value)) if p.strip()]


def read_table(source: Union[str, Path, bytes, io.BytesIO], filename: Optional[str] = None) -> pd.DataFrame:
    name = (filename or (str(source) if isinstance(source, (str, Path)) else "")).lower()
    if isinstance(source, bytes):
        source = io.BytesIO(source)
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(source, dtype=str).fillna("")
    if name.endswith((".csv", ".txt", "")):
        return pd.read_csv(source, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    raise DataValidationError(f"Unsupported file type: {filename or source}. Use .csv or .xlsx.")


def load_pairs(source, filename: Optional[str] = None) -> LoadResult:
    """Read a table and convert every valid row into an ``AdPair``."""
    res = LoadResult()
    try:
        df = read_table(source, filename)
    except DataValidationError as exc:
        res.errors.append(str(exc))
        return res
    except Exception as exc:  # unreadable / corrupt file
        res.errors.append(f"Could not read the file: {exc}")
        return res
    if df.empty:
        res.errors.append("The file contains no rows.")
        return res

    cols = {_norm_col(c): c for c in df.columns}

    def find(field_name: str) -> Optional[str]:
        for alias in COLUMN_ALIASES[field_name]:
            if alias in cols:
                return cols[alias]
        return None

    pid_col, desc_col = find("pair_id"), find("descriptions")
    head_col, url_col, snap_col = find("headlines"), find("landing_page_url"), find("snapshot_file")
    head_numbered = [orig for n, orig in cols.items() if re.fullmatch(r"(ad_)?headline_?\d+", n)]
    desc_numbered = [orig for n, orig in cols.items() if re.fullmatch(r"(ad_)?description_?\d+", n)]
    res.column_map = {k: v for k, v in {"pair_id": pid_col, "headlines": head_col,
                                        "descriptions": desc_col, "landing_page_url": url_col,
                                        "snapshot_file": snap_col}.items() if v}
    if not head_col and not head_numbered:
        res.errors.append("Missing required column: ad headlines (accepted names: "
                          + ", ".join(COLUMN_ALIASES["headlines"]) + ", or headline_1, headline_2, ...).")
        return res
    if not url_col and not snap_col and not pid_col:
        res.errors.append("Missing a way to find each landing page: add landing_page_url, "
                          "snapshot_file or pair_id (pair_id is matched to <pair_id>.html).")
        return res
    if not pid_col:
        res.warnings.append("No pair_id column found; IDs were generated (pair_001, pair_002, ...). "
                            "Snapshots will only match if snapshot_file is given.")

    seen = set()
    for i, row in df.iterrows():
        line = i + 2  # header is line 1
        pid = str(row[pid_col]).strip() if pid_col else ""
        if not pid:
            pid = f"pair_{i + 1:03d}"
        heads = split_multi(row[head_col]) if head_col else []
        heads += [h for c in head_numbered for h in split_multi(row[c])]
        descs = split_multi(row[desc_col]) if desc_col else []
        descs += [d for c in desc_numbered for d in split_multi(row[c])]
        url = str(row[url_col]).strip() if url_col else ""
        snap = str(row[snap_col]).strip() if snap_col else ""
        problems = []
        if not heads:
            problems.append("no ad headline")
        if pid in seen:
            problems.append(f"duplicate pair_id '{pid}'")
        if url and urlparse(url).scheme not in ("http", "https"):
            problems.append(f"landing_page_url '{url}' must start with http:// or https://")
        if not url and not snap and not pid_col:
            problems.append("no landing_page_url or snapshot_file")
        if problems:
            res.errors.append(f"Row {line} (pair '{pid}'): " + "; ".join(problems))
            continue
        seen.add(pid)
        res.pairs.append(AdPair(pair_id=pid, ad_headlines=heads, ad_descriptions=descs,
                                landing_page_url=url or None, snapshot_file=snap or None))
    if not descs_any(res.pairs):
        res.warnings.append("No ad descriptions found; only headlines will be audited.")
    return res


def descs_any(pairs: List[AdPair]) -> bool:
    return any(p.ad_descriptions for p in pairs)


# ------------------------------------------------------------------ snapshots
def _inside(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def resolve_snapshots(pairs: List[AdPair], snapshot_dir: Union[str, Path]
                      ) -> Tuple[Dict[str, Optional[Path]], Dict[str, str], List[str]]:
    """Match each pair to a snapshot file.

    Returns (paths, errors, unused_files). Order of preference: explicit ``snapshot_file``,
    then ``<pair_id>.html`` / ``.htm``. Paths that escape ``snapshot_dir`` are rejected.
    """
    base = Path(snapshot_dir)
    paths: Dict[str, Optional[Path]] = {}
    errors: Dict[str, str] = {}
    files = {p.name.lower(): p for p in base.rglob("*") if p.suffix.lower() in (".html", ".htm")} \
        if base.is_dir() else {}
    used = set()
    for pair in pairs:
        found: Optional[Path] = None
        if pair.snapshot_file:
            cand = base / pair.snapshot_file
            if not _inside(base, cand):
                errors[pair.pair_id] = f"Snapshot path '{pair.snapshot_file}' is outside the snapshot folder."
            elif cand.is_file():
                found = cand
            elif Path(pair.snapshot_file).name.lower() in files:
                found = files[Path(pair.snapshot_file).name.lower()]
            else:
                errors[pair.pair_id] = f"Snapshot file '{pair.snapshot_file}' was not found in {base}."
        else:
            for ext in (".html", ".htm"):
                key = f"{pair.pair_id}{ext}".lower()
                if key in files:
                    found = files[key]
                    break
            if not found:
                errors[pair.pair_id] = (f"No snapshot found for pair '{pair.pair_id}' "
                                        f"(looked for {pair.pair_id}.html in {base}).")
        paths[pair.pair_id] = found
        if found:
            used.add(found.name.lower())
    unused = sorted(n for n in files if n not in used)
    return paths, errors, unused


def extract_snapshot_zip(data: bytes, dest: Union[str, Path]) -> List[str]:
    """Safely extract an uploaded snapshot bundle (blocks zip-slip). Returns extracted names."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = dest / member.filename
            if not _inside(dest, target):
                logger.warning("Skipping unsafe zip member %s", member.filename)
                continue
            if target.suffix.lower() not in (".html", ".htm", ".json"):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(member))
            names.append(member.filename)
    return names


def read_snapshot(path: Union[str, Path]) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")
