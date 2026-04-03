"""
Cleya.ai Growth & Viral Marketing Crew
=======================================
Production crew with real tool integrations.

5 agents → Sequential pipeline → Results to Slack + Notion
"""

import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileReadTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

# ── LLM Config (explicit model to avoid crewAI default issues) ──────
DEFAULT_MODEL = os.getenv("CREW_MODEL", "gpt-4o-mini")
default_llm = LLM(model=DEFAULT_MODEL)

from cleya_marketing_crew.tools.integrations import (
    SlackPostTool,
    HubSpotCreateContactTool,
    NotionWriteTool,
    LemlistOutreachTool,
    ApifyScrapeTool,
    ResendEmailTool,
)

# ── Shared Tool Instances ────────────────────────────────────────────

serper_search = SerperDevTool()
web_scraper = ScrapeWebsiteTool()
file_reader = FileReadTool()

slack = SlackPostTool()
hubspot = HubSpotCreateContactTool()
notion = NotionWriteTool()
lemlist = LemlistOutreachTool()
apify = ApifyScrapeTool()
resend = ResendEmailTool()


@CrewBase
class CleyaMarketingCrew:
    """Cleya.ai Growth & Viral Marketing Crew — Production"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # ── AGENTS ───────────────────────────────────────────────────────

    @agent
    def market_intelligence_analyst(self) -> Agent:
        """Ecosystem intel: funding, competitors, trends, Tier-2 signals."""
        return Agent(
            config=self.agents_config["market_intelligence_analyst"],
            tools=[serper_search, web_scraper, apify, slack, file_reader],
            llm=default_llm,
            verbose=True,
        )

    @agent
    def growth_strategist(self) -> Agent:
        """Funnels, loops, channel strategy, metrics framework."""
        return Agent(
            config=self.agents_config["growth_strategist"],
            tools=[serper_search, notion, slack, file_reader],
            llm=default_llm,
            verbose=True,
            allow_delegation=True,
        )

    @agent
    def viral_content_architect(self) -> Agent:
        """LinkedIn/X content calendar, hooks, memes, viral mechanics."""
        return Agent(
            config=self.agents_config["viral_content_architect"],
            tools=[serper_search, web_scraper, notion, slack],
            llm=default_llm,
            verbose=True,
        )

    @agent
    def community_growth_hacker(self) -> Agent:
        """Partnerships, ambassadors, events, WhatsApp referral flows."""
        return Agent(
            config=self.agents_config["community_growth_hacker"],
            tools=[serper_search, web_scraper, hubspot, lemlist, notion, resend],
            llm=default_llm,
            verbose=True,
        )

    @agent
    def product_led_growth_engineer(self) -> Agent:
        """Referral systems, match cards, waitlist gamification, k-factor."""
        return Agent(
            config=self.agents_config["product_led_growth_engineer"],
            tools=[notion, slack, file_reader],
            llm=default_llm,
            verbose=True,
        )

    # ── TASKS ────────────────────────────────────────────────────────

    @task
    def ecosystem_intelligence_task(self) -> Task:
        return Task(config=self.tasks_config["ecosystem_intelligence_task"])

    @task
    def growth_strategy_task(self) -> Task:
        return Task(config=self.tasks_config["growth_strategy_task"])

    @task
    def viral_content_task(self) -> Task:
        return Task(config=self.tasks_config["viral_content_task"])

    @task
    def community_partnerships_task(self) -> Task:
        return Task(config=self.tasks_config["community_partnerships_task"])

    @task
    def product_led_growth_task(self) -> Task:
        return Task(config=self.tasks_config["product_led_growth_task"])

    # ── CREW ─────────────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        """Production crew: sequential pipeline with memory."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
