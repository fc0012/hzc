from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.service import monitor

app = FastAPI(title="Hetzner Traffic Guard")
app.mount('/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')

scheduler = AsyncIOScheduler(timezone=settings.timezone)


@app.on_event('startup')
async def startup_event():
    if settings.hetzner_token:
        scheduler.add_job(monitor.rotate_if_needed, 'interval', minutes=settings.check_interval_minutes, id='check-traffic', replace_existing=True)
        scheduler.start()


@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.get('/api/servers')
async def servers():
    if not settings.hetzner_token:
        raise HTTPException(status_code=500, detail='HETZNER_TOKEN missing')
    return await monitor.collect()


@app.post('/api/rotate/{server_id}')
async def rotate(server_id: int):
    if not settings.hetzner_token:
        raise HTTPException(status_code=500, detail='HETZNER_TOKEN missing')
    return await monitor.rotate_server(server_id)
