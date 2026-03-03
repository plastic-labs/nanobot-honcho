"""Lazy import bridge to plastic-vault pipeline."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.config import VaultConfig as PipelineVaultConfig
    from pipeline.pipeline import VaultPipeline

logger = logging.getLogger(__name__)

_pipeline: VaultPipeline | None = None


def get_pipeline() -> VaultPipeline | None:
    """Lazy-load the plastic-vault pipeline. Returns None if not installed."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from pipeline.config import VaultConfig as PipelineVaultConfig
        from pipeline.pipeline import VaultPipeline

        config = PipelineVaultConfig.from_env()
        _pipeline = VaultPipeline(config)
        return _pipeline
    except ImportError:
        logger.warning(
            "plastic-vault not installed. "
            "Install with: pip install -e /path/to/plastic-vault"
        )
        return None
    except Exception as e:
        logger.error("Failed to initialize vault pipeline: %s", e)
        return None
