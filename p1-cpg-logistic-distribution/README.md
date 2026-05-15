# Project 1 - CPG-LOGISTIC-DISTRIBUTION


## I. Bussines Requirements

AI-Tacos is an emerging AI company based in Mexico. AI-Tacos sells profesional robots that prepare all kinds of tacos available across Mexico. The process is oil-free: you simply add the meat, corn for tortillas and vegetables, and the robot uses air-frying technology to produce delicious tacos. 
Recently, the company has experienced rapid growth, making it neccesary to monitor the distribution process, define key KPIs, apply machine learning to optimize operations. 
Since AI-Tacos is a young company, they have never built a data ecosystem and now they are ready to start. 

AI-Tacos operates three warehouse distributed across Mexico: CED001 in Queretaro, CED002 in Chihuahua and CED003 in Oaxaca. Since the bussines model is B2B, robots are distributed to clients of diferent sizes, medium and large businesses mainly. 

Distribution is handled using straight trucks with capacity of 6 metric tons (6,000 kg). Each robot package weights 80 kg. Due to Mexican road regulations, trucks may only be loaded up to 80% of their total capacity, resulting in a usable load of 4,800 kg which allows for a maximum of 60 robots per truck. 

AI-Tacos recently purchased telemetric devices that provide real time information about GPS location and truck events. All data is available through the **TrackTruck** service platform and its API. 
AI-Tacos also uses a visit tracking service called **GPSVisit**, a mobile Android application that allows drivers to log completed visits. Similar to TrackTruck, GPSVisit also exposes an API for data access.

In this way, the bussinmes requirements are: 

1. **Real-Time Operation Monitoring** AI-Tacos wants to build a web application to monitor trucks in near real time, including the ability to track and identify visits logged through the GPSVisit mobile application.
2. **KPI Dashboard** They also want a dashboard to monitor key business KPIs in the same web application, including: service visits completed, truck capacity utilization, number of robots sold and revenue. Additionally, users must be able to export and download the reports in Excel format. 
3. **Advanced Analytics** AI-Tacos recently hired a data scientist and wants to support advanced analytics work, including identifying operational patterns. To enable this, the data scientist will need access to clean, final-state data. 


## II. Stakeholder requirements

### Upstream stakeholders
Our upstream stakeholders are our data provider. We have identified three sources:

1. **Technical lead - AI Tacos** - During discovery conversations, the technical lead confirmed that current data is stored in Excel files, including visit lists, orders, truck records, catalogs, and inventory. This indicates that the project has a significant digital transformation component, as structured data pipeline do not yet exist. 
    
    As a first step, it will be necessary to define a file transfer mechanism so that AI-Tacos can realiably share data with the engineering team (e.g., SFTP, shared cloud storage, or email ingestion).

2. **TrackTruck provider** - The technical documentation confirms that both the GPS position API and the telemetry events API are built on the REST API standard. Access is read-only (GET requests only). Both APIs operate in real time, with updates delivered in miliseconds.
    **Constraints:** 
    - Autehtication: Bearer Token + API key. Token expires every 3,600 seconds (1 hour) and must be refreshed via POST/auth/token before expiration.
    - Rate limit: 10,000 requests/hour per account, the estimated volume is ~18,000 requests/hour - this exceeds the rate limit and requires a polling strategy adjustment (e.g, every 20 seconds per truck = ~9,000 requests/hour)
    - Historical data retention: 90 days. A back fill job must be executed at project kickoff to load historical data into the data warehouse before the pipeline goes live. 
    - Response format: JSON. All timestamps are returned in ISO 8601 format (UTC).
    - Max page size: 500 records per request. Pagination is required for hsitorical queries. 
    - Data availability: Real-time position and telemery events are available within milliseconds of occurrende.
    - Enviroments: Two enviroments are available - Sandbox and Production.


3. **GPSVisit** - The technical documentation confirms that GPSVisit operates via a Webhook (push) nodel. Visit events are registered in real time at the moment the driver logs the visit from the Android application. Access is read-only (GET requests only). The platform pushes the event payload to a configured callback URL immediately upon registration.
    **Constraints:** 
    - Autehtication: API key sent as a request header (X-Api-Key). No token expiration - key must be rotated manually every 90 day as a security best practice.
    - Webhook retry policy: GPSVisit retries failed deliveries up too 3 times, with a 30 second interval between attempts. If all retries fail, the event is dropped on the provider side.
    - Payload size limit: 1 MB per event. Visit payloads are well within this limit under normal conditions.
    - Guaranteed delivery: GPSVisit does not guarantee exactly onde delivery. Duplicate events may occur on retries idempotency must be enforced using 'visit_id' as the unique key.
    - Response requirement: The receiver endpoint must respond with HTTP 200 within 5 seconds, otherwise GPSVisit considers the delivery failed and triggers a retry.
    - Enviroments: Two enviroments available, Sandbox and Production.


### Downstream stakeholders
Downstream stakeholders are the final users who will consume the data products generated by this project. Understanding their needs is essentials to ensure the pipeline delivers the right data, at the right time, in the right format.

1. **Dashboard users** - Managers and operations analysist at AI-Tacos who need visibility into business performance. They will consume the KPI dashboard to monitor key metrics such as service visits completed, truck capacity utilization, number of robots sold, and revenue. They require accurate, up-to-date data with the ability to export reports in Excel format for further analysis.

