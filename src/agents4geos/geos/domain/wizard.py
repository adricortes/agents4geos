"""Wizard step definitions for guided input file creation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WizardStep:
    """A single step in the wizard flow."""

    section_key: str
    label: str
    xml_section: str  # corresponding XML element name
    required: bool = True


WIZARD_STEPS: list[WizardStep] = [
    WizardStep("solver", "Choose Solver", "Solvers"),
    WizardStep("mesh", "Define Mesh", "Mesh"),
    WizardStep("constitutive", "Set Materials & Fluids", "Constitutive"),
    WizardStep("regions", "Map Element Regions", "ElementRegions"),
    WizardStep("field_specs", "Boundary & Initial Conditions", "FieldSpecifications"),
    WizardStep("events", "Time Stepping & Events", "Events"),
    WizardStep("outputs", "Configure Outputs", "Outputs"),
    WizardStep("numerical", "Numerical Methods", "NumericalMethods"),
    WizardStep("review", "Review & Save", ""),
]
