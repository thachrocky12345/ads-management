"""
core/hubspot_client.py
───────────────────────
HubSpot CRM data fetcher.
Pulls contact lists, deal history, and lifecycle stages
to build audience segments for targeting.

Setup:
  1. HubSpot > Settings > Integrations > Private Apps
  2. Create app with scopes: crm.objects.contacts.read,
     crm.objects.deals.read, crm.lists.read
  3. Copy the access token → set HUBSPOT_ACCESS_TOKEN
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HubSpotContact:
    id:               str
    email:            str
    lifecycle_stage:  str    # "lead", "customer", "evangelist", etc.
    total_revenue:    float  # Sum of closed deals
    deal_count:       int
    last_activity:    str    # ISO date
    city:             str
    job_title:        str
    company:          str


@dataclass
class HubSpotSegment:
    id:             str
    name:           str
    contact_count:  int
    avg_revenue:    float
    avg_deal_count: float
    top_cities:     list[str]
    top_job_titles: list[str]
    source:         str     # "crm_list", "lifecycle", "deal_stage"


class HubSpotClient:
    """
    Pulls CRM data from HubSpot to build first-party audience segments.

    Falls back to demo data if token not set —
    safe for development without live HubSpot access.
    """

    def __init__(self):
        self._token      = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
        self._client     = None
        self._demo_mode  = False
        self._init_client()

    def _init_client(self):
        if not self._token:
            logger.warning(
                "HUBSPOT_ACCESS_TOKEN not set. Running in DEMO MODE."
            )
            self._demo_mode = True
            return

        try:
            import hubspot
            from hubspot.crm.contacts import ApiClient, Configuration

            config = Configuration(access_token=self._token)
            self._client = hubspot.Client.create(access_token=self._token)
            logger.info("HubSpot client initialised")

        except Exception as e:
            logger.warning(f"HubSpot init failed: {e}. Running in DEMO MODE.")
            self._demo_mode = True

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def get_customer_segments(self) -> list[HubSpotSegment]:
        """
        Build audience segments from HubSpot CRM data.
        Returns segments suitable for ad targeting.
        """
        if self._demo_mode:
            return self._demo_segments()
        return self._fetch_live_segments()

    def get_top_customers(self, limit: int = 100) -> list[HubSpotContact]:
        """
        Returns top customers by revenue — used for lookalike seed lists.
        """
        if self._demo_mode:
            return self._demo_top_customers(limit)
        return self._fetch_live_top_customers(limit)

    def get_contacts_by_lifecycle(
        self,
        stage: str,
        limit: int = 500,
    ) -> list[HubSpotContact]:
        """
        Pull contacts in a specific lifecycle stage.
        Stages: subscriber, lead, marketingqualifiedlead,
                salesqualifiedlead, opportunity, customer, evangelist
        """
        if self._demo_mode:
            return self._demo_lifecycle_contacts(stage, limit)
        return self._fetch_live_lifecycle(stage, limit)

    # ─────────────────────────────────────────
    # Live HubSpot fetch
    # ─────────────────────────────────────────

    def _fetch_live_segments(self) -> list[HubSpotSegment]:
        """
        Builds segments by grouping contacts from HubSpot lists.
        Requires crm.lists.read + crm.objects.contacts.read scopes.
        """
        from hubspot.crm.lists import SimplePublicObjectWithAssociations

        segments = []

        # Fetch all static and dynamic lists
        try:
            lists_api = self._client.crm.lists.lists_api
            response  = lists_api.get_all(limit=20)

            for hs_list in response.lists[:10]:   # Cap at 10 lists
                contacts = self._get_list_contacts(hs_list.list_id)
                if not contacts:
                    continue

                revenues  = [c.total_revenue for c in contacts if c.total_revenue > 0]
                cities    = self._top_n([c.city for c in contacts if c.city], 3)
                titles    = self._top_n([c.job_title for c in contacts if c.job_title], 3)

                segments.append(HubSpotSegment(
                    id=f"hs_{hs_list.list_id}",
                    name=hs_list.name,
                    contact_count=len(contacts),
                    avg_revenue=sum(revenues) / len(revenues) if revenues else 0.0,
                    avg_deal_count=sum(c.deal_count for c in contacts) / len(contacts),
                    top_cities=cities,
                    top_job_titles=titles,
                    source="crm_list",
                ))

        except Exception as e:
            logger.error(f"HubSpot list fetch failed: {e}")

        return segments

    def _get_list_contacts(self, list_id: str) -> list[HubSpotContact]:
        try:
            response = self._client.crm.contacts.basic_api.get_page(
                limit=100,
                properties=[
                    "email", "lifecyclestage", "city",
                    "jobtitle", "company", "hs_analytics_revenue",
                    "num_associated_deals", "notes_last_activity",
                ],
            )
            return [self._parse_contact(c) for c in response.results]
        except Exception as e:
            logger.warning(f"Contact fetch for list {list_id} failed: {e}")
            return []

    def _parse_contact(self, raw) -> HubSpotContact:
        props = raw.properties
        return HubSpotContact(
            id=raw.id,
            email=props.get("email", ""),
            lifecycle_stage=props.get("lifecyclestage", "lead"),
            total_revenue=float(props.get("hs_analytics_revenue") or 0),
            deal_count=int(props.get("num_associated_deals") or 0),
            last_activity=props.get("notes_last_activity", ""),
            city=props.get("city", ""),
            job_title=props.get("jobtitle", ""),
            company=props.get("company", ""),
        )

    def _fetch_live_top_customers(self, limit: int) -> list[HubSpotContact]:
        try:
            from hubspot.crm.contacts.models import Filter, FilterGroup, PublicObjectSearchRequest
            filter_group = FilterGroup(filters=[
                Filter(
                    property_name="lifecyclestage",
                    operator="EQ",
                    value="customer",
                )
            ])
            search_req = PublicObjectSearchRequest(
                filter_groups=[filter_group],
                sorts=[{"propertyName": "hs_analytics_revenue", "direction": "DESCENDING"}],
                limit=min(limit, 100),
                properties=["email","lifecyclestage","city","jobtitle","company",
                            "hs_analytics_revenue","num_associated_deals"],
            )
            response = self._client.crm.contacts.search_api.do_search(
                public_object_search_request=search_req
            )
            return [self._parse_contact(c) for c in response.results]
        except Exception as e:
            logger.error(f"HubSpot top customer fetch failed: {e}")
            return []

    def _fetch_live_lifecycle(self, stage: str, limit: int) -> list[HubSpotContact]:
        try:
            from hubspot.crm.contacts.models import Filter, FilterGroup, PublicObjectSearchRequest
            filter_group = FilterGroup(filters=[
                Filter(
                    property_name="lifecyclestage",
                    operator="EQ",
                    value=stage,
                )
            ])
            search_req = PublicObjectSearchRequest(
                filter_groups=[filter_group],
                limit=min(limit, 100),
                properties=["email","lifecyclestage","city","jobtitle","company",
                            "hs_analytics_revenue","num_associated_deals","notes_last_activity"],
            )
            response = self._client.crm.contacts.search_api.do_search(
                public_object_search_request=search_req
            )
            return [self._parse_contact(c) for c in response.results]
        except Exception as e:
            logger.error(f"HubSpot lifecycle fetch failed: {e}")
            return []

    # ─────────────────────────────────────────
    # Demo data — realistic SMB CRM
    # ─────────────────────────────────────────

    def _demo_segments(self) -> list[HubSpotSegment]:
        return [
            HubSpotSegment(
                id="hs_seg_1",
                name="Active Customers (purchased 90d)",
                contact_count=312,
                avg_revenue=480.0,
                avg_deal_count=2.4,
                top_cities=["Chicago", "Oak Park", "Evanston"],
                top_job_titles=["Homeowner", "Property Manager", "Office Manager"],
                source="crm_list",
            ),
            HubSpotSegment(
                id="hs_seg_2",
                name="High-Value Customers (LTV > $1000)",
                contact_count=87,
                avg_revenue=1_640.0,
                avg_deal_count=5.8,
                top_cities=["Chicago", "Naperville", "Wilmette"],
                top_job_titles=["Business Owner", "Director", "VP Operations"],
                source="crm_list",
            ),
            HubSpotSegment(
                id="hs_seg_3",
                name="Lapsed Customers (90–180d no purchase)",
                contact_count=204,
                avg_revenue=220.0,
                avg_deal_count=1.2,
                top_cities=["Chicago", "Schaumburg", "Aurora"],
                top_job_titles=["Homeowner", "Renter", "Manager"],
                source="lifecycle",
            ),
            HubSpotSegment(
                id="hs_seg_4",
                name="Marketing Qualified Leads",
                contact_count=891,
                avg_revenue=0.0,
                avg_deal_count=0.0,
                top_cities=["Chicago", "Joliet", "Rockford"],
                top_job_titles=["Homeowner", "Tenant", "Office Admin"],
                source="lifecycle",
            ),
        ]

    def _demo_top_customers(self, limit: int) -> list[HubSpotContact]:
        return [
            HubSpotContact(
                id=f"contact_{i}",
                email=f"customer{i}@example.com",
                lifecycle_stage="customer",
                total_revenue=2_000.0 - (i * 15),
                deal_count=max(1, 6 - (i // 10)),
                last_activity="2026-03-01",
                city="Chicago",
                job_title="Business Owner" if i % 3 == 0 else "Homeowner",
                company=f"Company {i}" if i % 3 == 0 else "",
            )
            for i in range(min(limit, 50))
        ]

    def _demo_lifecycle_contacts(self, stage: str, limit: int) -> list[HubSpotContact]:
        return [
            HubSpotContact(
                id=f"lead_{i}",
                email=f"lead{i}@example.com",
                lifecycle_stage=stage,
                total_revenue=0.0,
                deal_count=0,
                last_activity="2026-02-15",
                city="Chicago",
                job_title="Homeowner",
                company="",
            )
            for i in range(min(limit, 30))
        ]

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    @staticmethod
    def _top_n(items: list[str], n: int) -> list[str]:
        from collections import Counter
        return [item for item, _ in Counter(items).most_common(n)]
