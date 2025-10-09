from abc import ABC, abstractmethod
from .models import AgentInput, AgentOutput

class BaseAgent(ABC):
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute the agent's main functionality
        Args:
            input_data (AgentInput): The input data containing query and optional context
        Returns:
            AgentOutput: The agent's response with result and confidence
        """
        pass