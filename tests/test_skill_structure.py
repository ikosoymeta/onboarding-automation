import pytest
from pathlib import Path


def test_skill_directory_exists():
    """Test that skill directory exists in correct location."""
    skill_path = Path.home() / ".llms" / "skills" / "vendor-onboarding"
    assert skill_path.exists(), f"Skill directory not found at {skill_path}"


def test_skill_file_exists():
    """Test that skill file exists."""
    skill_path = Path.home() / ".llms" / "skills" / "vendor-onboarding" / "SKILL.md"
    assert skill_path.exists(), f"Skill file not found at {skill_path}"


def test_skill_has_overview_section():
    """Test that skill file contains Overview section."""
    skill_path = Path.home() / ".llms" / "skills" / "vendor-onboarding" / "SKILL.md"
    content = skill_path.read_text()
    assert "# Vendor Onboarding" in content
    assert "## Overview" in content
