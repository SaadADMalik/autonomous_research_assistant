import pytest
from src.agents.researcher_agent import ResearcherAgent
from src.agents.summarizer_agent import SummarizerAgent  
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.base import AgentInput, AgentOutput

@pytest.mark.asyncio
async def test_researcher_agent():
    agent = ResearcherAgent()
    input_data = AgentInput(query="test query")
    # Pass empty list of documents since it's optional
    output = await agent.run(input_data, documents=[])
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0

@pytest.mark.asyncio
async def test_summarizer_agent():
    agent = SummarizerAgent()
    input_data = AgentInput(
        query="test query",
        context="This is test content for summarization. It needs to be long enough to test the BART model properly."
    )
    output = await agent.run(input_data)
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0

@pytest.mark.asyncio
async def test_reviewer_agent():
    agent = ReviewerAgent()
    input_data = AgentInput(
        query="test query", 
        context="This is test content for review."
    )
    output = await agent.run(input_data)
    assert isinstance(output, AgentOutput)
    assert isinstance(output.result, str)
    assert 0 <= output.confidence <= 1.0