# Lakebase Support Ticket App
URL: https://assignment1-7474650258708166.aws.databricksapps.com/
## Summary

1. This folder contains the deployable Streamlit source for Bootcamp Assignment 1.
2. The App uses the attached Lakebase resource rather than hard-coded credentials.
3. Startup creates the required schema and sample data through the App identity.
4. Deployment and live Lakebase verification must be completed before the assignment is marked done.

This Streamlit application is the DataExpert Databricks Bootcamp Day 1 assignment.

## Required Databricks resource

Attach a Lakebase Autoscaling database to the Databricks App with resource key
`postgres` and permission `Can connect and create`.

At deployment time Databricks supplies the standard `PG*` connection variables.
`app.yaml` maps the `postgres` resource to `ENDPOINT_NAME`, which the Databricks
SDK uses to generate rotating Lakebase OAuth credentials.

No password, token, host, client ID, or connection URL is stored in this folder.

## Files

- `app.py`: Streamlit UI and the five required user workflows.
- `db.py`: pooled PostgreSQL access with OAuth token rotation and parameterized SQL.
- `schema.sql`: idempotent schema and sample-data bootstrap.
- `verify.sql`: read-only assignment verification queries.
- `app.yaml`: Databricks Apps runtime and resource mapping.
- `requirements.txt`: Python dependencies installed during deployment.

## Deployment sequence

1. Attach the Lakebase resource with key `postgres`.
2. Upload or sync this folder to a Databricks workspace folder.
3. Deploy App `assignment1` from that workspace folder.
4. The App initializes `support_app.tickets` and
   `support_app.ticket_messages` through its own service-principal identity.
5. Run `verify.sql` in the Lakebase SQL Editor and save the results.

## Reflection

The most difficult part was configuring the Databricks App resource and establishing secure 
Lakebase connectivity without hard-coded credentials. 
Lakebase differs from a traditional analytics table because it supports low-latency transactional 
reads and writes for interactive applications. 
Next, I would add status filtering and summary metrics to help users triage support tickets more efficiently.
