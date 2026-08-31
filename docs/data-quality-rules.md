# Data-quality rules

| Dimension | Rule | Scope | Result when failed |
|---|---|---|---|
| Completeness | Required supplied fields are non-null | Customer/product extracts | Exception record |
| Validity | Email format and normalized phone length are valid | Customer extracts | Exception record |
| Validity | Quantity, price and revenue are positive; date parses | Sales | Exception record |
| Uniqueness | Source primary key is unique | Customer/product extracts | Critical exception |
| Consistency | Revenue equals quantity × unit price | Sales | Exception record |
| Referential integrity | Sales customer ID exists in CRM extract | Sales | Critical exception |
| Accuracy | Not scored automatically | All | Requires trusted external reference data |

The overall score is the count of passed atomic checks divided by evaluated checks, multiplied by 100. This is an operational indicator, not a claim that the data is clinically or commercially accurate. Accuracy remains explicitly unmeasured until a trusted reference source is available.

Severity is high by default and critical for primary-key and referential-integrity failures. Business owners can tune severity and weighting in a future configuration layer.
