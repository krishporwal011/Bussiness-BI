# Power BI model relationships

Recommended model:

```text
DimProduct (1) ───────< FactBasketItem >─────── (1) BasketSummary
                              |
                              └─────────────── (1) DimDate [optional]

PairMetrics (precomputed, unordered; use directly or with DimItemA/DimItemB role copies)
DataQualitySummary (disconnected summary)
CleaningAudit (disconnected quality table)
ItemFrequency (dimension-like summary for item analysis)
```

The pair table has one row per normalized `item_a_key < item_b_key`. Do not create a bidirectional relationship that creates an ambiguous path from one product dimension into both pair roles. For pair slicers, either use the pair table fields directly or create two role-playing product dimensions (`DimItemA` and `DimItemB`) with one-to-many, single-direction relationships.

