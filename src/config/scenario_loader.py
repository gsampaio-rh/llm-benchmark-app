"""
Scenario loader for YAML-based scenario definitions.

This module provides functionality to load, validate, and manage
benchmark scenarios from YAML configuration files.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from pydantic import ValidationError

from .scenario_models import (
    Scenario,
    ScenarioLibrary,
    PromptConfig,
    CompletionConfig,
    TestCase,
    ScenarioMetadata
)


logger = logging.getLogger(__name__)


class ScenarioLoadError(Exception):
    """Raised when scenario loading fails."""
    pass


class ScenarioValidationError(Exception):
    """Raised when scenario validation fails."""
    pass


class ScenarioLoader:
    """
    Loader for YAML-based scenario configurations.
    
    Provides functionality to load, validate, and manage benchmark
    scenarios from YAML files.
    """
    
    def __init__(self, scenarios_dir: Optional[Path] = None):
        """
        Initialize scenario loader.
        
        Args:
            scenarios_dir: Directory containing scenario YAML files
                          (defaults to configs/scenarios/)
        """
        if scenarios_dir is None:
            # Default to configs/scenarios/ relative to project root
            self.scenarios_dir = Path(__file__).parent.parent.parent / "configs" / "scenarios"
        else:
            self.scenarios_dir = Path(scenarios_dir)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized scenario loader with directory: {self.scenarios_dir}")
    
    def load_scenario(self, file_path: Path) -> Scenario:
        """
        Load a single scenario from YAML file.
        
        Args:
            file_path: Path to YAML scenario file
            
        Returns:
            Scenario object
            
        Raises:
            ScenarioLoadError: If file cannot be loaded
            ScenarioValidationError: If scenario is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ScenarioLoadError(f"Empty scenario file: {file_path}")
            
            # Parse scenario data
            scenario_data = data.get('scenario', data)
            
            # Create scenario object
            scenario = Scenario(**scenario_data)
            
            # Validate test cases
            errors = scenario.validate_test_cases()
            if errors:
                raise ScenarioValidationError(
                    f"Scenario '{scenario.name}' validation errors:\n" +
                    "\n".join(f"  - {err}" for err in errors)
                )
            
            self.logger.info(f"Loaded scenario: {scenario.name}")
            return scenario
            
        except FileNotFoundError:
            raise ScenarioLoadError(f"Scenario file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ScenarioLoadError(f"Invalid YAML in {file_path}: {e}")
        except ValidationError as e:
            raise ScenarioValidationError(f"Scenario validation failed for {file_path}:\n{e}")
        except Exception as e:
            raise ScenarioLoadError(f"Failed to load scenario from {file_path}: {e}")
    
    def load_all_scenarios(self) -> ScenarioLibrary:
        """
        Load all scenarios from the scenarios directory.
        
        Returns:
            ScenarioLibrary with all loaded scenarios
        """
        if not self.scenarios_dir.exists():
            self.logger.warning(f"Scenarios directory does not exist: {self.scenarios_dir}")
            return ScenarioLibrary(name="Empty Library")
        
        scenarios = []
        errors = []
        
        # Find all YAML files
        yaml_files = list(self.scenarios_dir.glob("*.yaml")) + list(self.scenarios_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                scenario = self.load_scenario(yaml_file)
                scenarios.append(scenario)
            except (ScenarioLoadError, ScenarioValidationError) as e:
                self.logger.error(f"Failed to load {yaml_file.name}: {e}")
                errors.append((yaml_file.name, str(e)))
        
        library = ScenarioLibrary(
            name="Benchmark Scenario Library",
            description=f"Loaded {len(scenarios)} scenarios from {self.scenarios_dir}",
            scenarios=scenarios
        )
        
        if errors:
            self.logger.warning(f"Loaded {len(scenarios)} scenarios with {len(errors)} errors")
        else:
            self.logger.info(f"Successfully loaded {len(scenarios)} scenarios")
        
        return library
    
    def save_scenario(self, scenario: Scenario, file_path: Optional[Path] = None) -> Path:
        """
        Save a scenario to YAML file.
        
        Args:
            scenario: Scenario to save
            file_path: Optional output path (defaults to scenarios_dir/{name}.yaml)
            
        Returns:
            Path to saved file
        """
        if file_path is None:
            # Create filename from scenario name
            filename = scenario.name.lower().replace(" ", "_") + ".yaml"
            file_path = self.scenarios_dir / filename
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and write YAML
        data = {"scenario": scenario.model_dump(exclude_none=True)}
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        self.logger.info(f"Saved scenario '{scenario.name}' to {file_path}")
        return file_path
    
    def create_scenario_template(
        self,
        name: str,
        description: str,
        prompt_template: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Scenario:
        """
        Create a basic scenario template.
        
        Args:
            name: Scenario name
            description: Scenario description
            prompt_template: Prompt template string
            max_tokens: Maximum completion tokens
            temperature: Sampling temperature
            
        Returns:
            Scenario object
        """
        return Scenario(
            name=name,
            description=description,
            prompt=PromptConfig(template=prompt_template),
            completion=CompletionConfig(
                max_tokens=max_tokens,
                temperature=temperature
            )
        )
    
    def list_available_scenarios(self) -> List[str]:
        """List names of all available scenarios."""
        library = self.load_all_scenarios()
        return [s.name for s in library.scenarios]
    
    def get_scenario_summary(self, scenario: Scenario) -> Dict[str, Any]:
        """Get summary information about a scenario."""
        return {
            "name": scenario.name,
            "description": scenario.description,
            "use_case": scenario.get_use_case_category(),
            "prompt_category": scenario.prompt.category.value if scenario.prompt.category else None,
            "completion_category": scenario.completion.category.value if scenario.completion.category else None,
            "max_tokens": scenario.completion.max_tokens,
            "temperature": scenario.completion.temperature,
            "num_test_cases": len(scenario.test_cases),
            "enabled": scenario.enabled
        }


# Global scenario loader instance
_scenario_loader: Optional[ScenarioLoader] = None


def get_scenario_loader(scenarios_dir: Optional[Path] = None) -> ScenarioLoader:
    """Get or create the global scenario loader instance."""
    global _scenario_loader
    
    if _scenario_loader is None:
        _scenario_loader = ScenarioLoader(scenarios_dir)
    
    return _scenario_loader


def load_scenario(file_path: Path) -> Scenario:
    """Convenience function to load a single scenario."""
    loader = get_scenario_loader()
    return loader.load_scenario(file_path)


def load_all_scenarios(scenarios_dir: Optional[Path] = None) -> ScenarioLibrary:
    """Convenience function to load all scenarios."""
    loader = get_scenario_loader(scenarios_dir)
    return loader.load_all_scenarios()

