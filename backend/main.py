import asyncio
import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from snapshot import build_history, build_snapshot

app = FastAPI()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STREAM_INTERVAL_SECONDS = 15
MAX_SYMBOLS = 20
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.=^\-]{1,15}$")  # Yahoo symbols, e.g. NQ=F, DX-Y.NYB, ^TNX


def parse_symbols(raw):
    symbols = list(dict.fromkeys(part.strip().upper() for part in raw.split(",") if part.strip()))
    if not symbols or len(symbols) > MAX_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Provide between 1 and {MAX_SYMBOLS} symbols")
    invalid = [symbol for symbol in symbols if not SYMBOL_PATTERN.match(symbol)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid symbols: {', '.join(invalid)}")
    return symbols


@app.get("/api/snapshot")
def get_snapshot(symbols: str = Query(...)):
    return build_snapshot(parse_symbols(symbols))


async def snapshot_events(symbols, is_disconnected):
    """Yields a Server-Sent Event with a fresh snapshot every STREAM_INTERVAL_SECONDS."""
    while not await is_disconnected():
        # Snapshot building is blocking (network + pandas), so keep it off the event loop
        snapshot = await run_in_threadpool(build_snapshot, symbols)
        yield f"data: {json.dumps(snapshot)}\n\n"
        await asyncio.sleep(STREAM_INTERVAL_SECONDS)


@app.get("/api/stream")
async def stream_snapshots(request: Request, symbols: str = Query(...)):
    events = snapshot_events(parse_symbols(symbols), request.is_disconnected)
    return StreamingResponse(events, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/history/{symbol}")
def get_history(symbol: str):
    return build_history(parse_symbols(symbol)[0])


# Mounted last so the API routes above take precedence; serves the dashboard at "/"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
