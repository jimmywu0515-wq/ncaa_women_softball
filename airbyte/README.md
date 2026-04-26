# Airbyte Integration Strategy

In a production Azure environment, Airbyte is used to handle the EL (Extract & Load) phase of the pipeline for sources that have structured APIs or standard connectors (e.g., historical stats databases).

### Implementation:
- **Source**: NCAA Statistics API / CSV Buckets.
- **Destination**: Azure SQL Database (staging schema).
- **Sync Frequency**: Daily, orchestrated via Airflow AirbyteOperator.

For the custom web scraping (Sidearm Sports PBP), we utilize the custom Python scrapers located in `/pipelines` which are triggered by Airflow.
