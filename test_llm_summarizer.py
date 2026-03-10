"""
Test the LLM-based summarizer directly (bypassing API)
"""
import sys
sys.path.insert(0, 'src')

from agents.summarizer_agent import SummarizerAgent
from agents.base import AgentInput
import asyncio

async def test_llm_summarizer():
    print("="*60)
    print("Testing LLM-Based Summarizer")
    print("="*60)
    
    # Initialize agent
    summarizer = SummarizerAgent()
    
    # Test context from research papers about women's careers
    test_context = """
    Efficacy and Outcome Expectations Influence Career Exploration and Decidedness. 
    This study examined how self-efficacy affects career decisions in women. 
    Women with higher self-efficacy were more likely to pursue STEM careers.
    
    Gender gap in the executive suite: CEOs and female executives report on breaking the glass ceiling.
    Research shows that mentorship and networking are critical for women advancing to executive roles.
    Female CEOs report facing bias but also highlight the importance of confidence and preparation.
    
    Underrepresentation of women in sport leadership: A review of research.
    Despite progress, women remain underrepresented in leadership positions across sports management.
    Barriers include lack of role models, work-life balance challenges, and organizational culture.
    
    The Makeshift Careers of Women in Malawi revealed that women face serial compromises in their careers
    due to family responsibilities and inflexible workplace policies. Many talented women are forced to
    choose between career advancement and family obligations.
    """
    
    # Create input
    agent_input = AgentInput(
        query="best careers for women",
        context=test_context
    )
    
    # Run the summarizer
    print("\n🧠 Running LLM summarizer...")
    result = await summarizer.run(agent_input)
    
    print("\n✅ SUMMARY RESULT:")
    print("="*60)
    print(result.result)
    print("="*60)
    print(f"\n📊 Confidence: {result.confidence:.2f}")
    print(f"🔧 Method: {result.metadata.get('method', 'unknown')}")
    print(f"⏱️ Time: {result.metadata.get('time_ms', 0)}ms")
    
    # Compare with old extractive approach (if desired)
    print("\n" + "="*60)
    print("🆚 COMPARISON WITH OLD METHOD:")
    print("="*60)
    print("OLD (Extractive): Takes first few sentences verbatim, often incoherent")
    print("NEW (LLM): Synthesizes information into coherent narrative that answers the query")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_llm_summarizer())
