"""Text normalization, date parsing, contact extraction, and PII anonymization."""

import re
from datetime import datetime
from typing import Tuple, Optional, Dict, Any


MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


class DocumentNormalizer:
    """Normalizes unstructured text, extracts contact metadata, and computes timelines."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Sanitize whitespace, non-standard bullets, and control characters."""
        text = re.sub(r"[\r\t\f]", " ", text)
        text = re.sub(r"[•‣◦⁃∙▪▫]", "\n- ", text)
        text = re.sub(r" +", " ", text)
        return text.strip()

    @staticmethod
    def extract_contact_info(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract candidate name, email, and phone."""
        # Email
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        email = email_match.group(0) if email_match else None

        # Phone
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        phone = phone_match.group(0) if phone_match else None

        # Name heuristic: First non-empty line
        name = None
        for line in text.splitlines():
            cleaned = re.sub(r"^[#\*\-\s]+", "", line).strip()
            if cleaned and not cleaned.lower().startswith(("http", "email", "phone", "location", "summary")) and "@" not in cleaned:
                tokens = cleaned.split()
                if len(tokens) in [2, 3, 4] and len(cleaned) < 50:
                    name = cleaned
                    break

        return name, email, phone

    @staticmethod
    def parse_date_range(date_str: str) -> Tuple[str, str, int]:
        """
        Parse date range like 'Jan 2020 - Dec 2022' or '2019 - Present'.
        Returns (start_iso, end_iso, duration_months).
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        cleaned = date_str.lower().strip()
        parts = re.split(r"\s*(?:[-–—]|\bto\b)\s*", cleaned)
        if len(parts) == 1:
            parts = [parts[0], "present"]

        start_raw = parts[0].strip()
        end_raw = parts[1].strip() if len(parts) > 1 else "present"

        start_yr, start_mo = DocumentNormalizer._parse_single_date(start_raw, default_year=2020, default_mo=1)
        if any(k in end_raw for k in ["present", "current", "now"]):
            end_yr, end_mo = current_year, current_month
            end_iso = "Present"
        else:
            end_yr, end_mo = DocumentNormalizer._parse_single_date(end_raw, default_year=current_year, default_mo=current_month)
            end_iso = f"{end_yr:04d}-{end_mo:02d}"

        duration_months = max(1, (end_yr - start_yr) * 12 + (end_mo - start_mo))
        start_iso = f"{start_yr:04d}-{start_mo:02d}"

        return start_iso, end_iso, duration_months

    @staticmethod
    def _parse_single_date(date_token: str, default_year: int, default_mo: int) -> Tuple[int, int]:
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", date_token)
        year = int(year_match.group(0)) if year_match else default_year

        month = default_mo
        for m_name, m_num in MONTH_MAP.items():
            if re.search(rf"\b{m_name}\b", date_token):
                month = m_num
                break

        return year, month

    @staticmethod
    def anonymize_profile(text: str, candidate_id: str) -> str:
        """Replace personally identifiable information for unbiased blind screening."""
        anonymized = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
        anonymized = re.sub(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]", anonymized)
        anonymized = re.sub(r"https?://\S+", "[LINK_REDACTED]", anonymized)
        return anonymized
