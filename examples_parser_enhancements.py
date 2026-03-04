#!/usr/bin/env python3
"""
Example script demonstrating CP2K Parser Enhancements

This script showcases the new features added to the CP2K input parser:
1. X..Y Range parsing (Issue #72)
2. Deprecated keyword warnings (Issue #35)
3. Enhanced error reporting with context
4. Nested section support
5. Improved keyword parsing
"""

import io
import warnings
from cp2k_input_tools.parser import CP2KInputParser, CP2KInputParserSimplified
from cp2k_input_tools.keyword_helpers import (
    IntegerRange,
    kw_converter_int,
    register_deprecated_keyword,
    register_deprecated_section,
)
from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML


def demo_integer_range():
    """Demonstrate X..Y integer range parsing (Issue #72 fix)."""
    print("=" * 60)
    print("Demo: X..Y Integer Range Parsing (Issue #72)")
    print("=" * 60)
    
    # Parse integer ranges
    result1 = kw_converter_int("1..10")
    print(f"kw_converter_int('1..10') = {result1} (type: {type(result1).__name__})")
    
    result2 = kw_converter_int("-5..5")
    print(f"kw_converter_int('-5..5') = {result2} (type: {type(result2).__name__})")
    
    result3 = kw_converter_int("42")
    print(f"kw_converter_int('42') = {result3} (type: {type(result3).__name__})")
    
    # IntegerRange features
    r = IntegerRange(1, 5)
    print(f"\nIntegerRange(1, 5):")
    print(f"  - List: {r.to_list()}")
    print(f"  - Length: {len(r)}")
    print(f"  - Contains 3: {3 in r}")
    print(f"  - String: {str(r)}")
    print()


def demo_deprecated_keywords():
    """Demonstrate deprecated keyword warnings (Issue #35 fix)."""
    print("=" * 60)
    print("Demo: Deprecated Keyword Warnings (Issue #35)")
    print("=" * 60)
    
    # Register deprecated keywords
    register_deprecated_keyword(
        "OLD_PARAMETER",
        replacement="NEW_PARAMETER",
        message="OLD_PARAMETER is deprecated, please use NEW_PARAMETER"
    )
    
    # Parse input with deprecated keyword
    input_text = """
&GLOBAL
  PRINT_LEVEL MEDIUM
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
"""
    
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        tree = parser.parse(io.StringIO(input_text))
        
        print(f"Parsed input successfully!")
        print(f"Project name: {tree['global']['project_name']}")
        print(f"Run type: {tree['global']['run_type']}")
        
        if w:
            print(f"\nWarnings captured: {len(w)}")
            for warning in w:
                print(f"  - {warning.message}")
        else:
            print("\nNo warnings (expected for valid input)")
    print()


def demo_enhanced_error_reporting():
    """Demonstrate enhanced error reporting."""
    print("=" * 60)
    print("Demo: Enhanced Error Reporting")
    print("=" * 60)
    
    # Test with invalid section
    input_text = """
&FORCE_EVAL
  &INVALID_SECTION
  &END INVALID_SECTION
&END FORCE_EVAL
"""
    
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    
    try:
        tree = parser.parse(io.StringIO(input_text))
    except Exception as e:
        print(f"Error type: {type(e).__name__}")
        print(f"Error message:\n{e}")
        if hasattr(e, 'context') and e.context:
            print(f"\nError context available:")
            print(f"  - Section stack: {e.context.section_stack}")
    print()


def demo_nested_sections():
    """Demonstrate nested section support."""
    print("=" * 60)
    print("Demo: Nested Section Support")
    print("=" * 60)
    
    input_text = """
&FORCE_EVAL
  METHOD Quickstep
  &DFT
    &SCF
      MAX_SCF 100
      &MIXING
        METHOD BROYDEN_MIXING
        ALPHA 0.4
      &END MIXING
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
&END FORCE_EVAL
"""
    
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    tree = parser.parse(io.StringIO(input_text))
    
    print("Successfully parsed deeply nested sections!")
    print(f"Method: {tree['force_eval']['method']}")
    print(f"SCF MAX_SCF: {tree['force_eval']['dft']['scf']['max_scf']}")
    print(f"MIXING METHOD: {tree['force_eval']['dft']['scf']['mixing']['method']}")
    print(f"XC FUNCTIONAL: {tree['force_eval']['dft']['xc']['xc_functional']['_']}")
    print()


def demo_full_input():
    """Demonstrate parsing a full CP2K input file."""
    print("=" * 60)
    print("Demo: Full Input Parsing")
    print("=" * 60)
    
    input_text = """
&GLOBAL
  PROJECT_NAME water
  RUN_TYPE MD
  PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_SETS
    POTENTIAL_FILE_NAME POTENTIALS
    &MGRID
      CUTOFF 400
    &END MGRID
    &SCF
      MAX_SCF 50
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      A 10.0 0.0 0.0
      B 0.0 10.0 0.0
      C 0.0 0.0 10.0
    &END CELL
    &KIND H
      ELEMENT H
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND
    &KIND O
      ELEMENT O
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &MD
    STEPS 100
    TIMESTEP 0.5
    TEMPERATURE 300.0
  &END MD
&END MOTION
"""
    
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    tree = parser.parse(io.StringIO(input_text))
    
    print("Full input parsed successfully!")
    print(f"\nGlobal settings:")
    print(f"  - Project: {tree['global']['project_name']}")
    print(f"  - Run type: {tree['global']['run_type']}")
    
    print(f"\nDFT settings:")
    print(f"  - Method: {tree['force_eval']['method']}")
    print(f"  - Cutoff: {tree['force_eval']['dft']['mgrid']['cutoff']}")
    
    print(f"\nMD settings:")
    print(f"  - Steps: {tree['motion']['md']['steps']}")
    print(f"  - Timestep: {tree['motion']['md']['timestep']}")
    print(f"  - Temperature: {tree['motion']['md']['temperature']}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CP2K Parser Enhancement Examples")
    print("=" * 60 + "\n")
    
    demo_integer_range()
    demo_deprecated_keywords()
    demo_enhanced_error_reporting()
    demo_nested_sections()
    demo_full_input()
    
    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)