2. **Monitoring users** - Fleet supervisors responsible for overseeing day-to-day distribution operations. They will use the real-time web application to track truck locations, monitor telemetry events (such as harsh braking or speeding), and identify visit status as logged by drivers through GPSVisit.

3. **Data Scientist** - A recently hired data scientist who will perform advanced analytics to identify operational patterns and support machine learning initiatives. They require access to clean, final-state data in a format suitable for exploration and modeling. 


## III. System requirements

### Functional requirements
#### FR-1: Real-time fleet monitoring (Web Application)
- The system must ingest GPS position and telemetry events from TrackTruck in real time, polling every 20 seconds per truck.
- The system must display the current location of all active trucks on an interative map, updated continuosly.
- The system must detect and display telemetry alerts (e.g., harsh braking, speeding, engine overheat) as they occur.
- They system must receive and process visit events pushed by GPSVisit via webhook and display visit status (commpleted, discarded) on the map in real time.
- The system must display the discard reason for any visit logged as discarded.

#### FR-2: KPI Dashboard
- The system must calculate and display the following KPIs:
    - Service visits completed vs planned
    - Truck capacity utilization
    - Number of robots sold per period
    - Revenue per period
    - Market time
- The system must allow users to filter KPIs by date range, warehouse and truck.
- The system must allow users to export any KPI report as an Excel.
- The system must refresh KPI data everyday before 8:00 AM.


#### FR-3: Advanced Analytics Data Access
- The system must store clean, final-state data.
- The system must execute a backfill job at project kickoff to load 90 days of historical data from TrackTruck into the data warehouse.
- The system must update the curated data layer on a daily schedule, making it available to the data scientist by 7:00 PM each day (Monday through Saturday).

### Non-functional requirements

#### NFR-1: Performance (SLAs)
- Real-time truck positions must be updated on the web application within 5 seconds of the poling cycle completing. 
- Telemetry alerts must appear on the web application within 10 seconds of the event ocurring on the truck.
- GPSVisit webhook receiver must respond with HTTP 200 within 5 seconds to prevent retries
- KPI Dashboard must load within 3 seconds under normal conditions.
- Excel export must complete within 10 seconds for any date range up to 90 days.

#### NFR-2: Reliability
- The pipeline must achieve 99.5% uptime during operating hours (Mondat-Saturday, 6:00 AM - 10:00 PM).
- The system must ensuring zero data loss.
- The system must handle TrackTruck API unavailable gracefully, the web application must display the last know position rather than an error.
- All failed pipeline jobs must trigger an alert to the engineering team within 5 minutes of failure.

#### NFR-3: Scalability
- The polling architecture must support fleets growth from 50 to 200 trucks without requiring limit of 10,000 requests/hour.
- The data warehouse shcema must support at leats 2 years of historical data without performance degregation.
- The data warehouse shcema must support at leats 2 years of historical data without performance degradation.

#### NFR-4: Security & Access Control
- The web application is accesible only to executive and fleet supervisors.
- The data scientist is granted read-only access to the curated data. 
- All API keys never be harcoded or exposed in source code. 
- All data in transit must be encrypted using TLS 1.2 or higher.

#### NFR-5: Data Quality
- Any record missing require fields must be routed to a quarantine tabkle for manual review rather than silently dropped.


#### NFR-6: Disaster Recovery & Rollback
- The system must define a **Recovery Time Objective (RTO) of 
  2 hours** — meaning that in the event of a failure, the pipeline 
  and its dependent applications must be fully restored within 
  2 hours.
- The system must define a **Recovery Point Objective (RPO) of 
  1 hour** — meaning that in the event of data loss, no more than 
  1 hour of data may be unrecoverable.
- All pipeline infrastructure must be defined as **Infrastructure 
  as Code (IaC)**, enabling full environment reconstruction from 
  scratch in a reproducible and auditable manner.
- Automated snapshots and backups must be configured for all 
  stateful components (data warehouse, message queues, and object 
  storage), with a minimum retention period of **30 days**.
- The system must support **rollback** to a previous stable state 
  in the event of a failed deployment or data corruption, without 
  requiring manual data reconstruction.
- A disaster recovery plan must be documented and reviewed before 
  the system goes live in production.

#### NFR-7: Data Governance
- All datasets produced by the pipeline must be registered in a 
  **data catalog**, including dataset name, source system, update 
  frequency, owner, and a description of its contents. This ensures 
  that all stakeholders — including the data scientist — can 
  discover and understand available data without requiring 
  engineering assistance.
- The system must maintain **data lineage** for all datasets, 
  documenting the full path a record travels from its source system 
  (TrackTruck or GPSVisit) through ingestion, transformation, and 
  final storage. This enables root cause analysis when data 
  quality issues are detected.
- All datasets must have a defined and documented **data owner** 
  responsible for validating quality, approving schema changes, 
  and resolving data issues.
- Any schema change to a dataset consumed by downstream 
  stakeholders (dashboard users, monitoring users, or the data 
  scientist) must follow a **change management process** — 
  communicated in advance and versioned to prevent breaking 
  downstream dependencies.
- Personal or sensitive data, if present, must be identified and 
  classified during the data catalog registration process, and 
  handled in accordance with applicable data privacy regulations.

## IV. Data Sources Specification

## V. Businnes rules

## VI. Product Requirements Document

