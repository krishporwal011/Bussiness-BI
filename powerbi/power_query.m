// Power Query Advanced Editor starter. Create a text parameter named ProjectRoot.
let
    ProjectRoot = "C:\\path\\to\\HCL-project",
    Csv = (relativePath as text) as table =>
        let
            Source = Csv.Document(
                File.Contents(ProjectRoot & "\\" & relativePath),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
        in
            Promoted,
    DimProduct = Table.TransformColumnTypes(Csv("data\\cleaned\\product_summary.csv"), {
        {"item_key", type text}, {"item_name", type text}, {"basket_count", Int64.Type},
        {"total_quantity", type number}, {"total_revenue", type number}
    }),
    BasketSummary = Table.TransformColumnTypes(Csv("data\\cleaned\\basket_summary.csv"), {
        {"basket_id", type text}, {"transaction_date", type datetime}, {"customer_id", type text},
        {"country", type text}, {"distinct_item_count", Int64.Type}, {"total_quantity", type number},
        {"total_revenue", type number}, {"item_line_count", Int64.Type}, {"is_single_item", Int64.Type}
    }),
    FactBasketItem = Table.TransformColumnTypes(Csv("data\\cleaned\\basket_item_presence.csv"), {
        {"basket_id", type text}, {"item_key", type text}, {"item_name", type text},
        {"transaction_date", type datetime}, {"customer_id", type text}, {"country", type text},
        {"quantity", type number}, {"revenue", type number}, {"line_count", Int64.Type}, {"presence", Int64.Type}
    }),
    PairMetrics = Table.TransformColumnTypes(Csv("outputs\\python_pair_metrics.csv"), {
        {"item_a_key", type text}, {"item_a_name", type text}, {"item_b_key", type text},
        {"item_b_name", type text}, {"pair_count", Int64.Type}, {"basket_count", Int64.Type},
        {"item_a_basket_count", Int64.Type}, {"item_b_basket_count", Int64.Type},
        {"support", type number}, {"confidence_a_to_b", type number},
        {"confidence_b_to_a", type number}, {"lift", type number}, {"rank", Int64.Type}
    }),
    ItemFrequency = Table.TransformColumnTypes(Csv("outputs\\python_item_frequency.csv"), {
        {"item_key", type text}, {"item_name", type text}, {"basket_count", Int64.Type}
    }),
    DataQualitySummary = Table.TransformColumnTypes(Csv("data\\cleaned\\data_quality_summary.csv"), {
        {"metric", type text}, {"value", Int64.Type}
    }),
    CleaningAudit = Table.TransformColumnTypes(Csv("data\\cleaned\\cleaning_audit.csv"), {
        {"primary_exclusion_reason", type text}, {"row_count", Int64.Type}, {"pct_raw", type number}
    })
in
    [DimProduct = DimProduct, BasketSummary = BasketSummary, FactBasketItem = FactBasketItem,
     PairMetrics = PairMetrics, ItemFrequency = ItemFrequency,
     DataQualitySummary = DataQualitySummary, CleaningAudit = CleaningAudit]
