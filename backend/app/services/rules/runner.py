import logging
from typing import Dict, List, Optional
from .contract import RuleResult, RuleContext, RuleStatus, EvidenceItem
from .base import BaseRule

logger = logging.getLogger("contribo.rules.runner")

class RuleRunner:
    def __init__(self):
        self._rules: Dict[str, BaseRule] = {}

    def register(self, rule: BaseRule) -> None:
        """Register a rule in the engine."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Fetch a registered rule by its stable ID."""
        return self._rules.get(rule_id)

    async def run_rule(self, rule_id: str, context: RuleContext) -> RuleResult:
        """Run a single rule safely with defensive exception boundary."""
        rule = self._rules.get(rule_id)
        if not rule:
            logger.warning(f"Rule '{rule_id}' not found in registry.")
            return RuleResult(
                rule_id=rule_id,
                status=RuleStatus.UNKNOWN,
                score=None,
                confidence=0.0,
                evidence=[
                    EvidenceItem(
                        source="runner",
                        reference="registry",
                        detail=f"Rule {rule_id} is not registered in the engine.",
                        status="unknown"
                    )
                ],
                recommended_action="Ensure the requested rule is implemented and registered."
            )

        try:
            return await rule.evaluate(context)
        except Exception as e:
            logger.exception(f"Unexpected error executing rule {rule_id}: {str(e)}")
            # Fail closed: never crash the engine, return UNKNOWN with error details
            return rule.build_result(
                status=RuleStatus.UNKNOWN,
                score=None,
                confidence=0.0,
                evidence=[
                    EvidenceItem(
                        source="runner_exception",
                        reference="execution",
                        detail=f"Execution error: {str(e)}",
                        status="error"
                    )
                ],
                recommended_action="Inspect rule execution logs and verify input structure."
            )

    async def run_all(
        self,
        context: RuleContext,
        rule_ids: Optional[List[str]] = None
    ) -> List[RuleResult]:
        """Execute a list of rules (or all registered rules) against the given context."""
        target_ids = rule_ids if rule_ids is not None else list(self._rules.keys())
        results: List[RuleResult] = []
        for rid in target_ids:
            res = await self.run_rule(rid, context)
            results.append(res)
        return results
