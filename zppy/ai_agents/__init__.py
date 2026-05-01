"""
zppy AI Agents Module

This module provides AI-powered assistance for zppy configuration,
monitoring, and workflow management.

Components:
- rag/: Retrieval-Augmented Generation for documentation lookup
- config_agent: Interactive configuration generation
"""

__all__ = ["ConfigAgent"]


def __getattr__(name):
    if name == "ConfigAgent":
        from zppy.ai_agents.config_agent import ConfigAgent

        return ConfigAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
