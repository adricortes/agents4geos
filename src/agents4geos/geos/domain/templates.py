"""Pre-built simulation templates for guided file creation."""

from __future__ import annotations

from geos_tui.schema.model import SchemaElement, SchemaModel
from geos_tui.xml.state import DocumentState, ElementState

TEMPLATES: dict[str, dict] = {
    "single_phase_flow": {
        "label": "Single-Phase Flow",
        "description": "Basic single-phase flow through a porous medium with a compressible fluid.",
        "sections": {
            "Solvers": {
                "children": [
                    {"element": "SinglePhaseFVM", "attrs": {
                        "name": "singlePhaseFlow",
                        "discretization": "fluidTPFA",
                        "targetRegions": "{ region }",
                    }},
                ],
            },
            "Mesh": {
                "children": [
                    {"element": "InternalMesh", "attrs": {
                        "name": "mesh",
                        "elementTypes": "{ C3D8 }",
                        "xCoords": "{ 0, 10 }",
                        "yCoords": "{ 0, 1 }",
                        "zCoords": "{ 0, 1 }",
                        "nx": "{ 10 }",
                        "ny": "{ 1 }",
                        "nz": "{ 1 }",
                        "cellBlockNames": "{ block }",
                    }},
                ],
            },
            "Constitutive": {
                "children": [
                    {"element": "CompressibleSinglePhaseFluid", "attrs": {
                        "name": "fluid",
                        "defaultDensity": "1000",
                        "defaultViscosity": "0.001",
                        "referencePressure": "0.0",
                        "compressibility": "5e-10",
                        "viscosibility": "0.0",
                    }},
                    {"element": "CompressibleSolidConstantPermeability", "attrs": {
                        "name": "rock",
                        "solidModelName": "nullSolid",
                        "porosityModelName": "rockPorosity",
                        "permeabilityModelName": "rockPerm",
                    }},
                    {"element": "NullModel", "attrs": {
                        "name": "nullSolid",
                    }},
                    {"element": "PressurePorosity", "attrs": {
                        "name": "rockPorosity",
                        "defaultReferencePorosity": "0.05",
                        "referencePressure": "0.0",
                        "compressibility": "1.0e-9",
                    }},
                    {"element": "ConstantPermeability", "attrs": {
                        "name": "rockPerm",
                        "permeabilityComponents": "{ 1e-16, 1e-16, 1e-16 }",
                    }},
                ],
            },
            "ElementRegions": {
                "children": [
                    {"element": "CellElementRegion", "attrs": {
                        "name": "region",
                        "cellBlocks": "{ * }",
                        "materialList": "{ fluid, rock }",
                    }},
                ],
            },
            "Events": {
                "attrs": {"maxTime": "1e4"},
                "children": [
                    {"element": "PeriodicEvent", "attrs": {
                        "name": "solverApp",
                        "forceDt": "1e3",
                        "target": "/Solvers/singlePhaseFlow",
                    }},
                    {"element": "PeriodicEvent", "attrs": {
                        "name": "output",
                        "timeFrequency": "1e3",
                        "target": "/Outputs/vtkOutput",
                    }},
                ],
            },
            "NumericalMethods": {
                "children": [
                    {"element": "FiniteVolume", "attrs": {}, "children": [
                        {"element": "TwoPointFluxApproximation", "attrs": {"name": "fluidTPFA"}},
                    ]},
                ],
            },
            "Outputs": {
                "children": [
                    {"element": "VTK", "attrs": {"name": "vtkOutput"}},
                ],
            },
        },
    },
    "compositional_two_phase": {
        "label": "Compositional Two-Phase",
        "description": "Compositional multiphase flow with two phases and two components.",
        "sections": {
            "Solvers": {
                "children": [
                    {"element": "CompositionalMultiphaseFVM", "attrs": {
                        "name": "compFlow",
                        "discretization": "fluidTPFA",
                        "targetRegions": "{ region }",
                        "temperature": "368.15",
                        "useMass": "1",
                    }},
                ],
            },
            "Mesh": {
                "children": [
                    {"element": "InternalMesh", "attrs": {
                        "name": "mesh",
                        "elementTypes": "{ C3D8 }",
                        "xCoords": "{ 0, 100 }",
                        "yCoords": "{ 0, 1 }",
                        "zCoords": "{ 0, 1 }",
                        "nx": "{ 20 }",
                        "ny": "{ 1 }",
                        "nz": "{ 1 }",
                        "cellBlockNames": "{ block }",
                    }},
                ],
            },
            "Constitutive": {
                "children": [
                    {"element": "CompositionalMultiphaseFluid", "attrs": {
                        "name": "fluid",
                        "phaseNames": "{ oil, gas }",
                        "equationsOfState": "{ PR, PR }",
                        "componentNames": "{ C1, C10 }",
                        "componentCriticalPressure": "{ 46e5, 25.3e5 }",
                        "componentCriticalTemperature": "{ 190.6, 622.0 }",
                        "componentAcentricFactor": "{ 0.011, 0.443 }",
                        "componentMolarWeight": "{ 16e-3, 134e-3 }",
                        "componentVolumeShift": "{ 0, 0 }",
                        "componentBinaryCoeff": "{ { 0, 0 }, { 0, 0 } }",
                    }},
                    {"element": "CompressibleSolidConstantPermeability", "attrs": {
                        "name": "rock",
                        "solidModelName": "nullSolid",
                        "porosityModelName": "rockPorosity",
                        "permeabilityModelName": "rockPerm",
                    }},
                    {"element": "NullModel", "attrs": {
                        "name": "nullSolid",
                    }},
                    {"element": "PressurePorosity", "attrs": {
                        "name": "rockPorosity",
                        "defaultReferencePorosity": "0.2",
                        "referencePressure": "0.0",
                        "compressibility": "1.0e-9",
                    }},
                    {"element": "ConstantPermeability", "attrs": {
                        "name": "rockPerm",
                        "permeabilityComponents": "{ 1.0e-16, 1.0e-16, 1.0e-16 }",
                    }},
                    {"element": "BrooksCoreyRelativePermeability", "attrs": {
                        "name": "relperm",
                        "phaseNames": "{ oil, gas }",
                        "phaseMinVolumeFraction": "{ 0.1, 0.15 }",
                        "phaseRelPermExponent": "{ 2.0, 2.0 }",
                        "phaseRelPermMaxValue": "{ 0.8, 0.9 }",
                    }},
                ],
            },
            "ElementRegions": {
                "children": [
                    {"element": "CellElementRegion", "attrs": {
                        "name": "region",
                        "cellBlocks": "{ * }",
                        "materialList": "{ fluid, rock, relperm }",
                    }},
                ],
            },
            "Events": {
                "attrs": {"maxTime": "1e5"},
                "children": [
                    {"element": "PeriodicEvent", "attrs": {
                        "name": "solverApp",
                        "forceDt": "1e3",
                        "target": "/Solvers/compFlow",
                    }},
                ],
            },
            "NumericalMethods": {
                "children": [
                    {"element": "FiniteVolume", "attrs": {}, "children": [
                        {"element": "TwoPointFluxApproximation", "attrs": {"name": "fluidTPFA"}},
                    ]},
                ],
            },
            "Outputs": {
                "children": [{"element": "VTK", "attrs": {"name": "vtkOutput"}}],
            },
        },
    },
    "co2_injection": {
        "label": "CO2 Injection",
        "description": "CO2 injection into a saline aquifer using the Phillips CO2-brine model.",
        "sections": {
            "Solvers": {
                "children": [
                    {"element": "CompositionalMultiphaseFVM", "attrs": {
                        "name": "compFlow",
                        "discretization": "fluidTPFA",
                        "targetRegions": "{ reservoir }",
                        "temperature": "368.15",
                        "useMass": "1",
                    }},
                ],
            },
            "Mesh": {
                "children": [
                    {"element": "InternalMesh", "attrs": {
                        "name": "mesh",
                        "elementTypes": "{ C3D8 }",
                        "xCoords": "{ 0, 500 }",
                        "yCoords": "{ 0, 500 }",
                        "zCoords": "{ 0, 50 }",
                        "nx": "{ 10 }",
                        "ny": "{ 10 }",
                        "nz": "{ 5 }",
                        "cellBlockNames": "{ block }",
                    }},
                ],
            },
            "Constitutive": {
                "children": [
                    {"element": "CO2BrinePhillipsFluid", "attrs": {
                        "name": "fluid",
                        "phaseNames": "{ gas, water }",
                        "componentNames": "{ co2, water }",
                        "componentMolarWeight": "{ 44e-3, 18e-3 }",
                        "phasePVTParaFiles": "{ pvtgas.txt, pvtliquid.txt }",
                        "flashModelParaFile": "flashModel.txt",
                    }},
                    {"element": "CompressibleSolidConstantPermeability", "attrs": {
                        "name": "rock",
                        "solidModelName": "nullSolid",
                        "porosityModelName": "rockPorosity",
                        "permeabilityModelName": "rockPerm",
                    }},
                    {"element": "NullModel", "attrs": {
                        "name": "nullSolid",
                    }},
                    {"element": "PressurePorosity", "attrs": {
                        "name": "rockPorosity",
                        "defaultReferencePorosity": "0.2",
                        "referencePressure": "0.0",
                        "compressibility": "1.0e-9",
                    }},
                    {"element": "ConstantPermeability", "attrs": {
                        "name": "rockPerm",
                        "permeabilityComponents": "{ 1e-15, 1e-15, 1e-16 }",
                    }},
                    {"element": "BrooksCoreyRelativePermeability", "attrs": {
                        "name": "relperm",
                        "phaseNames": "{ gas, water }",
                        "phaseMinVolumeFraction": "{ 0.05, 0.30 }",
                        "phaseRelPermExponent": "{ 2.0, 2.0 }",
                        "phaseRelPermMaxValue": "{ 1.0, 1.0 }",
                    }},
                ],
            },
            "ElementRegions": {
                "children": [
                    {"element": "CellElementRegion", "attrs": {
                        "name": "reservoir",
                        "cellBlocks": "{ * }",
                        "materialList": "{ fluid, rock, relperm }",
                    }},
                ],
            },
            "Events": {
                "attrs": {"maxTime": "3.1557e7"},
                "children": [
                    {"element": "PeriodicEvent", "attrs": {
                        "name": "solverApp",
                        "forceDt": "1e4",
                        "target": "/Solvers/compFlow",
                    }},
                    {"element": "PeriodicEvent", "attrs": {
                        "name": "output",
                        "timeFrequency": "3.1557e6",
                        "target": "/Outputs/vtkOutput",
                    }},
                ],
            },
            "NumericalMethods": {
                "children": [
                    {"element": "FiniteVolume", "attrs": {}, "children": [
                        {"element": "TwoPointFluxApproximation", "attrs": {"name": "fluidTPFA"}},
                    ]},
                ],
            },
            "Outputs": {
                "children": [{"element": "VTK", "attrs": {"name": "vtkOutput"}}],
            },
        },
    },
}


