-- The daily job snapshots the customer master twice. Changed customers must
-- have a closed version. 30 = 20 SAP accounts + 10 Oracle accounts.

select count(*) as closed_rows
from {{ ref('snap_customer') }}
where dbt_valid_to is not null
having count(*) <> 30
