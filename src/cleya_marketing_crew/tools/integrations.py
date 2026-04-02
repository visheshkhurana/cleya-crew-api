"""
Real Tool Integrations for Cleya.ai Marketing Crew
=====================================================

Connected services:
  - Slack       → Post reports, alerts, content for review
  - HubSpot     → Create/update contacts, track partnership leads
  - Notion      → Write content calendar entries, strategy docs
  - Lemlist     → Add leads to outreach campaigns
  - Apify       → Run scrapers for competitor monitoring, social listening
  - Resend      → Send transactional emails
"""

import os
import json
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional


# ── SLACK ────────────────────────────────────────────────────────────

class SlackPostInput(BaseModel):
    channel: str = Field(
        default="#marketing",
        description="Slack channel to post to (e.g. #marketing, #content-review, #growth)"
    )
    message: str = Field(description="Message text to post (supports Slack markdown)")

class SlackPostTool(BaseTool):
    name: str = "post_to_slack"
    description: str = (
        "Post a message, report, or content draft to a Slack channel for team review. "
        "Use for sharing intelligence briefs, content drafts, strategy updates, or alerts. "
        "Default channel is #marketing."
    )
    args_schema: Type[BaseModel] = SlackPostInput

    def _run(self, channel: str = "#marketing", message: str = "") -> str:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return "[Slack] Not configured — set SLACK_BOT_TOKEN env var"
        
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={"channel": channel, "text": message, "mrkdwn": True},
                timeout=10,
            )
            data = resp.json()
            if data.get("ok"):
                return f"[Slack] Posted to {channel} successfully"
            return f"[Slack] Error: {data.get('error', 'unknown')}"
        except Exception as e:
            return f"[Slack] Failed: {str(e)}"


# ── HUBSPOT ──────────────────────────────────────────────────────────

class HubSpotContactInput(BaseModel):
    email: str = Field(description="Contact email address")
    first_name: str = Field(default="", description="First name")
    last_name: str = Field(default="", description="Last name")
    company: str = Field(default="", description="Company name")
    role: str = Field(default="", description="Job title or role")
    lead_source: str = Field(
        default="cleya_marketing_crew",
        description="How the lead was sourced (e.g. community_partnership, content_lead)"
    )
    notes: str = Field(default="", description="Additional context about the contact")

class HubSpotCreateContactTool(BaseTool):
    name: str = "create_hubspot_contact"
    description: str = (
        "Create or update a contact in HubSpot CRM. Use for tracking partnership leads, "
        "community contacts, event attendees, or potential Cleya.ai members identified "
        "during outreach."
    )
    args_schema: Type[BaseModel] = HubSpotContactInput

    def _run(self, email: str, first_name: str = "", last_name: str = "",
             company: str = "", role: str = "", lead_source: str = "cleya_marketing_crew",
             notes: str = "") -> str:
        token = os.getenv("HUBSPOT_API_KEY")
        if not token:
            return "[HubSpot] Not configured — set HUBSPOT_API_KEY env var"
        
        properties = {
            "email": email,
            "firstname": first_name,
            "lastname": last_name,
            "company": company,
            "jobtitle": role,
            "hs_lead_status": "NEW",
            "leadsource": lead_source,
        }
        if notes:
            properties["notes_last_contacted"] = notes

        try:
            resp = requests.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"properties": properties},
                timeout=10,
            )
            if resp.status_code in (200, 201):
                contact_id = resp.json().get("id", "")
                return f"[HubSpot] Contact created: {email} (ID: {contact_id})"
            elif resp.status_code == 409:
                return f"[HubSpot] Contact already exists: {email}"
            return f"[HubSpot] Error {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"[HubSpot] Failed: {str(e)}"


# ── NOTION ───────────────────────────────────────────────────────────

class NotionPageInput(BaseModel):
    title: str = Field(description="Page title (e.g. 'Week 14 Content Calendar', 'Intel Brief Apr 7')")
    content: str = Field(description="Full content in plain text or markdown")
    page_type: str = Field(
        default="report",
        description="Type: report, content_calendar, strategy, partnership_tracker, or prd"
    )

class NotionWriteTool(BaseTool):
    name: str = "write_to_notion"
    description: str = (
        "Create a page in Notion for storing content calendars, strategy documents, "
        "intelligence briefs, partnership trackers, or PRDs. Content is saved as a "
        "child page under the Cleya Marketing workspace."
    )
    args_schema: Type[BaseModel] = NotionPageInput

    def _run(self, title: str, content: str, page_type: str = "report") -> str:
        token = os.getenv("NOTION_API_KEY")
        parent_id = os.getenv("NOTION_PARENT_PAGE_ID")
        if not token or not parent_id:
            return "[Notion] Not configured — set NOTION_API_KEY and NOTION_PARENT_PAGE_ID env vars"

        # Split content into Notion blocks (2000 char limit per block)
        chunks = [content[i:i+2000] for i in range(0, min(len(content), 40000), 2000)]
        children = []

        # Add a type tag block
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Type: {page_type} | Generated by Cleya Marketing Crew"}}],
                "icon": {"type": "emoji", "emoji": "🤖"},
            }
        })

        for chunk in chunks:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })

        try:
            resp = requests.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Notion-Version": "2022-06-28",
                },
                json={
                    "parent": {"page_id": parent_id},
                    "properties": {"title": {"title": [{"text": {"content": title}}]}},
                    "children": children,
                },
                timeout=15,
            )
            if resp.ok:
                page_url = resp.json().get("url", "")
                return f"[Notion] Page created: {title} — {page_url}"
            return f"[Notion] Error {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"[Notion] Failed: {str(e)}"


