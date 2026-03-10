"""Test script for improved routing logic."""

from src.agents.api_router_agent import APIRouterAgent

router = APIRouterAgent()
print("✅ Router initialized successfully\n")

# Test queries
test_queries = [
    "how being a mother changes a female",
    "best careers for women to excel",
    "quantum computing",
    "technical industry evolution over time",
    "why men commit more suicides than women",
    "machine learning applications in healthcare",
    "climate change impact on agriculture",
]

print("📝 TESTING IMPROVED ROUTING:\n")
print("=" * 80)

for i, query in enumerate(test_queries, 1):
    print(f"\n{i}. Query: '{query}'")
    result = router.route(query)
    print(f"   Domain: {result['domain']}")
    print(f"   Primary API: {result['primary']}")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Reasoning: {result['reasoning'][:100]}...")

print("\n" + "=" * 80)
print("\n✅ All routing tests completed!")
