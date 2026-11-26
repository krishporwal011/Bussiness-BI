-- Oracle setup notes
--
-- Run this script while connected to the target analytical schema. Creating a
-- database user/schema requires DBA privileges and is intentionally not done
-- here. The remaining scripts use unqualified table names so they work in a
-- local schema, a dedicated reporting schema, or an Oracle Autonomous Database
-- user schema.
--
-- Recommended session settings:
ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';
ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';

-- Optional DBA example, not executed by this project:
-- CREATE USER market_basket IDENTIFIED BY "<secret supplied out of band>";
-- GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE SEQUENCE TO market_basket;
-- ALTER USER market_basket QUOTA UNLIMITED ON users;

