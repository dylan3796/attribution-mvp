"""
Natural Language Rule Parser
=============================

Convert natural language descriptions into attribution rule configurations.

Examples:
- "Split evenly among all partners" → equal_split config
- "Give more credit to recent touches" → time_decay config with half_life
- "SI partners get 60%, influence 40%" → role_weighted config
- "First partner gets 100%" → first_touch config

Uses Claude API (optional) with fallback to heuristics.
"""

import os
import json
import re
from typing import Dict, Any, Optional, Tuple
from models_new import AttributionModel, SplitConstraint, RULE_TEMPLATES, validate_rule_config

# Try to import Claude API
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class NaturalLanguageRuleParser:
    """
    Parse natural language descriptions into attribution rule configs.

    Uses Claude API when available, falls back to pattern matching.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the parser.

        Args:
            api_key: Anthropic API key (optional, reads from env if not provided)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = Anthropic(api_key=self.api_key)

    def parse(self, natural_language: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse natural language into a rule configuration.

        Args:
            natural_language: User's description (e.g., "Split based on activity")

        Returns:
            (success, rule_config, error_message)

            rule_config format:
            {
                "name": "User-friendly rule name",
                "model_type": "equal_split" | "role_weighted" | ...,
                "config": {...},  # Model-specific config
                "split_constraint": "must_sum_to_100" | ...,
                "applies_to": {...}  # Optional filters
            }
        """

        # Try Claude API first
        if self.client:
            success, config, error = self._parse_with_claude(natural_language)
            if success:
                return success, config, error

        # Fallback to pattern matching
        return self._parse_with_heuristics(natural_language)

    def _parse_with_claude(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Use Claude API to parse natural language.
        """
        if not self.client:
            return False, None, "Claude API not available"

        system_prompt = """You are an expert in partner attribution methodologies.

Convert the user's natural language description into a JSON attribution rule configuration.

Available attribution models:
- equal_split: Divide revenue evenly among all partners
- role_weighted: Weight by partner role (SI, Influence, Referral, ISV)
- activity_weighted: Weight by # of activities/meetings
- time_decay: More recent touches get more credit (exponential decay)
- first_touch: 100% to first partner
- last_touch: 100% to last partner
- linear: Equal credit over time
- u_shaped: 40% first, 40% last, 20% middle

Split constraints:
- must_sum_to_100: Splits must add to 100%
- allow_double_counting: Splits can exceed 100%
- cap_at_100: Each partner capped at 100%, total can exceed
- no_constraint: No validation

Return JSON only with this structure:
{
  "name": "User-friendly rule name",
  "model_type": "equal_split",
  "config": {},
  "split_constraint": "must_sum_to_100",
  "applies_to": {}
}

Config examples:
- role_weighted: {"weights": {"Implementation (SI)": 0.6, "Influence": 0.4}}
- time_decay: {"half_life_days": 30}
- activity_weighted: {"normalize": true}
- u_shaped: {"first_touch_weight": 0.4, "last_touch_weight": 0.4, "middle_weight": 0.2}

Applies_to filters (optional):
{"min_value": 100000, "target_type": "opportunity", "metadata": {"stage": "Closed Won"}}
"""

        user_prompt = f"Convert this to an attribution rule:\n\n{text}"

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract JSON from response
            content = response.content[0].text

            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                rule_config = json.loads(json_match.group())

                # Validate the config
                model_type = AttributionModel(rule_config["model_type"])
                is_valid, error = validate_rule_config(model_type, rule_config.get("config", {}))

                if not is_valid:
                    return False, None, f"Claude generated invalid config: {error}"

                return True, rule_config, None
            else:
                return False, None, "Could not extract JSON from Claude response"

        except Exception as e:
            return False, None, f"Claude API error: {str(e)}"

    def _parse_with_heuristics(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Fallback: Use pattern matching to infer rule type.
        """
        text_lower = text.lower()

        # Pattern: Equal split
        if any(word in text_lower for word in ["equal", "evenly", "same", "split evenly"]):
            return True, {
                "name": "Equal Split",
                "model_type": "equal_split",
                "config": {},
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Pattern: First touch
        if any(phrase in text_lower for phrase in ["first touch", "first partner", "first to touch", "sourcing gets 100"]):
            return True, {
                "name": "First Touch Attribution",
                "model_type": "first_touch",
                "config": {},
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Pattern: Last touch
        if any(phrase in text_lower for phrase in ["last touch", "last partner", "most recent", "final touch"]):
            return True, {
                "name": "Last Touch Attribution",
                "model_type": "last_touch",
                "config": {},
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Pattern: Time decay
        if any(word in text_lower for word in ["recent", "decay", "recency", "time"]):
            # Try to extract half-life if mentioned
            half_life = 30  # default
            if "30 day" in text_lower or "30-day" in text_lower:
                half_life = 30
            elif "60 day" in text_lower or "60-day" in text_lower:
                half_life = 60
            elif "90 day" in text_lower or "90-day" in text_lower:
                half_life = 90

            return True, {
                "name": f"Time Decay ({half_life}d half-life)",
                "model_type": "time_decay",
                "config": {"half_life_days": half_life},
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Pattern: Activity weighted
        if any(word in text_lower for word in ["activity", "activities", "meetings", "engagement", "work"]):
            return True, {
                "name": "Activity-Weighted Attribution",
                "model_type": "activity_weighted",
                "config": {"normalize": True},
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Pattern: Role-weighted (look for percentages)
        if "%" in text or any(word in text_lower for word in ["si", "implementation", "influence", "referral"]):
            # Try to extract role percentages
            weights = self._extract_role_weights(text)
            if weights:
                return True, {
                    "name": "Role-Weighted Attribution",
                    "model_type": "role_weighted",
                    "config": {"weights": weights},
                    "split_constraint": "must_sum_to_100",
                    "applies_to": {}
                }, None

        # Pattern: U-shaped
        if "u-shaped" in text_lower or "u shaped" in text_lower:
            return True, {
                "name": "U-Shaped Attribution",
                "model_type": "u_shaped",
                "config": {
                    "first_touch_weight": 0.4,
                    "last_touch_weight": 0.4,
                    "middle_weight": 0.2
                },
                "split_constraint": "must_sum_to_100",
                "applies_to": {}
            }, None

        # Could not parse
        return False, None, f"Could not parse: '{text}'. Try being more specific (e.g., 'split evenly', 'first touch gets 100%', 'SI 60% Influence 40%')"

    def _extract_role_weights(self, text: str) -> Optional[Dict[str, float]]:
        """
        Try to extract role weights from text.

        Examples:
        - "SI 60%, Influence 40%"
        - "Implementation gets 50%, others 25% each"
        """
        weights = {}

        # Pattern: "SI 60%"
        matches = re.findall(r'(SI|Implementation|Influence|Referral|ISV|Reseller)\s*(\d+)%', text, re.IGNORECASE)
        for role, percent in matches:
            role_normalized = self._normalize_role(role)
            weights[role_normalized] = float(percent) / 100.0

        if weights:
            return weights

        return None

    def _normalize_role(self, role: str) -> str:
        """
        Normalize role names to standard format.
        """
        role_lower = role.lower()

        if role_lower in ["si", "implementation"]:
            return "Implementation (SI)"
        elif role_lower == "influence":
            return "Influence"
        elif role_lower == "referral":
            return "Referral"
        elif role_lower == "isv":
            return "ISV"
        elif role_lower == "reseller":
            return "Reseller"
        else:
            return role  # Return as-is


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_nl_to_rule(
    natural_language: str,
    api_key: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Convenience function to parse natural language into rule config.

    Args:
        natural_language: User's description
        api_key: Optional Anthropic API key

    Returns:
        (success, rule_config, error_message)
    """
    parser = NaturalLanguageRuleParser(api_key=api_key)
    return parser.parse(natural_language)


def get_example_prompts() -> list[Dict[str, Any]]:
    """
    Get example natural language prompts for users.

    Returns:
        List of {prompt, expected_model, description}
    """
    return [
        {
            "prompt": "Split evenly among all partners",
            "expected_model": "equal_split",
            "description": "Each partner gets equal share"
        },
        {
            "prompt": "First partner to touch the deal gets 100%",
            "expected_model": "first_touch",
            "description": "Sourcing/first touch attribution"
        },
        {
            "prompt": "More recent partner touches get more credit",
            "expected_model": "time_decay",
            "description": "Exponential time decay (30-day half-life)"
        },
        {
            "prompt": "SI partners get 60%, Influence 30%, Referral 10%",
            "expected_model": "role_weighted",
            "description": "Weight by partner role"
        },
        {
            "prompt": "Split based on who did the most work (meetings/activities)",
            "expected_model": "activity_weighted",
            "description": "Weight by activity count"
        },
        {
            "prompt": "Last partner before close gets 100%",
            "expected_model": "last_touch",
            "description": "Closing/last touch attribution"
        },
        {
            "prompt": "40% to first touch, 40% to last touch, 20% to middle",
            "expected_model": "u_shaped",
            "description": "U-shaped multi-touch attribution"
        },
        {
            "prompt": "Implementation partners get 50% on enterprise deals over $100K",
            "expected_model": "role_weighted",
            "description": "Role-weighted with filters"
        }
    ]


def suggest_rule_from_template(template_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a prebuilt rule template by name.

    Args:
        template_name: Key from RULE_TEMPLATES

    Returns:
        Rule config dict or None
    """
    if template_name in RULE_TEMPLATES:
        template = RULE_TEMPLATES[template_name].copy()
        return {
            "name": template["name"],
            "model_type": template["model_type"].value,
            "config": template["config"],
            "split_constraint": template["split_constraint"].value,
            "applies_to": template.get("applies_to", {})
        }
    return None


# ============================================================================
# Interactive Rule Builder
# ============================================================================

class InteractiveRuleBuilder:
    """
    Guide users through rule creation with prompts and validation.
    """

    def __init__(self):
        self.steps = [
            self._choose_model_type,
            self._configure_model,
            self._set_constraints,
            self._set_filters
        ]
        self.rule_config = {}

    def build(self) -> Dict[str, Any]:
        """
        Run interactive rule builder (for CLI/terminal use).

        Returns:
            Complete rule configuration
        """
        print("=== Attribution Rule Builder ===\n")

        for step in self.steps:
            step()

        return self.rule_config

    def _choose_model_type(self):
        """Step 1: Choose attribution model"""
        print("Step 1: Choose attribution model")
        print("1. Equal Split - Divide evenly")
        print("2. Role-Weighted - Weight by partner role")
        print("3. Activity-Weighted - Weight by engagement")
        print("4. Time Decay - More credit to recent touches")
        print("5. First Touch - 100% to first partner")
        print("6. Last Touch - 100% to last partner")
        print("7. U-Shaped - 40/40/20 first/last/middle")

        choice = input("\nEnter choice (1-7): ").strip()

        model_map = {
            "1": AttributionModel.EQUAL_SPLIT,
            "2": AttributionModel.ROLE_WEIGHTED,
            "3": AttributionModel.ACTIVITY_WEIGHTED,
            "4": AttributionModel.TIME_DECAY,
            "5": AttributionModel.FIRST_TOUCH,
            "6": AttributionModel.LAST_TOUCH,
            "7": AttributionModel.U_SHAPED
        }

        self.rule_config["model_type"] = model_map.get(choice, AttributionModel.EQUAL_SPLIT).value
        print(f"\n✓ Selected: {self.rule_config['model_type']}\n")

    def _configure_model(self):
        """Step 2: Configure model-specific settings"""
        print("Step 2: Configure model settings")

        model_type = self.rule_config["model_type"]

        if model_type == "role_weighted":
            print("Enter role weights (e.g., 'SI:0.6 Influence:0.3 Referral:0.1')")
            weights_input = input("Weights: ").strip()
            weights = {}
            for part in weights_input.split():
                if ":" in part:
                    role, weight = part.split(":")
                    weights[role] = float(weight)
            self.rule_config["config"] = {"weights": weights}

        elif model_type == "time_decay":
            half_life = input("Half-life in days (default 30): ").strip() or "30"
            self.rule_config["config"] = {"half_life_days": int(half_life)}

        elif model_type == "activity_weighted":
            self.rule_config["config"] = {"normalize": True}

        elif model_type == "u_shaped":
            self.rule_config["config"] = {
                "first_touch_weight": 0.4,
                "last_touch_weight": 0.4,
                "middle_weight": 0.2
            }

        else:
            self.rule_config["config"] = {}

        print(f"\n✓ Config: {self.rule_config['config']}\n")

    def _set_constraints(self):
        """Step 3: Set split constraints"""
        print("Step 3: Split constraint")
        print("1. Must sum to 100%")
        print("2. Allow double-counting (can exceed 100%)")
        print("3. Cap each partner at 100%")

        choice = input("\nEnter choice (1-3, default 1): ").strip() or "1"

        constraint_map = {
            "1": "must_sum_to_100",
            "2": "allow_double_counting",
            "3": "cap_at_100"
        }

        self.rule_config["split_constraint"] = constraint_map.get(choice, "must_sum_to_100")
        print(f"\n✓ Constraint: {self.rule_config['split_constraint']}\n")

    def _set_filters(self):
        """Step 4: Set optional filters"""
        print("Step 4: Apply filters (optional)")
        print("Press Enter to skip, or enter filter (e.g., 'min_value:100000')")

        filter_input = input("Filter: ").strip()

        if filter_input:
            applies_to = {}
            for part in filter_input.split():
                if ":" in part:
                    key, value = part.split(":")
                    if key in ["min_value", "max_value"]:
                        applies_to[key] = float(value)
                    else:
                        applies_to[key] = value
            self.rule_config["applies_to"] = applies_to
        else:
            self.rule_config["applies_to"] = {}

        # Set rule name
        name = input("\nRule name (descriptive): ").strip()
        self.rule_config["name"] = name or "Custom Rule"

        print(f"\n✓ Complete!\n")
