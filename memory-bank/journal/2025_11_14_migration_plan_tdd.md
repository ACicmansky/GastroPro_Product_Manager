# Migration Plan: TDD Approach - November 14, 2025

## Overview
Created comprehensive migration plan using Test-Driven Development (TDD) approach to migrate entire application from old format to new 138-column e-shop format.

## Key Decisions Made

### 1. Migration Strategy
- **TDD Approach**: Write tests first, then implement
- **No Backward Compatibility**: Clean break, support only new format
- **Incremental Migration**: Phase by phase, one component at a time

### 2. Format Decisions
- **Input/Output**: New 138-column format for both
- **File Format**: XLSX as primary, CSV as fallback
- **Breaking Changes**: Acceptable - clean migration

### 3. Feature Decisions
- **Variant Matcher**: Skip updates (feature not currently used)
- **Image Merging**: Use source with most images available
- **Default Values**: Apply at end of pipeline if cells empty
- **Code Uppercase**: Apply on load and merge for consistency

### 4. Technical Decisions
- **Category Transformation**: Add "Tovary a kategórie > " prefix, change "/" to " > "
- **Column Names**: English names throughout (code, name, price, etc.)
- **All 138 Columns**: Always present, even if empty

## Migration Plan Structure

### Phase 0: Test Infrastructure Setup
- Create test directory structure
- Set up pytest configuration
- Create sample test data files
- Create conftest.py with fixtures

### Phase 1: Test Current Implementation ⭐ CRITICAL
**Purpose**: Establish baseline - all current functionality must pass tests before making changes

**Components to Test**:
1. Data Loading (CSV, encoding fallback)
2. XML Parsing (gastromarket, forgastro)
3. Data Merging (merge logic, price updates)
4. AI Enhancement (column updates, fuzzy matching)
5. Category Mapping (mapping, normalization)
6. Data Pipeline (full integration)

**Success Criteria**: All tests pass before proceeding

### Phase 2: OutputTransformer Module
- Write tests FIRST (will fail)
- Implement transformation logic
- Extract from standalone script
- Add image merging logic
- Tests must pass before proceeding

### Phase 3: Data Loading
- Write tests for XLSX loading FIRST
- Implement new loader
- Add format validation
- Uppercase codes on load
- Tests must pass

### Phase 4: XML Parser
- Write tests for new format output FIRST
- Update parser to output new format
- Apply transformations
- Tests must pass

### Phase 5: Data Merging
- Write tests for new merge logic FIRST
- Implement image priority merging
- Handle uppercase code matching
- Tests must pass

### Phase 6: AI Enhancement
- Write tests for new column names FIRST
- Update column references
- Update fuzzy matching
- Tests must pass

### Phase 7: Category Mapper
- Write tests for transformation FIRST
- Add transformation logic
- Update to use new columns
- Tests must pass

### Phase 8: Data Pipeline Integration
- Write integration tests FIRST
- Update pipeline to use new format
- Apply defaults at end
- Ensure column order
- Tests must pass

### Phase 9: Final Validation
- Run all tests
- Manual testing with real data
- Performance testing
- Code coverage > 80%

### Phase 10: Documentation & Cleanup
- Update README
- Update memory bank
- Clean up old code
- Update dependencies

## Test Execution Strategy

### Daily Workflow
1. Write tests for next feature
2. Run tests (should fail - Red)
3. Implement feature
4. Run tests (should pass - Green)
5. Refactor if needed
6. Commit when all tests pass

### Continuous Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only failed tests
pytest --lf
```

## Timeline Estimate
- **Phase 0-1**: 2-3 days (infrastructure + current tests)
- **Phase 2**: 1-2 days (OutputTransformer)
- **Phase 3**: 1 day (Data loading)
- **Phase 4**: 1-2 days (XML parser)
- **Phase 5**: 1-2 days (Data merging)
- **Phase 6**: 1 day (AI enhancement)
- **Phase 7**: 1 day (Category mapper)
- **Phase 8**: 2-3 days (Pipeline)
- **Phase 9**: 2-3 days (Validation)
- **Phase 10**: 1 day (Documentation)

**Total**: ~2-3 weeks

## Success Criteria

✅ All existing tests pass (Phase 1)
✅ All new tests pass (Phases 2-8)
✅ Code coverage > 80%
✅ No regressions in functionality
✅ Load XLSX with 138 columns
✅ Process feeds → new format
✅ Merge with image priority
✅ AI enhancement works
✅ Category mapping works
✅ Export XLSX successfully
✅ Data integrity maintained

## Risk Mitigation

1. **Test First**: Write tests before implementation
2. **Incremental**: One phase at a time
3. **Validation**: Run tests after each change
4. **Backup**: Git branches for rollback
5. **Documentation**: Update as we go

## Files Created

- `MIGRATION_PLAN_TDD.md` - Detailed migration plan with TDD approach
- Updated `memory-bank/activeContext.md` - Current focus and decisions
- Updated `memory-bank/progress.md` - In progress items
- This journal entry

## Next Immediate Steps

1. Create test directory structure
2. Set up pytest configuration
3. Create sample test data
4. Write tests for current CSV loading
5. Run tests - ensure all pass
6. Proceed to Phase 2

**Start with Phase 0 and 1 - get all current tests passing first!**

## Notes

- TDD approach ensures no regressions
- Each phase is independent and testable
- Can pause/resume at any phase boundary
- Tests serve as documentation
- Variant matcher explicitly skipped (not used)
- Focus on data integrity throughout migration
