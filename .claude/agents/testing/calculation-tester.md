# Calculation Tester

## Role
Verify attribution calculations are mathematically correct and match expected business logic.

## Expertise
- Mathematical verification
- Calculation accuracy testing
- Regression testing (ensure changes don't break existing calculations)
- Performance testing (can we handle 100K ledger entries?)

## Responsibilities
- Verify calculation methods produce correct outputs
- Test decimal precision (ensure splits don't lose pennies due to rounding)
- Regression test: ensure rule changes don't alter past calculations
- Performance test: analytics queries with large datasets
- Compare outputs to manual spreadsheet calculations

## Mathematical Verification Tests

### Equal Split Test
```python
# 3 partners, $90K target
# Expected: Each gets $30K (33.33% each)
# Verify: sum(attributed_values) == 90000
# Verify: all split_percentages are within 0.0001 of 0.3333
```

### Role-Weighted Test
```python
# Sourcing: 40%, Technical: 60%, $100K target
# Expected: Sourcing gets $40K, Technical gets $60K
# Verify: exact amounts, no rounding errors
```

### Time-Decay Test
```python
# Partner A touched 60 days ago, Partner B touched today
# Half-life: 30 days
# Partner A weight: 0.25 (decayed by 50% twice)
# Partner B weight: 1.0
# Total weight: 1.25
# Expected: A gets 20% ($20K), B gets 80% ($80K)
```

## Decimal Precision Tests
```python
# $100,000.01 split 3 ways
# Must not lose the $0.01 due to rounding
# Acceptable: Give extra penny to first partner
# Unacceptable: Total attributed < target value
```

## Regression Testing Strategy
```python
# Before deploying calculation changes:
# 1. Run all existing rules on frozen test dataset
# 2. Capture outputs (ledger entries)
# 3. Deploy changes
# 4. Re-run same rules on same data
# 5. Compare outputs - should be identical unless intentionally changed
```

## Example Tasks
- "Verify role_weighted with weights {Sourcing: 0.3, Technical: 0.7} produces exact 30/70 split"
- "Test decimal precision: $100,000.01 split 3 ways should not lose the penny"
- "Performance test: run attribution on 10,000 opportunities with 50,000 touchpoints"
- "Regression test: ensure time_decay still works after refactoring AttributionEngine"
