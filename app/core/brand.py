from __future__ import annotations

# Centralized branding so it can be reused in UI + packaging.

APP_NAME = "HD Supply - LOCPRIORITY Upload Builder"

DEPARTMENT = "IPR Department"
MANAGER = "Elliot Chen"
DEVELOPER = "Ben F. Benjamaa"

# Simple, embedded SVG logo (no external asset required).
# Colors are driven by theme: black background with yellow accents.
LOGO_SVG = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg width=\"320\" height=\"80\" viewBox=\"0 0 320 80\" xmlns=\"http://www.w3.org/2000/svg\">
  <rect x=\"0\" y=\"0\" width=\"320\" height=\"80\" rx=\"12\" fill=\"#000000\"/>
  <rect x=\"10\" y=\"10\" width=\"60\" height=\"60\" rx=\"10\" fill=\"#FFD200\"/>
  <path d=\"M24 28h32v8H24zM24 44h32v8H24z\" fill=\"#000000\"/>
  <text x=\"86\" y=\"36\" font-family=\"Segoe UI, Arial\" font-size=\"22\" font-weight=\"700\" fill=\"#FFD200\">HD Supply</text>
  <text x=\"86\" y=\"60\" font-family=\"Segoe UI, Arial\" font-size=\"14\" font-weight=\"600\" fill=\"#FFD200\">LOCPRIORITY Upload Builder</text>
</svg>
"""
