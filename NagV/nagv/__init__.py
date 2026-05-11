"""NagV: WFM (SMT profile) → Nagini-verified Python pipeline."""

from .runtime_env import apply_nagv_gemini_defaults, apply_nagv_gemini_post_wfm_thinking

__all__ = ["apply_nagv_gemini_defaults", "apply_nagv_gemini_post_wfm_thinking", "__version__"]

__version__ = "0.1.0"
