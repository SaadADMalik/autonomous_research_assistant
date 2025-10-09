import pytest
from src.agents import ResearcherAgent, SummarizerAgent, ReviewerAgent, AgentInput, AgentOutput

@pytest.mark.asyncio
async def test_researcher_agent():
    agent = ResearcherAgent()
    output = await agent.run(AgentInput(query="test query"))
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0

@pytest.mark.asyncio
async def test_summarizer_agent():
    agent = SummarizerAgent()
    output = await agent.run(AgentInput(
        query="test query",
        context="test context"
    ))
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0

@pytest.mark.asyncio
async def test_reviewer_agent():
    agent = ReviewerAgent()
    output = await agent.run(AgentInput(
        query="test query",
        context="test context"
    ))
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0