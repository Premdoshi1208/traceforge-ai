"""Untrusted model output contracts. No contract grants execution permission."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyArguments(StrictModel):
    pass


class Hypothesis(StrictModel):
    title: str
    explanation: str
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    assessment: Literal["supported", "uncertain", "contradicted"]


class Diagnosis(StrictModel):
    root_cause: str
    hypotheses: list[Hypothesis]
    evidence_ids: list[str]
    safe_to_patch: bool
    missing_evidence: str

    @field_validator("hypotheses")
    @classmethod
    def bounded_hypotheses(cls, value):
        if not 1 <= len(value) <= 4:
            raise ValueError("Expected one to four competing hypotheses")
        return value


class PatchProposal(StrictModel):
    source: str
    explanation: str
    evidence_ids: list[str]

    @field_validator("source")
    @classmethod
    def bounded_source(cls, value):
        if not value.strip() or len(value.encode()) > 12000:
            raise ValueError("Candidate source is empty or exceeds the patch budget")
        return value


class Review(StrictModel):
    approved: bool
    summary: str
    risks: list[str]
    evidence_ids: list[str]


def validate_citations(payload: dict, evidence_ids: set[str]) -> None:
    """Reject invented references and unsupported positive claims."""
    refs = payload.get("evidence_ids", [])
    if not refs or not set(refs).issubset(evidence_ids):
        raise ValueError("Model response has missing or unknown evidence references")
    for hypothesis in payload.get("hypotheses", []):
        support = hypothesis["supporting_evidence"]
        contra = hypothesis["contradicting_evidence"]
        if not set(support + contra).issubset(evidence_ids):
            raise ValueError("Hypothesis cites an unknown evidence ID")
        if hypothesis["assessment"] == "supported" and not support:
            raise ValueError("Supported hypothesis requires supporting evidence")
