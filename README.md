# NCAA Women's Softball Data Engineering Project

## Overview
This project establishes a robust data ecosystem for NCAA Women's Softball, specifically targeting IU Indy (formerly IUPUI) 2024 season data. It provides an automated pipeline for performance analysis and recruitment optimization.

## Key Features
- **ETL Pipelines**: Python-based scrapers that ingest and structure PBP data from `stats.ncaa.org` and transfer portal metrics from On3.
- **Data Modeling**: Predictive modeling using `scikit-learn` to generate performance heat maps and strategic insights.
- **Containerization**: Fully Dockerized environment for reproducible data workflows.
- **Cloud Readiness**: Architecture designed for integration with **Microsoft Azure** (Blob Storage) and **Snowflake** Data Warehouse.
- **Feature Engineering**: Automated position classification and hit location parsing from raw text.

## Tech Stack
- **Languages**: Python (Pandas, Scikit-learn, SQLAlchemy, Streamlit)
- **Database**: SQLite (Local Warehouse), Snowflake/Azure (Cloud ready)
- **DevOps**: Docker, Docker Compose
- **Visualization**: Matplotlib, Seaborn
