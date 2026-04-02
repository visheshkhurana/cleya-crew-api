"""
Custom Tools for Cleya.ai Marketing Crew
==========================================

Add specialized tools here as the crew evolves.
Example: Indian startup database lookup, social media analytics, etc.
"""

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class IndianStartupSearchInput(BaseModel):
    """Input schema for Indian Startup ecosystem search."""
    query: str = Field(
        ..., 
        description="Search query about Indian startups, funding rounds, or ecosystem trends."
    )
    sector: str = Field(
        default="all",
        description="Sector filter: fintech, healthtech, saas, ai_ml, ecommerce, edtech, or all."
    )
    stage: str = Field(
        default="all", 
        description="Stage filter: pre_seed, seed, series_a, series_b, growth, or all."
    )


class IndianStartupSearchTool(BaseTool):
    """
    Searches for Indian startup ecosystem information.
    
    This is a template — connect to Inc42 API, Tracxn, or your own 
    database for production use. Currently wraps web search with 
    India-specific query augmentation.
    """
    name: str = "indian_startup_search"
    description: str = (
        "Search for information about Indian startups, funding rounds, "
        "investors, and ecosystem trends. Augments queries with India-specific "
        "context for better results."
    )
    args_schema: Type[BaseModel] = IndianStartupSearchInput

    def _run(self, query: str, sector: str = "all", stage: str = "all") -> str:
        """
        Augment the query with Indian ecosystem context and search.
        
        In production, replace this with direct API calls to:
        - Inc42 / Entrackr for funding data
        - Tracxn for startup profiles
        - LinkedIn API for people data
        - Twitter/X API for trending conversations
        """
        augmented_query = f"India startup ecosystem: {query}"
        
        if sector != "all":
            augmented_query += f" {sector} sector"
        if stage != "all":
            augmented_query += f" {stage.replace('_', ' ')} stage"

        # Placeholder — integrate with SerperDevTool or direct APIs
        return (
            f"[IndianStartupSearch] Query: {augmented_query}\n"
            f"Note: Connect this tool to Inc42 API, Tracxn, or Crunchbase "
            f"for production-grade results. Currently using web search fallback."
        )


class ViralScoreCalculatorInput(BaseModel):
    """Input schema for viral coefficient calculator."""
    total_users: int = Field(..., description="Current total users/members.")
    invites_sent: int = Field(..., description="Total invites sent by existing users.")
    invites_accepted: int = Field(..., description="Total invites that converted to signups.")
    time_period_days: int = Field(default=7, description="Time period in days for the calculation.")


class ViralScoreCalculatorTool(BaseTool):
    """
    Calculates viral coefficient (k-factor) and related growth metrics.
    
    K = invites_per_user × conversion_rate
    If K > 1.0, the product is growing virally.
    """
    name: str = "viral_score_calculator"
    description: str = (
        "Calculate the viral coefficient (k-factor) for Cleya.ai based on "
        "referral data. Returns k-factor, growth rate, and projections."
    )
    args_schema: Type[BaseModel] = ViralScoreCalculatorInput

    def _run(
        self, 
        total_users: int, 
        invites_sent: int, 
        invites_accepted: int, 
        time_period_days: int = 7,
    ) -> str:
        if total_users == 0:
            return "Error: total_users must be > 0"

        invites_per_user = invites_sent / total_users
        conversion_rate = invites_accepted / invites_sent if invites_sent > 0 else 0
        k_factor = invites_per_user * conversion_rate

        # Project growth over 4 cycles
        projected = total_users
        projections = []
        for cycle in range(1, 5):
            new_users = int(projected * k_factor)
            projected += new_users
            projections.append(f"  Cycle {cycle}: +{new_users} → {projected} total")

        status = "🚀 VIRAL" if k_factor > 1.0 else "📈 Growing" if k_factor > 0.5 else "⚠️ Below threshold"

        return (
            f"Viral Coefficient Analysis ({time_period_days}-day period)\n"
            f"{'=' * 50}\n"
            f"Total Users:        {total_users}\n"
            f"Invites Sent:       {invites_sent} ({invites_per_user:.1f} per user)\n"
            f"Invites Accepted:   {invites_accepted} ({conversion_rate:.1%} conversion)\n"
            f"K-Factor:           {k_factor:.2f} {status}\n"
            f"\nGrowth Projection (4 cycles):\n"
            + "\n".join(projections)
            + f"\n\nTarget: K > 1.0 for organic viral growth"
        )
