# CPG-LOGISTIC-DISTRIBUTION

## Overview
AI-Tacos is an emerging AI company based in Mexico. AI-Tacos sells profesional robots that prepare all kinds of tacos available across Mexico. The process is oil-free: you simply add the meat, corn for tortillas and vegetables, and the robot uses air-frying technology to produce delicious tacos.

After a period of rapid growth, AI-Tacos needed to build its data ecosystem from scratch. This project delivers that foundation: a centralized data platform on Azure + Databricks, real-time operational monitoring, executive KPI dashboards, and the analytical infrastructure needed to support a data science team.


## Bussines Requirements
AI-Tacos operates a B2B distribution model across multiple warehouses in Mexico.

The company recently equipped its fleet with two external data sources:
|System|Type|Description|
|--------|--------|--------|
|TrackTruck|Telemetry Platform + REST API|Provides real-time GPS location and truck event data|
|GPSVisit|Android App + REST API|Allows drivers to log completed client visits in the field|


#### Requirements
1. **Centralized Data Lake (Delta Lake)** <br>
Consolidate all data sources into a single, governed repository. The platform must be built on Azure and Databricks, as mandated by the company's technology stack decision.

2. **Real-Time Operational Monitoring**<br>
Build a web application that allows operations teams to track trucks and driver activity in near real-time, including visit logs captured through the GPSVisit mobile app.

3. **KPI Dashboard**<br>
In other application, deliver an executive dashboard tracking and visit.<br>
    - Completed service visits
    - Units sold (robots)
    - Revenue

4. **Advanced Analytics Layer**<br>
Support the company's newly hired data scientist by providing access to clean, curated, production-ready data. This includes surfacing operational patterns to support predictive and prescriptive analytics work.


