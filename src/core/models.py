# src/core/models.py
from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd


@dataclass
class PipelineResult:
    """Data class to hold the results of the data processing pipeline."""

    dataframe: pd.DataFrame
    statistics: Dict[str, Any]
