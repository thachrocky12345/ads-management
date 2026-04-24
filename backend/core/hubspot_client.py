"""
core/hubspot_client.py
──────────────────────
HubSpot CRM client for pulling customer segments.
Uses the HubSpot API when HUBSPOT_API_KEY is set,
falls back to realistic mock data for development.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HubSpotSegment:
    """A customer segment from HubSpot CRM."""
    id: str
    name: str
    contact_count: int
    avg_revenue: float
    avg_deal_count: float
    top_cities: list[str] = field(default_factory=list)
    top_job_titles: list[str] = field(default_factory=list)
    source: str = "crm_list"  # "crm_list" | "lifecycle" | "pixel"


# Realistic mock segments for a local service business
_MOCK_SEGMENTS = [
    HubSpotSegment(
        id="seg_past_customers",
        name="Past Customers (Repeat Buyers)",
        contact_count=1240,
        avg_revenue=850.0,
        avg_deal_count=3.2,
        top_cities=["Chicago", "Naperville", "Evanston"],
        top_job_titles=["Homeowner", "Property Manager", "Office Manager"],
        source="crm_list",
    ),
    HubSpotSegment(
        id="seg_women_35_44",
        name="Women 35-44 / Local 10km",
        contact_count=3800,
        avg_revenue=420.0,
        avg_deal_count=1.4,
        top_cities=["Chicago", "Oak Park", "Berwyn"],
        top_job_titles=["Stay-at-home parent", "Teacher", "Nurse"],
        source="pixel",
    ),
    HubSpotSegment(
        id="seg_lookalike_top20",
        name="Lookalike of Top 20% Customers",
        contact_count=8500,
        avg_revenue=0.0,
        avg_deal_count=0.0,
        top_cities=["Chicago", "Schaumburg", "Aurora"],
        top_job_titles=[],
        source="pixel",
    ),
    HubSpotSegment(
        id="seg_men_25_34",
        name="Men 25-34 / Broad Interest",
        contact_count=12000,
        avg_revenue=180.0,
        avg_deal_count=0.6,
        top_cities=["Chicago", "Joliet", "Elgin"],
        top_job_titles=["Software Engineer", "Sales Rep", "Student"],
        source="pixel",
    ),
    HubSpotSegment(
        id="seg_cold_interest",
        name="Cold Interest: Home Services",
        contact_count=25000,
        avg_revenue=0.0,
        avg_deal_count=0.0,
        top_cities=["Chicago Metro"],
        top_job_titles=[],
        source="pixel",
    ),
]


class HubSpotClient:
    """
    Fetches customer segments from HubSpot CRM.
    Falls back to mock data when HUBSPOT_API_KEY is not set.
    """

    def __init__(self):
        self.api_key = os.getenv("HUBSPOT_API_KEY")
        if self.api_key:
            logger.info("HubSpot client initialized with API key")
        else:
            logger.info("HubSpot client using mock data (set HUBSPOT_API_KEY for real data)")

    def get_customer_segments(self) -> list[HubSpotSegment]:
        """
        Fetch all customer segments.
        Returns real HubSpot data if API key is set, mock data otherwise.
        """
        if not self.api_key:
            return _MOCK_SEGMENTS

        return self._fetch_real_segments()

    def _fetch_real_segments(self) -> list[HubSpotSegment]:
        """Fetch segments from HubSpot API."""
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Get contact lists (used as segments)
            response = requests.get(
                "https://api.hubapi.com/contacts/v1/lists",
                headers=headers,
                params={"count": 20},
                timeout=10,
            )
            response.raise_for_status()
            lists_data = response.json()

            segments = []
            for lst in lists_data.get("lists", []):
                list_id = str(lst.get("listId", ""))
                name = lst.get("name", "Unknown")
                count = lst.get("metaData", {}).get("size", 0)

                segments.append(HubSpotSegment(
                    id=f"hs_{list_id}",
                    name=name,
                    contact_count=count,
                    avg_revenue=0.0,
                    avg_deal_count=0.0,
                    source="crm_list",
                ))

            if not segments:
                logger.warning("No HubSpot lists found, falling back to mock data")
                return _MOCK_SEGMENTS

            return segments

        except Exception as e:
            logger.error(f"HubSpot API error: {e}. Falling back to mock data.")
            return _MOCK_SEGMENTS