def build_template_state(template_key: str, schema: SchemaModel) -> DocumentState:
    """Build a DocumentState from a template definition."""
    template = TEMPLATES[template_key]
    if schema.root is None:
        raise ValueError("Schema has no root element")
    root_elem = schema.root
    root_state = ElementState(schema_element=root_elem, attributes={}, children=[])

    for section_name, section_def in template["sections"].items():
        section_schema = _find_child(root_elem, section_name)
        if section_schema is None:
            continue
        section_state = _build_section(section_schema, section_def, schema)
        root_state.children.append(section_state)

    return DocumentState(root=root_state, source_path=None, is_modified=False)


def _build_section(
    schema_elem: SchemaElement, section_def: dict, schema: SchemaModel
) -> ElementState:
    attrs = section_def.get("attrs", {})
    children = []
    for child_def in section_def.get("children", []):
        child_schema = _find_child(schema_elem, child_def["element"])
        if child_schema is None:
            # Try global elements
            child_schema = schema.elements.get(child_def["element"])
        if child_schema is None:
            continue
        child_state = _build_section(child_schema, child_def, schema)
        children.append(child_state)
    return ElementState(
        schema_element=schema_elem, attributes=attrs, children=children
    )


def _find_child(parent: SchemaElement, name: str) -> SchemaElement | None:
    for child in parent.children:
        if child.name == name:
            return child
    return None
