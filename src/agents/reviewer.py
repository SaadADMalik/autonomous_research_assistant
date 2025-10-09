from .base import BaseAgent
from .models import AgentInput, AgentOutput

class ReviewerAgent(BaseAgent):
    async def run(self, input_data: AgentInput) -> AgentOutput:
        # Placeholder implementation
        return AgentOutput(
            result=f"Review of: {input_data.query}\nContext: {input_data.context}",
            confidence=0.75
        )