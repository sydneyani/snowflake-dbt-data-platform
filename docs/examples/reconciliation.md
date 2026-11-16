# Source-to-target reconciliation

- Generated: 2026-11-16T17:23:52+00:00
- Seed: 42
- Pipeline status: PASS

Pipeline control totals tie to the raw extract. Explained source findings: header_tie_out.

| Check | Status | Source | Target | Variance | Detail |
| --- | --- | --- | --- | --- | --- |
| sales_accepted_doc_total | PASS | raw lines=8801, fact lines=8801, manifest lines=8801 | raw amount=2786783.00, fact amount=2786783.00, manifest amount=2786783.00 | 0.00 | Accepted line count and document amount across manifest, raw SQL, and the fact. |
| sales_accepted_usd_total | PASS | 2907700.45 | 2907700.45 | 0.00 | Target minus source, tolerance 0.01 USD. |
| work_order_planned_qty | PASS | count=1400; qty=145999.000 | count=1400; qty=145999.000 | 0.000 | Work order count and planned quantity, raw versus fact. |
| header_tie_out | EXPLAINED | 500421 residual 25.00 | lines + freight | 25.00 | One source document does not tie. The line fact keeps the line amounts. This is not a pipeline variance. |
| sap_customer_duplicate | PASS | raw_rows=201; distinct=200 | current_dim=200 | 1 | One duplicate KUNNR is in the extract and one current dimension row remains. |
| customer_snapshot_closed_versions | PASS | 30 | 30 | 0 | Changed customers (20 SAP, 10 Oracle) have one closed snapshot version. |
| test_accounts_absent_from_fact | PASS | 0 | 0 | 0 | Test account lines stay in the exception mart. |
| shared_customer_tax_ids | PASS | tax_ids=30; rows=60 | tax_ids=30; rows=60 | 0 | Thirty tax ids are shared by exactly two current ERP accounts. |
| customer_point_in_time | PASS | Columbus | Austin | 0 | SAP document 0000042201 uses the pre-change city and 0000042202 uses Austin. |
| header_freight_ties | PASS | freight=50.00 | residual=0.00 | 0.00 | Document 500420 carries header freight that is not on the lines. Header minus lines minus freight is zero, so the line fact is not expected to include that freight. |
