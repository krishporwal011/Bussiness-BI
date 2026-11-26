-- Run after tables exist and before or after loading data.
-- Primary and foreign keys are declared in 02_create_tables.sql.

CREATE INDEX ix_stg_invoice_item ON stg_transaction_line (invoice_id, item_key);
CREATE INDEX ix_stg_retained ON stg_transaction_line (is_retained, invoice_id);
CREATE INDEX ix_stg_item ON stg_transaction_line (item_key);
CREATE INDEX ix_fact_txn_date ON fact_transaction (transaction_date);
CREATE INDEX ix_fact_txn_customer ON fact_transaction (customer_key);
CREATE INDEX ix_fbi_item_basket ON fact_basket_item (item_key, basket_id);
CREATE INDEX ix_dim_product_name ON dim_product (item_name);

-- For large one-time loads, create non-constraint indexes after the INSERTs and
-- gather statistics. See sql/README.md for the two supported sequences.

