from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings, with paths resolved independently of the current shell."""

    project_root: Path
    data_dir: Path
    start_date: date = date(2015, 1, 1)

    @classmethod
    def from_env(cls) -> Settings:
        project_root = Path(__file__).resolve().parents[2]
        configured_data_dir = os.environ.get("NSE_LAKE_DATA_DIR")
        data_dir = (
            Path(configured_data_dir).expanduser().resolve()
            if configured_data_dir
            else project_root / "data"
        )
        return cls(project_root=project_root, data_dir=data_dir)


SETTINGS = Settings.from_env()
