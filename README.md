# ftrack_service

Custom ftrack services for automatic review-media generation.

When an image sequence get int to the specific location, this service picks it up, converts it
to an MP4 (with OCIO colour management and a burned-in frame counter) and uploads the
result back to the ftrack version as review media.

The system can be notified with two ways - either webhook on ftrack site or catchng an special event from ftrack event hub. Webhook is more prefered, but if your organization does not allow to expose any endpoints to the internet - the only option is catching an event.

When event occures catcher gets id of new image sequence and send it to fastAPI service script. the script writes this id to the end of queue in SQLite database. Then it launches encodeq.py script that reads from queue and converts sequences to movies/previews and publishes it along with other version components
## How it works


1. `apps/location_event.py` listens on the ftrack event hub for
   `ftrack.location.component-added`. If the new component is a *sequence* published
   into the `x.local` location, it POSTs the component id to the API.
2. `main.py` (FastAPI) receives it on `/encode` (or `/addq`) and inserts the component
   id into the `queue` table of `db/queue.db` as a background task. It then checks
   with `psutil` whether an `apps.encodeq` worker is already running and starts one if
   not.
3. `apps/encodeq.py` drains the queue one row at a time. For each component it:
   - resolves the on-disk sequence path from the ftrack location,
   - reads project `fps` from the project custom attributes and builds a start timecode,
   - for EXR input, runs `oiiotool` with `ocio/config.ocio` to convert to
     `Output - sRGB` PNGs,
   - runs `ffmpeg` (libx264, yuv420p, crf 18) with a `drawtext` frame-number overlay,
   - calls `version.encode_media()` so ftrack ingests the MP4 as review media,
   - deletes the row and moves on. The loop exits when the queue is empty.

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | FastAPI/uvicorn service: `/encode`, `/addq`, `/ping` |
| `apps/location_event.py` | ftrack event-hub listener, triggers encodes |
| `apps/encodeq.py` | Queue worker: OCIO convert + ffmpeg encode + upload |
| `apps/ftr_checker.py` | Helper that prints all ftrack location names/ids |
| `db/` | SQLite queue database (`queue` table: `id`, `component_id`) |
| `ocio/` | OCIO configs (`config.ocio`, `cg.ocio`) and LUTs |

FastAPI's docs/redoc/openapi endpoints are disabled deliberately.

## Requirements

- Python >= 3.13, managed with [uv](https://github.com/astral-sh/uv)
- `oiiotool` (OpenImageIO) and `ffmpeg` on `PATH`
- Access to the media root (`/nas/data/proj/`) and to the ftrack server

Dependencies: `fastapi`, `uvicorn`, `ftrack-python-api`, `clique`, `psutil`, `dotenv`.

## Configuration

Credentials are read from `apps/.env` (git-ignored):

```
FTRACK_SERVER_URL=https://your-instance.ftrackapp.com
FTRACK_API_KEY=...
FTRACK_API_USER=...
```

## Running

```bash
uv sync

# API - since it runs inside your network --host 0.0.0.0 is ok. but you can
# restrict api calls from specific host specifying its ip or use 127.0.0.1 if  
# event listener runs on the same machine 
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# event listener - if you are not able to expose endpoint for ftrack webhooks 
uv run python -m apps.location_event

