"""A small messy folder to practise on."""
from __future__ import annotations

import os

from .errors import CleanupError

DEMO = {
    "Finance/Budget 2024 FINAL.xlsx": 48, "Finance/Budget 2024 FINAL (1).xlsx": 48, "Finance/Budget 2024 FINAL_v2.xlsx": 52,
    "Finance/Budget 2023.xlsx": 44, "Finance/Old/Budget 2021.xlsx": 40, "Finance/Old/Budget 2022.xlsx": 41,
    "Finance/Invoices/inv-001.pdf": 120, "Finance/Invoices/inv-002.pdf": 118, "Finance/Invoices/inv-002 copy.pdf": 118,
    "Finance/Travel/Ottawa trip Oct 2025/receipt1.pdf": 80, "Finance/Travel/Ottawa trip Oct 2025/claim.xlsx": 30,
    "Finance/Travel/Toronto trip/receipt1.pdf": 75, "Finance/Travel/Toronto trip/claim.xlsx": 31,
    "Contracts/ACME-001/contract.docx": 220, "Contracts/ACME-001/contract signed.pdf": 540,
    "Contracts/ACME-001/Archive/contract draft v1.docx": 210, "Contracts/ACME-002/contract.docx": 230,
    "Contracts/ACME-002/statement of work.docx": 90, "Contracts/BETA-010/contract.pdf": 600,
    "Contracts/BETA-010/amendment 1.pdf": 110, "Contracts/misc/templates/contract template.docx": 60,
    "Meeting notes/2025-01 kickoff.docx": 25, "Meeting notes/2025-02 review.docx": 27, "Meeting notes/2025-03 review.docx": 26,
    "Meeting notes/untitled.docx": 5, "Meeting notes/Copy of 2025-03 review.docx": 26,
    "Misc/new folder/photo1.jpg": 900, "Misc/new folder/photo1 (1).jpg": 900, "Misc/stuff.txt": 1,
    "Misc/Presentation FINAL FINAL.pptx": 2400, "Misc/Presentation FINAL.pptx": 2300, "Reports/Q1 report.docx": 150,
    "Reports/Q2 report.docx": 160, "Reports/Q3 report.docx": 158, "Reports/Q3 report - Copy.docx": 158,
    "readme.txt": 1, "Archive/old plan.docx": 70,
}


def make_demo(root: str) -> int:
    """Create the practice folder at root (must be empty or missing). Returns the file count."""
    if os.path.exists(root) and os.listdir(root):
        raise CleanupError(f"{root} already exists and is not empty.")
    for rel, kb in DEMO.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        seed = rel.rsplit(" copy", 1)[0].replace(" (1)", "").replace(" - Copy", "").encode()
        with open(p, "wb") as f:
            f.write((seed * (kb * 1024 // max(len(seed), 1) + 1))[: kb * 1024])
    return len(DEMO)
