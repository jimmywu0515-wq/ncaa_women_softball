# NCAA Women's Softball Performance Analytics Pipeline

## 🥎 Project Overview
This project is a comprehensive **Modern Data Stack (MDS)** solution designed to scrape, transform, and visualize NCAA Softball performance data. It automates the extraction of full-season Play-by-Play (PBP) data from dozens of university athletics websites and tracks the 2024 Transfer Portal to provide a 360-degree view of opponent scouting and recruitment optimization.

The architecture is built for scalability and production readiness, transitioning from simple scripts to a fully orchestrated **ELT (Extract, Load, Transform)** pipeline.

---

## 🏗️ Architecture & Tech Stack

### Data Ingestion & Extraction
- **Python (BeautifulSoup4 & Requests)**: Used for custom scraping of Sidearm Sports athletics pages. Python was chosen for its flexibility in handling non-standardized DOM structures across different university websites.
- **Airbyte (Strategy)**: Employed for ingesting structured data from standard sports APIs and historical CSV repositories into the data warehouse.

### Storage (Data Warehouse)
- **Azure SQL Database / SQLite**: The project supports both local development (SQLite) and enterprise cloud deployment (Azure SQL). Azure SQL was chosen for its seamless integration with the Microsoft ecosystem and support for high-concurrency analytics.

### Transformation
- **dbt (Data Build Tool)**: Implements the **Transform** in ELT. Instead of complex Python cleaning scripts, we use modular SQL models to build analytical tables (e.g., calculating batting averages and spray charts) directly within the warehouse, ensuring data lineage and testing.

### Orchestration
- **Apache Airflow**: Orchestrates the entire pipeline. It manages task dependencies, retries, and scheduling (e.g., daily scraping during the season), providing a robust monitoring interface.

### Visualization
- **Streamlit**: A high-performance framework used to build the interactive analytics dashboard, allowing coaches and analysts to filter data by team and player in real-time.

### Infrastructure
- **Docker & Docker Compose**: Ensures environment consistency across development and production, encapsulating all services from Airflow to the Streamlit UI.

---

## 🛠️ The Pipeline Workflow

1.  **Extraction**: The Airflow DAG triggers custom Python scrapers to fetch the latest 2024 game data. It currently supports 25+ opponent teams, extracting over 140,000 unique plays.
2.  **Loading**: Raw PBP data and Transfer Portal entries are loaded into the **Staging Schema** of the Azure SQL Database.
3.  **Transformation (dbt)**:
    - **Staging**: Cleanse raw text, handle player name regex (e.g., normalizing "CHIPPS, A" and "A. Chipps").
    - **Marts**: Build the `fct_player_performance` table, calculating advanced metrics like BA, HR totals, and hit location frequency.
4.  **Analytics**: The Streamlit dashboard queries the **Marts layer** to generate:
    - **Batted Ball Heat Maps**: Visualizing spray patterns on a standardized softball field.
    - **Quick Stats**: Real-time performance metrics for opponent scouting.
    - **Portal Insights**: Tracking available talent and commitment trends.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Running the Full Stack
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/jimmywu0515-wq/ncaa_women_softball.git
    cd ncaa_women_softball
    ```
2.  **Set up environment variables**:
    Create a `.env` file with your `DATABASE_URL`.
3.  **Launch the services**:
    ```bash
    docker-compose up -d
    ```
4.  **Access the tools**:
    - **Dashboard**: `http://localhost:8501`
    - **Airflow UI**: `http://localhost:8080`

---

## 📈 Engineering Decisions & Rationale
- **Why ELT instead of ETL?** By loading raw data first, we retain the ability to re-transform data if our analysis requirements change without needing to re-scrape the sources.
- **Why dbt?** It brings software engineering best practices (version control, testing) to the SQL layer, which is critical when dealing with messy sports data.
- **Why Airflow?** In a production sports environment, data must be ready before morning practice. Airflow's scheduling and alerting ensure high data reliability.

---

## 🗺️ Future Roadmap
- [ ] **Automated Seasonal Trigger**: Implement dynamic scheduling to automatically detect and fetch data when a new NCAA season begins.
- [ ] **Expanded Multi-Sport Support**: Adapt the scraping logic for NCAA Baseball and other collegiate sports.
- [ ] **Advanced Analytics**: Integrate machine learning models for player performance prediction.

---