# ── LEMLIST ──────────────────────────────────────────────────────────

class LemlistLeadInput(BaseModel):
    campaign_id: str = Field(description="Lemlist campaign ID to add the lead to")
    email: str = Field(description="Lead email address")
    first_name: str = Field(default="", description="Lead first name")
    last_name: str = Field(default="", description="Lead last name")
    company: str = Field(default="", description="Lead company name")
    custom_fields: Optional[dict] = Field(default=None, description="Additional custom fields")

class LemlistOutreachTool(BaseTool):
    name: str = "add_to_lemlist_campaign"
    description: str = (
        "Add a lead to a Lemlist email outreach campaign. Use for partnership outreach, "
        "community ambassador recruitment, event speaker invitations, or co-marketing "
        "campaign leads."
    )
    args_schema: Type[BaseModel] = LemlistLeadInput

    def _run(self, campaign_id: str, email: str, first_name: str = "",
             last_name: str = "", company: str = "", custom_fields: dict = None) -> str:
        api_key = os.getenv("LEMLIST_API_KEY")
        if not api_key:
            return "[Lemlist] Not configured — set LEMLIST_API_KEY env var"

        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "companyName": company,
        }
        if custom_fields:
            payload.update(custom_fields)

        try:
            resp = requests.post(
                f"https://api.lemlist.com/api/campaigns/{campaign_id}/leads/{email}",
                auth=("", api_key),
                json=payload,
                timeout=10,
            )
            if resp.ok:
                return f"[Lemlist] Added {email} to campaign {campaign_id}"
            return f"[Lemlist] Error {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"[Lemlist] Failed: {str(e)}"


# ── APIFY ────────────────────────────────────────────────────────────

class ApifyRunInput(BaseModel):
    actor_id: str = Field(
        description="Apify actor ID (e.g. 'apify/web-scraper', 'clockworks/free-twitter-scraper')"
    )
    run_input: dict = Field(description="Input configuration for the actor")
    wait_for_finish: bool = Field(
        default=False,
        description="Wait for the scraper to finish (max 60s) before returning results"
    )

class ApifyScrapeTool(BaseTool):
    name: str = "run_apify_scraper"
    description: str = (
        "Run an Apify actor/scraper for competitor monitoring, social media listening, "
        "or web data collection. Useful for gathering competitor content strategies, "
        "trending posts, event listings, or startup ecosystem data."
    )
    args_schema: Type[BaseModel] = ApifyRunInput

    def _run(self, actor_id: str, run_input: dict, wait_for_finish: bool = False) -> str:
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            return "[Apify] Not configured — set APIFY_API_TOKEN env var"

        try:
            url = f"https://api.apify.com/v2/acts/{actor_id}/runs"
            params = {"token": token}
            if wait_for_finish:
                params["waitForFinish"] = 60

            resp = requests.post(url, params=params, json=run_input, timeout=70)

            if resp.ok:
                run_data = resp.json().get("data", {})
                run_id = run_data.get("id", "unknown")
                status = run_data.get("status", "unknown")
                dataset_id = run_data.get("defaultDatasetId", "")

                if status == "SUCCEEDED" and dataset_id:
                    # Fetch results
                    items_resp = requests.get(
                        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
                        params={"token": token, "limit": 50},
                        timeout=15,
                    )
                    if items_resp.ok:
                        items = items_resp.json()
                        return f"[Apify] Completed. {len(items)} results:\n{json.dumps(items[:10], indent=2)}"

                return f"[Apify] Run started: {run_id} (status: {status}). Dataset: {dataset_id}"
            return f"[Apify] Error {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"[Apify] Failed: {str(e)}"


# ── RESEND (Transactional Email) ─────────────────────────────────────

class ResendEmailInput(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body (HTML supported)")
    from_name: str = Field(default="Cleya.ai", description="Sender display name")

class ResendEmailTool(BaseTool):
    name: str = "send_email_via_resend"
    description: str = (
        "Send a transactional email via Resend. Use for partnership introduction emails, "
        "event invitations, or personalized outreach that needs a custom template "
        "(not mass outreach — use Lemlist for that)."
    )
    args_schema: Type[BaseModel] = ResendEmailInput

    def _run(self, to: str, subject: str, body: str, from_name: str = "Cleya.ai") -> str:
        api_key = os.getenv("RESEND_API_KEY")
        from_email = os.getenv("RESEND_FROM_EMAIL", "crew@cleya.ai")
        if not api_key:
            return "[Resend] Not configured — set RESEND_API_KEY env var"

        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{from_name} <{from_email}>",
                    "to": [to],
                    "subject": subject,
                    "html": body,
                },
                timeout=10,
            )
            if resp.ok:
                email_id = resp.json().get("id", "")
                return f"[Resend] Email sent to {to} (ID: {email_id})"
            return f"[Resend] Error {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return f"[Resend] Failed: {str(e)}"
