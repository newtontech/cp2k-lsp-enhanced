# CP2K Parser Enhancement Update

This document describes the enhancements made to the CP2K input file parser to address the known issues and improve overall functionality.

## Summary of Changes

### 1. Enhanced Error Reporting (All Issues)

**Files Modified:**
- `cp2k_input_tools/parser_errors.py` - Complete rewrite with enhanced context

**New Features:**
- `ErrorContext` dataclass with comprehensive error location information
- Error markers showing exact position in source code
- Section stack tracking for nested context
- Suggestions for common mistakes (typos, missing END statements)
- Improved error messages with line numbers and filenames

**Example:**
```python
# Before:
InvalidSectionError: invalid section 'DFT_INVALID'

# After:
InvalidSectionError: invalid section 'DFT_INVALID'
  Context: in input.inp line 5 section: FORCE_EVAL
    &DFT_INVALID
    ^
  Did you mean: DFT?
```

### 2. X..Y Range Parsing (Issue #72)

**Files Modified:**
- `cp2k_input_tools/keyword_helpers.py` - Enhanced IntegerRange support

**New Features:**
- Robust X..Y integer range parsing with validation
- `IntegerRange` dataclass with iteration and membership support
- `parse_integer_range()` helper function
- Proper error handling for invalid ranges (start > end)

**Example:**
```python
from cp2k_input_tools.keyword_helpers import IntegerRange, kw_converter_int

# Range parsing
result = kw_converter_int("1..10")  # Returns IntegerRange(1, 10)
result = kw_converter_int("-5..5")  # Returns IntegerRange(-5, 5)

# IntegerRange features
r = IntegerRange(1, 10)
list(r)       # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
5 in r        # True
len(r)        # 10
```

### 3. Deprecated Keyword Support (Issue #35)

**Files Modified:**
- `cp2k_input_tools/keyword_helpers.py` - Added deprecation registry
- `cp2k_input_tools/parser.py` - Integrated warning system

**New Features:**
- `register_deprecated_keyword()` - Register deprecated keywords with replacements
- `register_deprecated_section()` - Register deprecated sections
- Automatic warning generation during parsing
- `parser.warnings` property to access all warnings
- Pre-registered common CP2K deprecations

**Example:**
```python
from cp2k_input_tools.keyword_helpers import register_deprecated_keyword
import warnings

# Register a deprecated keyword
register_deprecated_keyword(
    "OLD_PARAM", 
    replacement="NEW_PARAM",
    message="OLD_PARAM is deprecated, use NEW_PARAM instead"
)

# Parse file - warnings will be issued automatically
parser = CP2KInputParserSimplified()
with warnings.catch_warnings(record=True) as w:
    tree = parser.parse(fhandle)
    for warning in w:
        print(f"Warning: {warning.message}")

# Or check warnings after parsing
print(parser.warnings)
```

### 4. Enhanced Nested Section Support

**Files Modified:**
- `cp2k_input_tools/parser.py` - Improved section tracking

**New Features:**
- Section stack tracking for deep nesting
- Better error messages for section mismatches
- Support for arbitrarily deep nesting levels
- Section line number tracking

**Example:**
```cp2k
&FORCE_EVAL
  &DFT
    &SCF
      &MIXING
        METHOD BROYDEN_MIXING
      &END MIXING
    &END SCF
  &END DFT
&END FORCE_EVAL
```

### 5. Improved Keyword Parsing Logic (Issue #69)

**Files Modified:**
- `cp2k_input_tools/parser.py` - Enhanced keyword resolution
- `cp2k_input_tools/tokenizer.py` - Better tokenization context

**New Features:**
- Fuzzy matching for keyword/section suggestions
- Better handling of unknown keywords
- Enhanced context preservation during tokenization
- `tokenize_with_context()` function for detailed token info

### 6. Keyword Value Conversion Improvements (Issue #55)

**Files Modified:**
- `cp2k_input_tools/keyword_helpers.py` - Optimized converters

**Optimizations:**
- Efficient boolean value parsing
- Fast Fortran notation conversion (D to E)
- Cached unit registry lookups
- Improved fraction parsing

## API Changes

### New Classes

#### ErrorContext
```python
@dataclass
class ErrorContext:
    line: Optional[str] = None
    filename: Optional[str] = None
    linenr: Optional[int] = None
    colnr: Optional[int] = None
    colnrs: List[int] = field(default_factory=list)
    ref_colnr: Optional[int] = None
    ref_line: Optional[str] = None
    section: Any = None
    section_stack: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None
```

#### IntegerRange
```python
@dataclass(frozen=True)
class IntegerRange:
    start: int
    end: int
    
    def __iter__(self): ...
    def __contains__(self, value): ...
    def __len__(self): ...
    def to_list(self): ...
```

### New Functions

```python
# Deprecation management
def register_deprecated_keyword(name: str, replacement: Optional[str] = None, message: Optional[str] = None)
def register_deprecated_section(name: str, replacement: Optional[str] = None, message: Optional[str] = None)
def check_deprecated_keyword(name: str) -> Optional[DeprecatedKeywordWarning]
def check_deprecated_section(name: str) -> Optional[DeprecatedSectionWarning]

# Range parsing
def parse_integer_range(string: str) -> Union[int, IntegerRange, str]

# Tokenization
def tokenize_with_context(string: str, filename: Optional[str] = None, line_number: Optional[int] = None) -> List[Token]
```

### Modified Parser Classes

All parser classes now have:
- `warnings` property to access parsing warnings
- Enhanced error context in all exceptions
- Better section stack tracking

## Testing

New comprehensive test suite: `tests/test_parser_enhanced.py`

Test coverage:
- IntegerRange parsing (10 tests)
- Deprecated keyword handling (5 tests)
- Error reporting (6 tests)
- Tokenizer enhancements (5 tests)
- Nested section support (3 tests)
- Parser warnings (2 tests)
- Keyword value conversion (3 tests)
- Error suggestions (2 tests)
- Integration tests (2 tests)

**Run tests:**
```bash
cd ~/desktop/code/cp2k-lsp-enhanced
pytest tests/test_parser_enhanced.py -v
```

## Backward Compatibility

All changes are backward compatible:
- Existing code will continue to work without modifications
- New features are opt-in (e.g., deprecation warnings)
- Error messages are enhanced but exception types remain the same
- All existing tests pass

## Migration Guide

### To use enhanced error reporting:
No changes needed - errors now include more context automatically.

### To use deprecated keyword warnings:
```python
import warnings
from cp2k_input_tools.keyword_helpers import register_deprecated_keyword

# Register your deprecated keywords
register_deprecated_keyword("OLD_KW", "NEW_KW")

# Enable warnings
warnings.simplefilter("always")

# Parse as usual
parser = CP2KInputParser()
tree = parser.parse(fhandle)
```

### To use X..Y ranges:
```python
from cp2k_input_tools.keyword_helpers import IntegerRange

# In your CP2K input:
# &SECTION
#   RANGE 1..100
# &END

# The parser now automatically converts to IntegerRange
```

## Known Limitations

1. Deprecation registry is in-memory only - should be loaded from XML or config file
2. Fuzzy matching for suggestions is basic (prefix-based)
3. Section stack in errors shows path but not exact nesting depth

## Future Enhancements

- Load deprecations from CP2K XML schema
- More sophisticated fuzzy matching (Levenshtein distance)
- Configurable warning levels
- Performance metrics for large files
