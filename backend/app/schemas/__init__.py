"""Pydantic schemas — request/response models for the MP HTTP API.

Mirrors the shapes in ``src/lib/types.ts``: response fields match the TS
interfaces verbatim (names, types, optionality) so a TS client can consume a
backend response without translation.
"""

from app.schemas.memory_crud import MemoryListResponse, MemoryPatch, MemoryRecordResponse

__all__ = ["MemoryListResponse", "MemoryPatch", "MemoryRecordResponse"]
