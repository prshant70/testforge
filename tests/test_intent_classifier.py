from testforge.core.analyzer.change_analyzer import ChangeSummary
from testforge.core.analyzer.intent_classifier import classify_intent


def test_intent_classifier_positive_signals() -> None:
    diff = """
diff --git a/app.py b/app.py
index 000..111 100644
--- a/app.py
+++ b/app.py
@@
+@app.post("/users")
+def create_user():
+    if not email:
+        raise BadRequest("missing email")
+    return {"ok": True}
"""
    cs = ChangeSummary(files=["app.py"], functions=[], diff_text=diff)
    intent = classify_intent(cs)
    assert intent.intent_score >= 0.65
    assert intent.intent_label in {"intentional", "mixed"}
    assert intent.signals


def test_intent_classifier_negative_signals() -> None:
    diff = """
diff --git a/x.py b/x.py
index 000..111 100644
--- a/x.py
+++ b/x.py
@@
-if ok:
-    return 1
+if ok and ready:
+    return 2
"""
    cs = ChangeSummary(files=["x.py"], functions=[], diff_text=diff)
    intent = classify_intent(cs)
    assert intent.intent_score <= 0.6
    assert intent.intent_label in {"mixed", "uncertain"}
