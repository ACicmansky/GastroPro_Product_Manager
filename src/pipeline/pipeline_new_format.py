"""
Complete pipeline for new 138-column format.
Integrates all components: XML parsing, merging, category mapping, transformation.
"""

from typing import Dict, Tuple, Optional
import pandas as pd

from src.pipeline.pipeline import Pipeline
from src.pipeline.strategies.new_format_strategy import NewFormatStrategy


class PipelineNewFormat(Pipeline):
    """Complete pipeline for new format data processing."""

    def __init__(self, config: Dict, options: Dict):
        """
        Initialize pipeline with configuration.

        Args:
            config: Configuration dictionary from config.json
            options: Options from GUI
        """
        super().__init__(NewFormatStrategy(config, options))
