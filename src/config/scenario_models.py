"""
Pydantic models for scenario configuration.

This module defines the schema for benchmark scenarios including
prompt templates, completion settings, and test cases.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class PromptLengthCategory(str, Enum):
    """Prompt length categories."""
    SHORT = "short"      # 5-50 tokens
    MEDIUM = "medium"    # 50-500 tokens
    LONG = "long"        # 500-4000 tokens
    VERY_LONG = "very_long"  # 4000+ tokens


class CompletionLengthCategory(str, Enum):
    """Completion length categories."""
    SHORT = "short"      # 10-100 tokens
    MEDIUM = "medium"    # 100-500 tokens
    LONG = "long"        # 500-2000 tokens
    VERY_LONG = "very_long"  # 2000+ tokens


class PromptConfig(BaseModel):
    """Configuration for prompt generation."""
    
    model_config = {"extra": "forbid"}
    
    template: str = Field(
        ...,
        description="Prompt template with optional {placeholders}"
    )
    min_tokens: Optional[int] = Field(
        default=None,
        description="Minimum expected tokens in prompt",
        ge=1
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum expected tokens in prompt",
        ge=1
    )
    category: Optional[PromptLengthCategory] = Field(
        default=None,
        description="Prompt length category"
    )
    
    @validator("max_tokens")
    def validate_token_range(cls, v, values):
        """Ensure max_tokens >= min_tokens if both specified."""
        if v is not None and "min_tokens" in values and values["min_tokens"] is not None:
            if v < values["min_tokens"]:
                raise ValueError("max_tokens must be >= min_tokens")
        return v


class CompletionConfig(BaseModel):
    """Configuration for completion generation."""
    
    model_config = {"extra": "forbid"}
    
    max_tokens: int = Field(
        default=500,
        description="Maximum tokens to generate",
        ge=1,
        le=8192
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature",
        ge=0.0,
        le=2.0
    )
    top_p: Optional[float] = Field(
        default=None,
        description="Nucleus sampling threshold",
        ge=0.0,
        le=1.0
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Top-k sampling",
        ge=1
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        description="Sequences that stop generation"
    )
    category: Optional[CompletionLengthCategory] = Field(
        default=None,
        description="Completion length category"
    )


class TestCase(BaseModel):
    """Individual test case with parameter values."""
    
    model_config = {"extra": "allow"}
    
    name: Optional[str] = Field(
        default=None,
        description="Optional test case name"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for template substitution"
    )
    
    def __init__(self, **data):
        """Allow flexible parameter passing."""
        # Extract known fields
        name = data.pop("name", None)
        params = data.pop("params", {})
        
        # Remaining fields become params
        params.update(data)
        
        super().__init__(name=name, params=params)


class ScenarioMetadata(BaseModel):
    """Metadata about the scenario."""
    
    model_config = {"extra": "forbid"}
    
    author: Optional[str] = Field(default=None, description="Scenario author")
    created: Optional[str] = Field(default=None, description="Creation date")
    version: str = Field(default="1.0", description="Scenario version")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class Scenario(BaseModel):
    """Complete scenario definition."""
    
    model_config = {"extra": "forbid"}
    
    name: str = Field(
        ...,
        description="Scenario name (unique identifier)"
    )
    description: str = Field(
        ...,
        description="Human-readable description"
    )
    prompt: PromptConfig = Field(
        ...,
        description="Prompt configuration"
    )
    completion: CompletionConfig = Field(
        ...,
        description="Completion configuration"
    )
    test_cases: List[TestCase] = Field(
        default_factory=list,
        description="Test cases with parameter values"
    )
    num_requests: Optional[int] = Field(
        default=None,
        description="Number of requests to run (optional, prompts user if not set)",
        ge=1
    )
    targets: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Pre-configured engines and models to test (optional)"
    )
    metadata: Optional[ScenarioMetadata] = Field(
        default=None,
        description="Scenario metadata"
    )
    enabled: bool = Field(
        default=True,
        description="Whether scenario is enabled"
    )
    
    @validator("name")
    def validate_name(cls, v):
        """Ensure name is valid (alphanumeric with common punctuation)."""
        # Allow alphanumeric, spaces, underscores, hyphens, and common punctuation
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-+().,")
        if not all(c in allowed_chars for c in v):
            raise ValueError("Scenario name contains invalid characters")
        return v
    
    def get_use_case_category(self) -> str:
        """Determine use case category based on prompt/completion lengths."""
        prompt_cat = self.prompt.category
        comp_cat = self.completion.category
        
        if not prompt_cat or not comp_cat:
            return "uncategorized"
        
        # Map to use case categories
        categories = {
            ("short", "short"): "chat",
            ("short", "medium"): "chat",
            ("short", "long"): "creative_writing",
            ("short", "very_long"): "creative_writing",
            ("medium", "short"): "qa",
            ("medium", "medium"): "qa",
            ("long", "short"): "rag",
            ("long", "medium"): "summarization",
            ("long", "long"): "document_analysis",
            ("long", "very_long"): "document_analysis",
            ("very_long", "short"): "rag",
            ("very_long", "medium"): "summarization",
            ("very_long", "long"): "document_analysis",
        }
        
        return categories.get((prompt_cat.value, comp_cat.value), "mixed")
    
    def expand_test_cases(self) -> List[str]:
        """Expand test cases into actual prompts."""
        prompts = []
        
        if not self.test_cases:
            # If no test cases, use template as-is
            prompts.append(self.prompt.template)
        else:
            # Expand each test case
            for test_case in self.test_cases:
                try:
                    prompt = self.prompt.template.format(**test_case.params)
                    prompts.append(prompt)
                except KeyError as e:
                    raise ValueError(
                        f"Test case missing required parameter: {e}. "
                        f"Template requires: {self._get_template_params()}"
                    )
        
        return prompts
    
    def _get_template_params(self) -> List[str]:
        """Extract parameter names from template."""
        import re
        return re.findall(r'\{(\w+)\}', self.prompt.template)
    
    def validate_test_cases(self) -> List[str]:
        """Validate that all test cases have required parameters."""
        required_params = set(self._get_template_params())
        errors = []
        
        for i, test_case in enumerate(self.test_cases):
            missing = required_params - set(test_case.params.keys())
            if missing:
                errors.append(
                    f"Test case {i} ({test_case.name or 'unnamed'}) missing parameters: {missing}"
                )
        
        return errors


class ScenarioLibrary(BaseModel):
    """Collection of scenarios."""
    
    model_config = {"extra": "forbid"}
    
    name: str = Field(
        default="Default Library",
        description="Library name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Library description"
    )
    scenarios: List[Scenario] = Field(
        default_factory=list,
        description="List of scenarios"
    )
    
    def get_scenario(self, name: str) -> Optional[Scenario]:
        """Get scenario by name."""
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario
        return None
    
    def get_enabled_scenarios(self) -> List[Scenario]:
        """Get all enabled scenarios."""
        return [s for s in self.scenarios if s.enabled]
    
    def get_scenarios_by_category(self, category: str) -> List[Scenario]:
        """Get scenarios by use case category."""
        return [s for s in self.scenarios if s.get_use_case_category() == category]

