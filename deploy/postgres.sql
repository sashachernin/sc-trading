-- Run as PostgreSQL administrator; replace password interactively, never commit it.
CREATE ROLE aiinvest LOGIN;
CREATE DATABASE ai_investment_lab OWNER aiinvest;
REVOKE ALL ON DATABASE ai_investment_lab FROM PUBLIC;
-- In psql: \password aiinvest
-- Restrict pg_hba.conf to the service host and SCRAM authentication.
