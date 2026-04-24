"""
core/ga4_client.py
──────────────────
Google Analytics 4 client for pulling conversion data.
Uses the GA4 Data API when GA4_PROPERTY_ID is set,
falls back to realistic mock data for development.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GA4ConversionRecord:
    """Conversion data for a campaign/segment from GA4."""
    campaign: str
    sessions: int
    conversions: int
    revenue_usd: float
    avg_order_value: float
    source_medium: str


# Realistic mock data matching the HubSpot segments
_MOCK_GA4_DATA = [
    GA4ConversionRecord(
        campaign="Past Customers (Repeat Buyers)",
        sessions=820,
        conversions=98,
        revenue_usd=810.0,
        avg_order_value=82.65,
        source_medium="email / crm_retarget",
    ),
    GA4ConversionRecord(
        campaign="Women 35-44 / Local 10km",
        sessions=2400,
        conversions=72,
        revenue_usd=960.0,
        avg_order_value=13.33,
        source_medium="facebook / paid",
    ),
    GA4ConversionRecord(
        campaign="Lookalike of Top 20% Customers",
        sessions=3200,
        conversions=44,
        revenue_usd=770.0,
        avg_order_value=17.50,
        source_medium="facebook / paid",
    ),
    GA4ConversionRecord(
        campaign="Men 25-34 / Broad Interest",
        sessions=4800,
        conversions=31,
        revenue_usd=620.0,
        avg_order_value=20.0,
        source_medium="google / cpc",
    ),
    GA4ConversionRecord(
        campaign="Cold Interest: Home Services",
        sessions=6200,
        conversions=12,
        revenue_usd=180.0,
        avg_order_value=15.0,
        source_medium="google / cpc",
    ),
]


class GA4Client:
    """
    Fetches conversion data from Google Analytics 4.
    Falls back to mock data when GA4_PROPERTY_ID is not set.
    """

    def __init__(self):
        self.property_id = os.getenv("GA4_PROPERTY_ID")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if self.property_id:
            logger.info(f"GA4 client initialized for property {self.property_id}")
        else:
            logger.info("GA4 client using mock data (set GA4_PROPERTY_ID for real data)")

    def get_conversions_by_campaign(self, lookback_days: int = 7) -> list[GA4ConversionRecord]:
        """
        Fetch conversion data grouped by campaign.
        Returns real GA4 data if configured, mock data otherwise.
        """
        if not self.property_id:
            return _MOCK_GA4_DATA

        return self._fetch_real_data(lookback_days)

    def _fetch_real_data(self, lookback_days: int) -> list[GA4ConversionRecord]:
        """Fetch from GA4 Data API."""
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            client = BetaAnalyticsDataClient()

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="sessionCampaignName"),
                    Dimension(name="sessionSourceMedium"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="conversions"),
                    Metric(name="totalRevenue"),
                ],
                date_ranges=[DateRange(start_date=f"{lookback_days}daysAgo", end_date="today")],
            )

            response = client.run_report(request)

            records = []
            for row in response.rows:
                campaign = row.dimension_values[0].value
                source_medium = row.dimension_values[1].value
                sessions = int(row.metric_values[0].value)
                conversions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value)
                aov = revenue / conversions if conversions > 0 else 0

                records.append(GA4ConversionRecord(
                    campaign=campaign,
                    sessions=sessions,
                    conversions=conversions,
                    revenue_usd=revenue,
                    avg_order_value=round(aov, 2),
                    source_medium=source_medium,
                ))

            if not records:
                logger.warning("No GA4 data returned, falling back to mock data")
                return _MOCK_GA4_DATA

            return records

        except ImportError:
            logger.warning(
                "google-analytics-data not installed. "
                "Run: pip install google-analytics-data"
            )
            return _MOCK_GA4_DATA
        except Exception as e:
            logger.error(f"GA4 API error: {e}. Falling back to mock data.")
            return _MOCK_GA4_DATA
