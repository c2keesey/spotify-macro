"""
Staging Classification Automation

Unified classification system that processes songs from a staging playlist using
intelligent multi-strategy approach:

1. Artist Matching (100% accuracy) - Priority 1
2. Genre Classification (76% accuracy) - Priority 2

Integrates with the bidirectional flow architecture for optimal music organization.
"""

from .action import run_action, main

__all__ = ['run_action', 'main']