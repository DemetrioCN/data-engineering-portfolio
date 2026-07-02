import logging
from contextlib import asynccontextmanager
from datetime import datetime

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException

from config import CACHE_DIR, INIT_DAY, INPUT_DIR, NUM_NEXT_EVENT, OUTPUT_DIR
from model import VisitEvent
from simulator import simulate_visit
from storage import load_cache, load_latest_csv, write_cache, write_events

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Global state ─────────────────────────────────────────────────────────────
scheduler       = AsyncIOScheduler()
last_run_events: list[dict] = []


# ─── Core logic ───────────────────────────────────────────────────────────────
def process_route(
    route_id: str,
    df: pd.DataFrame,
    cache: dict,
    process_date: datetime,
) -> tuple[list[VisitEvent], dict]:
    """
    Process the next N pending visits for a given route.

    Reads the current state from cache (last sequence and departure time),
    filters visits not yet processed, simulates each one in order,
    and returns the generated events along with the updated cache state.

    Returns an empty list and empty dict if no pending visits are found.
    """
    d_route = df[df["route_id"] == route_id].sort_values("sequence")

    if route_id in cache:
        cache_sequence, cache_last_time = cache[route_id]
    else:
        cache_sequence  = 0
        cache_last_time = datetime.combine(
            process_date.date(),
            datetime.strptime(INIT_DAY, "%H:%M:%S").time(),
        )

    df_next = d_route[d_route["sequence"] > cache_sequence].head(NUM_NEXT_EVENT)

    if df_next.empty:
        log.info("Route %s: no pending visits.", route_id)
        return [], {
            route_id: {
                "sequence":            cache_sequence,
                "last_departure_time": cache_last_time.isoformat(),
            }
        }

    events = []
    for _, row in df_next.iterrows():
        event, cache_last_time, cache_sequence = simulate_visit(row.to_dict(), cache_last_time)
        events.append(event)
        # cache_sequence is intentionally overwritten each iteration
        # only the last processed sequence is stored in cache

    log.info("Route %s: %d events simulated.", route_id, len(events))

    route_cache = {
        route_id: {
            "sequence":            cache_sequence,
            "last_departure_time": cache_last_time.isoformat(),
        }
    }
    return events, route_cache


def run_simulation() -> list[VisitEvent]:
    """
    Run the full simulation pipeline for all routes in the latest CSV.

    Loads and aggregates the CSV, reads the cache, processes each route,
    writes all generated events to a single JSON file, and updates the cache.
    A route failure is logged and skipped without stopping the other routes.

    Returns a list of all VisitEvent objects generated in this run.
    """
    df = load_latest_csv(INPUT_DIR)
    df = df.groupby("customer_id", as_index=False).agg({
        "date":           "first",
        "warehouse_code": "first",
        "order_id":       "first",
        "route_id":       "first",
        "sequence":       "first", # Assumes one sequence position per customer per route
        "quantity":       "sum",
    })
    df["date"] = pd.to_datetime(df["date"])

    process_date  = pd.to_datetime(df["date"].iloc[0])
    cache         = load_cache(CACHE_DIR, process_date)
    list_route_id = sorted(df["route_id"].unique())

    all_events  = []
    final_cache = {}

    for route_id in list_route_id:
        try:
            events, route_cache = process_route(route_id, df, cache, process_date)
            all_events.extend(events)
            final_cache.update(route_cache)
        except Exception as e:
            log.error("Route %s failed — skipping. Error: %s", route_id, e)

    write_events(all_events, OUTPUT_DIR, process_date)
    write_cache(CACHE_DIR, final_cache, process_date)

    log.info("Simulation done — %d events generated.", len(all_events))
    return all_events


# ─── Scheduler wrapper ────────────────────────────────────────────────────────
async def scheduled_run():
    """
    Async wrapper for run_simulation, called automatically by the scheduler.

    Updates the in-memory last_run_events so the GET /events endpoint
    reflects the most recent scheduled execution. Errors are logged
    without raising so the scheduler keeps running on the next interval.
    """
    global last_run_events
    try:
        events          = run_simulation()
        last_run_events = [e.model_dump(mode="json") for e in events]

        if len(events) == 0:
            log.info("All routes exhausted — stopping scheduler.")
            scheduler.remove_job("simulation_job")

    except Exception as e:
        log.error(f"Scheduled run failed: {e}")


# ─── Lifespan + App ───────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the server lifetime.

    Starts the APScheduler instance when the server boots and shuts it
    down cleanly when the server stops. Any scheduled jobs are cancelled
    automatically on shutdown.
    """
    scheduler.start()
    log.info("Scheduler started.")
    yield
    scheduler.shutdown()
    log.info("Scheduler stopped.")

app = FastAPI(
    title="Delivery Simulator API",
    description="Simulates delivery events from a visit list CSV.",
    lifespan=lifespan,
)


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/simulate/batch", response_model=list[VisitEvent])
def simulate_batch():
    """
    Trigger the full simulation immediately and return the generated events.

    Runs run_simulation(), updates last_run_events, and returns the events
    as JSON. Raises 404 if the input CSV is not found, 500 on any other error.
    """
    global last_run_events
    try:
        events          = run_simulation()
        last_run_events = [e.model_dump(mode="json") for e in events]
        return events
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error(f"Batch simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate/scheduler/start")
def start_scheduler(interval_minutes: int = 60):
    """
    Activate the scheduler to run the simulation every N minutes.

    Raises 400 if the scheduler is already running.
    The job runs with max_instances=1 to prevent overlapping executions.
    """
    if scheduler.get_job("simulation_job"):
        raise HTTPException(status_code=400, detail="Scheduler already running.")
    scheduler.add_job(
        scheduled_run,
        "interval",
        minutes=interval_minutes,
        id="simulation_job",
        max_instances=1,
    )
    log.info("Scheduler started — every %d min.", interval_minutes)
    return {"message": f"Scheduler running every {interval_minutes} minutes."}

@app.post("/simulate/scheduler/stop")
def stop_scheduler():
    """
    Stop the scheduler without shutting down the server.

    Raises 400 if the scheduler is not currently running.
    The server keeps running and can be restarted via /simulate/scheduler/start.
    """
    if not scheduler.get_job("simulation_job"):
        raise HTTPException(status_code=400, detail="Scheduler is not running.")
    scheduler.remove_job("simulation_job")
    log.info("Scheduler stopped.")
    return {"message": "Scheduler stopped."}

@app.get("/simulate/scheduler/status")
def scheduler_status():
    """
    Return the current scheduler state.

    Returns active=False and next_run=None if the scheduler is not running.
    Returns active=True and the next scheduled run time in ISO format if active.
    """
    job = scheduler.get_job("simulation_job")
    if not job:
        return {"active": False, "next_run": None}
    return {"active": True, "next_run": job.next_run_time.isoformat()}

@app.get("/events", response_model=list[VisitEvent])
def get_events():
    """
    Return the events generated in the most recent run.

    Reflects the last batch or scheduled execution, whichever ran last.
    Raises 404 if no simulation has been run since the server started.
    """
    if not last_run_events:
        raise HTTPException(status_code=404, detail="No events yet. Run /simulate/batch first.")
    return last_run_events