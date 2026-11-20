"""File Cleanup Tool: review a messy folder visually, plan a clean structure, copy it safely."""

__version__ = "0.1.0"

from .apply import ApplyReport, apply_plan, check_destination  # noqa: E402
from .errors import CleanupError  # noqa: E402
from .explorer import build_page  # noqa: E402
from .plan import Plan, PlanItem, read_plan  # noqa: E402
from .rules import RuleSet, load_rules, parse_rules, suggest  # noqa: E402
from .scanner import ScanResult, read_inventory, scan, write_inventory  # noqa: E402

__all__ = [
    "__version__", "ApplyReport", "CleanupError", "Plan", "PlanItem", "RuleSet", "ScanResult",
    "apply_plan", "build_page", "check_destination", "load_rules", "parse_rules", "read_inventory",
    "read_plan", "scan", "suggest", "write_inventory",
]
