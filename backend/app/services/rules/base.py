from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .contract import RuleStatus, RuleResult, RuleResultMetadata, RuleContext, EvidenceItem

class BaseRule(ABC):
    rule_id: str
    rule_type: str = "deterministic"  # "deterministic", "llm", "hybrid"
    version: str = "1.0.0"

    @abstractmethod
    async def evaluate(self, context: RuleContext) -> RuleResult:
        """
        Evaluate the rule against the provided RuleContext.
        Must handle missing, stale, or malformed input safely without throwing unhandled exceptions.
        """
        pass

    def build_result(
        self,
        status: RuleStatus,
        recommended_action: str,
        score: Optional[float] = None,
        confidence: float = 1.0,
        evidence: Optional[List[EvidenceItem]] = None,
        model_id: Optional[str] = None,
    ) -> RuleResult:
        """Helper to construct a fully validated RuleResult complying with Section 2."""
        return RuleResult(
            rule_id=self.rule_id,
            status=status,
            score=score,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=evidence or [],
            recommended_action=recommended_action,
            metadata=RuleResultMetadata(
                rule_version=self.version,
                model_id=model_id,
                execution_type=self.rule_type
            )
        )

    def handle_missing_data(
        self,
        missing_desc: str,
        recommended_action: Optional[str] = None
    ) -> RuleResult:
        """
        Per SH-03: Missing data = unknown.
        Per SH-12: Truncated or absent data = insufficient_evidence or unknown with confidence 0.0.
        """
        return self.build_result(
            status=RuleStatus.UNKNOWN,
            score=None,
            confidence=0.0,
            evidence=[
                EvidenceItem(
                    source="system",
                    reference="input_validation",
                    detail=f"Missing or insufficient data: {missing_desc}",
                    status="unknown"
                )
            ],
            recommended_action=recommended_action or f"Provide required data ({missing_desc}) to evaluate rule {self.rule_id}."
        )
