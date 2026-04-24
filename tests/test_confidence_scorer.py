from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.confidence_scorer import compute_confidence
from testforge.core.analyzer.intent_classifier import IntentSummary


def test_confidence_structural_and_localized_high() -> None:
    diff = """
diff --git a/models.py b/models.py
--- a/models.py
+++ b/models.py
@@
+class User:
+    pass
"""
    cs = ChangeSummary(files=["models.py"], functions=[], diff_text=diff)
    intent = IntentSummary(intent_score=0.7, intent_label="intentional", signals=["x"])
    conf = compute_confidence(cs, intent)
    assert conf.score >= 0.75
    assert conf.level == "High"
    assert conf.reasons


def test_confidence_large_change_lowish() -> None:
    cs = ChangeSummary(files=[f"f{i}.py" for i in range(12)], functions=[], diff_text="manager\n")
    intent = IntentSummary(intent_score=0.3, intent_label="uncertain", signals=[])
    conf = compute_confidence(cs, intent)
    assert conf.level in {"Low", "Medium"}
