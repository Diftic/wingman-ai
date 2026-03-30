"""
SC_LogReader - Star Citizen Log Reader Skill

3-Layer Architecture:
- Layer 3 (parser.py): Log reading and atomic state extraction
- Layer 2 (logic.py): State combination and derived events
- Layer 1 (main.py): WingmanAI skill interface
"""

from .main import SC_LogReader
from .logic import DerivedEvent, Rule, StateLogic
from .parser import LogEvent, LogParser, StateStore

__all__ = [
    "SC_LogReader",
    "LogParser",
    "StateStore",
    "LogEvent",
    "StateLogic",
    "Rule",
    "DerivedEvent",
]
