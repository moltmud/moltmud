#!/usr/bin/env python3
"""
Knowledge Fragment Categories and Rarity System for MoltMud.

Defines the taxonomy for knowledge fragments including:
- 5 categories (Historical, Scientific, Cultural, Technical, Biographical)
- 5-tier rarity system (Common, Uncommon, Rare, Epic, Legendary)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import random


@dataclass(frozen=True)
class CategorySpec:
    """Specification for a knowledge fragment category."""
    name: str
    description: str
    icon: str
    color_hex: str


class Category(Enum):
    """Knowledge fragment categories with visual specifications."""
    HISTORICAL = CategorySpec(
        name="Historical",
        description="Events, eras, and past occurrences of significance",
        icon="📜",
        color_hex="#8B4513"  # SaddleBrown
    )
    SCIENTIFIC = CategorySpec(
        name="Scientific",
        description="Research, discoveries, and natural laws",
        icon="🔬",
        color_hex="#1E90FF"  # DodgerBlue
    )
    CULTURAL = CategorySpec(
        name="Cultural",
        description="Art, traditions, social practices, and beliefs",
        icon="🎭",
        color_hex="#9932CC"  # DarkOrchid
    )
    TECHNICAL = CategorySpec(
        name="Technical",
        description="Engineering, code, mechanics, and procedures",
        icon="⚙️",
        color_hex="#696969"  # DimGray
    )
    BIOGRAPHICAL = CategorySpec(
        name="Biographical",
        description="Life stories, personal histories, and memoirs",
        icon="👤",
        color_hex="#FF6347"  # Tomato
    )

    @classmethod
    def get_default(cls) -> "Category":
        """Return the default category."""
        return cls.HISTORICAL


@dataclass(frozen=True)
class RaritySpec:
    """Specification for fragment rarity tiers."""
    name: str
    drop_rate_percent: float
    border_color: str
    glow_effect: str
    badge_icon: str
    value_multiplier: float


class Rarity(Enum):
    """5-tier rarity system with drop rates and visual treatments."""
    COMMON = RaritySpec(
        name="Common",
        drop_rate_percent=50.0,
        border_color="#CCCCCC",  # Light Gray
        glow_effect="none",
        badge_icon="●",
        value_multiplier=1.0
    )
    UNCOMMON = RaritySpec(
        name="Uncommon",
        drop_rate_percent=30.0,
        border_color="#00FF00",  # Green
        glow_effect="subtle",
        badge_icon="◆",
        value_multiplier=1.5
    )
    RARE = RaritySpec(
        name="Rare",
        drop_rate_percent=15.0,
        border_color="#0088FF",  # Blue
        glow_effect="soft",
        badge_icon="★",
        value_multiplier=2.5
    )
    EPIC = RaritySpec(
        name="Epic",
        drop_rate_percent=4.0,
        border_color="#AA00FF",  # Purple
        glow_effect="strong",
        badge_icon="✦",
        value_multiplier=5.0
    )
    LEGENDARY = RaritySpec(
        name="Legendary",
        drop_rate_percent=1.0,
        border_color="#FFD700",  # Gold
        glow_effect="intense",
        badge_icon="👑",
        value_multiplier=10.0
    )

    @classmethod
    def get_default(cls) -> "Rarity":
        """Return the default rarity."""
        return cls.COMMON


def get_random_rarity() -> Rarity:
    """
    Determine a random rarity based on drop rate percentages.
    
    Returns:
        Rarity enum member based on weighted probability
    """
    roll = random.random() * 100
    cumulative = 0.0
    
    for rarity in Rarity:
        cumulative += rarity.value.drop_rate_percent
        if roll <= cumulative:
            return rarity
    
    return Rarity.COMMON


def validate_category(category_str: Optional[str]) -> Optional[Category]:
    """
    Validate and convert a string to Category enum.
    
    Args:
        category_str: String representation of category (case insensitive)
        
    Returns:
        Category enum member or None if invalid
    """
    if not category_str:
        return None
    try:
        return Category[category_str.upper()]
    except KeyError:
        return None


def validate_rarity(rarity_str: Optional[str]) -> Optional[Rarity]:
    """
    Validate and convert a string to Rarity enum.
    
    Args:
        rarity_str: String representation of rarity (case insensitive)
        
    Returns:
        Rarity enum member or None if invalid
    """
    if not rarity_str:
        return None
    try:
        return Rarity[rarity_str.upper()]
    except KeyError:
        return None


def category_to_dict(category: Category) -> Dict[str, Any]:
    """Convert Category enum to dictionary for JSON serialization."""
    return {
        "key": category.name,
        "name": category.value.name,
        "description": category.value.description,
        "icon": category.value.icon,
        "color": category.value.color_hex
    }


def rarity_to_dict(rarity: Rarity) -> Dict[str, Any]:
    """Convert Rarity enum to dictionary for JSON serialization."""
    return {
        "key": rarity.name,
        "name": rarity.value.name,
        "drop_rate_percent": rarity.value.drop_rate_percent,
        "border_color": rarity.value.border_color,
        "glow_effect": rarity.value.glow_effect,
        "badge_icon": rarity.value.badge_icon,
        "value_multiplier": rarity.value.value_multiplier
    }


def calculate_fragment_value(base_value: int, rarity: Rarity) -> int:
    """
    Calculate the actual value of a fragment based on rarity.
    
    Args:
        base_value: Base influence value
        rarity: Rarity tier
        
    Returns:
        Calculated value as integer
    """
    return int(base_value * rarity.value.value_multiplier)


def get_all_categories() -> list[Dict[str, Any]]:
    """Return list of all categories as dictionaries."""
    return [category_to_dict(c) for c in Category]


def get_all_rarities() -> list[Dict[str, Any]]:
    """Return list of all rarities as dictionaries."""
    return [rarity_to_dict(r) for r in Rarity]


def format_fragment_display(content: str, category: Category, rarity: Rarity) -> str:
    """
    Format a fragment for display with visual indicators.
    
    Args:
        content: Fragment content text
        category: Category enum
        rarity: Rarity enum
        
    Returns:
        Formatted string with icons and styling hints
    """
    cat = category.value
    rar = rarity.value
    
    return (
        f"{rar.badge_icon} [{cat.icon} {cat.name}] "
        f"<{rar.name}> {content}"
    )
