"""Shared constants for the KBSteel ERP."""

STAGE_ORDER = ["fabrication", "painting", "dispatch"]
STAGE_FLOW = {"fabrication": "painting", "painting": "dispatch", "dispatch": None}
VALID_REASON_CODES = ["cutting_waste", "defect", "damage", "overrun", "leftover"]
LOW_STOCK_THRESHOLD = 0.15  # 15%
SCRAP_LOSS_RATE_PER_KG = 50  # INR
