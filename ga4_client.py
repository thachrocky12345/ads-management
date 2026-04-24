"""
core/ga4_client.py
───────────────────
Google Analytics 4 data fetcher.
Pulls conversion events and revenue by audience segment / campaign.

Setup:
  1. Create a Service Account in Google Cloud Console
  2. Grant it "Viewer" access to your GA4 property
  3. Download the JSON key → set GA4_CREDENTIALS_PATH
  4. Enable the "Google Analytics Data API" in your GCP project
"""

import os
import logging
from datetime import date, timedelta
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GA4ConversionRecord:
    segment_id:        str     # Maps to audience segment (e.g. campaign source)
    campaign:          str
    source_medium:     str
    sessions:          int
    conversions:       int
    revenue_usd:       float
    avg_order_value:   float
    date_range:        str


class GA4Client:
    """
    Wraps the Google Analytics Data API v1.
    Fetches conversion + revenue data for a given date range.

    Falls back to demo data if credentials not configured —
    so you can develop without a live GA4 property.
    """

    def __init__(self):
        self._property_id = os.getenv("GA4_PROPERTY_ID", "")
        self._creds_path  = os.getenv("GA4_CREDENTIALS_PATH", "")
        self._client      = None
        self._demo_mode   = False
        self._init_client()

    def _init_client(self):
        if not self._property_id or not self._creds_path:
            logger.warning(
                "GA4 credentials not configured "
                "(GA4_PROPERTY_ID or GA4_CREDENTIALS_PATH missing). "
                "Running in DEMO MODE with realistic sample data."
            )
            self._demo_mode = True
            return

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                self._creds_path,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            self._client = BetaAnalyticsDataClient(credentials=credentials)
            logger.info(f"GA4 client initialised for property {self._property_id}")

        except Exception as e:
            logger.warning(f"GA4 init failed: {e}. Running in DEMO MODE.")
            self._demo_mode = True

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def get_conversions_by_campaign(
        self,
        lookback_days: int = 7,
    ) -> list[GA4ConversionRecord]:
        """
        Pull conversion events and revenue grouped by campaign/source.
        Maps to your audience segments via UTM campaign names.
        """
        if self._demo_mode:
            return self._demo_conversions(lookback_days)
        return self._fetch_live(lookback_days)

    def get_conversion_rate_by_audience(
        self,
        audience_names: list[str],
        lookback_days: int = 7,
    ) -> dict[str, float]:
        """
        Returns conversion rate (0.0–1.0) per audience name.
        Used by Audience Intel agent to score segment quality.
        """
        records = self.get_conversions_by_campaign(lookback_days)
        rates = {}
        for record in records:
            if record.campaign in audience_names:
                rate = (
                    record.conversions / record.sessions
                    if record.sessions > 0 else 0.0
                )
                rates[record.campaign] = round(rate, 4)
        return rates

    # ─────────────────────────────────────────
    # Live GA4 fetch
    # ─────────────────────────────────────────

    def _fetch_live(self, lookback_days: int) -> list[GA4ConversionRecord]:
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric,
        )

        end   = date.today()
        start = end - timedelta(days=lookback_days)
        date_range_str = f"{start} to {end}"

        request = RunReportRequest(
            property=self._property_id,
            dimensions=[
                Dimension(name="sessionCampaignName"),
                Dimension(name="sessionSourceMedium"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="totalRevenue"),
                Metric(name="averageSessionDuration"),
            ],
            date_ranges=[DateRange(
                start_date=str(start),
                end_date=str(end),
            )],
        )

        response = self._client.run_report(request)
        records  = []

        for i, row in enumerate(response.rows):
            campaign      = row.dimension_values[0].value
            source_medium = row.dimension_values[1].value
            sessions      = int(row.metric_values[0].value)
            conversions   = int(row.metric_values[1].value)
            revenue       = float(row.metric_values[2].value)
            aov           = revenue / conversions if conversions > 0 else 0.0

            records.append(GA4ConversionRecord(
                segment_id=f"seg_{i+1}",
                campaign=campaign,
                source_medium=source_medium,
                sessions=sessions,
                conversions=conversions,
                revenue_usd=round(revenue, 2),
                avg_order_value=round(aov, 2),
                date_range=date_range_str,
            ))

        logger.info(f"GA4: fetched {len(records)} campaign records")
        return records

    # ─────────────────────────────────────────
    # Demo data — realistic SMB numbers
    # ─────────────────────────────────────────

    def _demo_conversions(self, lookback_days: int) -> list[GA4ConversionRecord]:
        end   = date.today()
        start = end - timedelta(days=lookback_days)
        dr    = f"{start} to {end}"

        return [
            GA4ConversionRecord("seg_1", "past_customers_email",    "email / crm",           420,   38, 3_800.00, 100.00, dr),
            GA4ConversionRecord("seg_2", "website_retarget_30d",    "paid_social / meta",   1_240,   52, 4_160.00,  80.00, dr),
            GA4ConversionRecord("seg_3", "lookalike_top5pct",       "paid_social / meta",   4_100,   41, 3_485.00,  85.00, dr),
            GA4ConversionRecord("seg_4", "local_radius_search",     "paid_search / google", 2_800,   28, 2_800.00, 100.00, dr),
            GA4ConversionRecord("seg_5", "cold_interest_homedecor", "paid_social / meta",   6_200,   12,   960.00,  80.00, dr),
            GA4ConversionRecord("seg_6", "linkedin_office_mgr",     "paid_social / linkedin", 180,    3,   540.00, 180.00, dr),
        ]
