"""Test script for the hybrid intent classifier."""
from services.intent_classifier import classify_intent

test_cases = [
    # Social chat -> GENERAL_CONVERSATION
    ("Hi", "GENERAL_CONVERSATION"),
    ("Hello", "GENERAL_CONVERSATION"),
    ("Hey", "GENERAL_CONVERSATION"),
    ("Thank you", "GENERAL_CONVERSATION"),
    ("Thanks", "GENERAL_CONVERSATION"),
    ("Bye", "GENERAL_CONVERSATION"),
    ("Goodbye", "GENERAL_CONVERSATION"),
    ("Good night", "GENERAL_CONVERSATION"),
    ("How are you?", "GENERAL_CONVERSATION"),
    ("Who are you?", "GENERAL_CONVERSATION"),
    ("What can you do?", "GENERAL_CONVERSATION"),
    ("Good morning", "GENERAL_CONVERSATION"),
    ("Good evening", "GENERAL_CONVERSATION"),
    ("OK", "GENERAL_CONVERSATION"),
    ("Got it", "GENERAL_CONVERSATION"),
    ("Nice to meet you", "GENERAL_CONVERSATION"),
    ("hi", "GENERAL_CONVERSATION"),
    ("ok", "GENERAL_CONVERSATION"),
    ("sure", "GENERAL_CONVERSATION"),
    ("cool", "GENERAL_CONVERSATION"),
    # Factual questions -> DOCUMENT_QUERY
    ("Who is Shreyas Iyer", "DOCUMENT_QUERY"),
    ("What is deep learning", "DOCUMENT_QUERY"),
    ("International yoga day date?", "DOCUMENT_QUERY"),
    ("Give me python program to find prime number", "DOCUMENT_QUERY"),
    ("Explain Section 4", "DOCUMENT_QUERY"),
    ("Write a Python function to sort a list", "DOCUMENT_QUERY"),
    ("Tell me about IPL 2026", "DOCUMENT_QUERY"),
    ("What is the capital of France?", "DOCUMENT_QUERY"),
    ("How does photosynthesis work?", "DOCUMENT_QUERY"),
    ("Give me brief details about shreyas iyer", "DOCUMENT_QUERY"),
    ("What is numerology?", "DOCUMENT_QUERY"),
    ("Define machine learning", "DOCUMENT_QUERY"),
    ("shreyas iyer played on which team in ipl 2026?", "DOCUMENT_QUERY"),
    ("Earth day date?", "DOCUMENT_QUERY"),
    ("Few Indian cricketer names", "DOCUMENT_QUERY"),
    # Compound messages -> DOCUMENT_QUERY
    ("Hi, can you summarize my document?", "DOCUMENT_QUERY"),
    ("Hey, what does page 5 say?", "DOCUMENT_QUERY"),
]

passed = 0
failed = 0
errors = []

print("=" * 80)
print("HYBRID INTENT CLASSIFIER TEST RESULTS")
print("=" * 80)

for msg, expected in test_cases:
    try:
        intent, resp = classify_intent(msg)
        status = "PASS" if intent == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
            errors.append((msg, expected, intent))
        
        intent_label = intent if intent else "NONE"
        expected_label = expected
        print(f"  {status}: '{msg:50s}' => {intent_label:25s} (expected {expected_label})")
    except Exception as e:
        failed += 1
        errors.append((msg, expected, str(e)))
        print(f"  ERROR: '{msg:50s}' => {e}")

print("=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)

if errors:
    print("\nFAILURES:")
    for msg, expected, actual in errors:
        print(f"  - '{msg}' : expected {expected}, got {actual}")

print("\nResponse samples:")
for msg in ["Hi", "Thank you", "How are you?", "Who are you?"]:
    intent, resp = classify_intent(msg)
    if resp:
        print(f"  '{msg}' -> {resp[:80]}")
