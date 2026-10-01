from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.desk import router as desk_router
from app.models import Brief
from app.providers import SnapshotCaseProvider
from app.service import build_brief

load_dotenv()
BASE_DIR = Path(__file__).parent
app = FastAPI(title="Earnings Options Brief", version="0.2.0")
app.include_router(desk_router)
FRONTEND = BASE_DIR.parent / "frontend" / "dist"
if (FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
provider = SnapshotCaseProvider()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cases")
def cases() -> dict[str, list[str]]:
    return {"tickers": provider.available()}


@app.get("/api/brief/{ticker}", response_model=Brief)
def api_brief(ticker: str) -> Brief:
    try:
        return build_brief(provider.get(ticker))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/legacy", response_class=HTMLResponse)
def dashboard(request: Request, ticker: str = "ACME"):
    try:
        brief = build_brief(provider.get(ticker))
    except KeyError:
        brief = build_brief(provider.get("ACME"))
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"brief": brief, "tickers": provider.available()},
    )


@app.get("/")
def react_dashboard():
    if (FRONTEND / "index.html").exists():
        return FileResponse(FRONTEND / "index.html")
    return HTMLResponse(
        "<h1>Earnings Desk</h1><p>Build the interface: cd frontend &amp;&amp; npm ci &amp;&amp; npm run build.</p><a href='/docs'>API documentation</a>",
        status_code=503,
    )
