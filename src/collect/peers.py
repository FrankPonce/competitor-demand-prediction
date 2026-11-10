"""AI-market peers (Sprint 8), collected through the same documented public ATS APIs as Anthropic/OpenAI.

Each board was checked on 2026-11-10 to belong to the named company (the company names itself throughout
its own postings; for xAI: "x.ai" ×308, "Grok" ×1,646). One request per peer per snapshot; the companies'
own websites are never contacted. Review recorded in docs/source-register.csv and the Sprint 1 doc.
"""

from __future__ import annotations

# key: (display name, ats, board token, segment)
PEERS = {
    "xai": ("xAI", "greenhouse", "xai", "Frontier lab"),
    "cohere": ("Cohere", "ashby", "cohere", "Frontier lab"),
    "databricks": ("Databricks", "greenhouse", "databricks", "Data & AI infrastructure"),
    "scaleai": ("Scale AI", "greenhouse", "scaleai", "Data & AI infrastructure"),
    "togetherai": ("Together AI", "greenhouse", "togetherai", "Data & AI infrastructure"),
    "baseten": ("Baseten", "ashby", "baseten", "Data & AI infrastructure"),
    "perplexity": ("Perplexity", "ashby", "perplexity", "AI application"),
    "cursor": ("Cursor", "ashby", "cursor", "AI application"),
    "elevenlabs": ("ElevenLabs", "ashby", "elevenlabs", "AI application"),
    "harvey": ("Harvey", "ashby", "harvey", "AI application"),
    "sierra": ("Sierra", "ashby", "sierra", "AI application"),
    "decagon": ("Decagon", "ashby", "decagon", "AI application"),
    "figureai": ("Figure AI", "greenhouse", "figureai", "Robotics"),
}
CORE_SEGMENT = {"Anthropic": "Frontier lab", "OpenAI": "Frontier lab", "Google": "Big tech", "NVIDIA": "Semiconductors"}


def segment(company: str) -> str:
    for name, _, _, seg in PEERS.values():
        if name == company:
            return seg
    return CORE_SEGMENT.get(company, "Other")
