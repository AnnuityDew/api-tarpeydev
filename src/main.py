# import native Python packages
import multiprocessing

# import third party packages
from fastapi import FastAPI, Request, Depends
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# import custom local stuff
from instance.config import GCP_FILE
from src.api.index import index_api
from src.api.autobracket import ab_api
from src.api.haveyouseenx import hysx_api
from src.api.mildredleague import ml_api
from src.db.startup import motor_startup, motor_shutdown
from src.api.security import get_api_key

# GCP debugger
try:
    import googleclouddebugger
    googleclouddebugger.enable(
        breakpoint_enable_canary=False,
        service_account_json_file=GCP_FILE,
    )
except ImportError:
    pass


def multiproc_context():
    # possible multiprocessing solution from https://github.com/tiangolo/fastapi/issues/1487
    # this prevents gunicorn workers from crashing on multiprocessing!
    multiprocessing.set_start_method('spawn')


def create_fastapi_app():
    api_app = FastAPI(
        title="tarpey.dev API",
        description="API for Mike Tarpey's app sandbox.",
        servers=[
            {"url": "https://api.tarpey.dev/", "description": "Production environment"},
            {"url": "https://dev-api.tarpey.dev/", "description": "Staging environment."},
            {"url": "http://127.0.0.1:8000/", "description": "Testing environment."},
        ],
        redoc_url=None,
        default_response_class=ORJSONResponse,
    )

    # CORS middleware to enable preflight OPTIONS requests
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # templates for the root page
    templates = Jinja2Templates(directory='templates')

    # root path
    @api_app.get('/')
    async def api_portal(request: Request):
        return templates.TemplateResponse(
            'api-portal.html',
            context={
                'request': request,
            }
        )

    @api_app.get('/all-paths', dependencies=[Depends(get_api_key)])
    async def all_paths():
        """View all active paths. Thanks JPG!

        https://stackoverflow.com/questions/63206332/how-can-i-list-all-defined-url-paths-in-fastapi
        
        """
        url_list = [
            {'path': route.path, 'name': route.name}
            for route in app.routes
        ]
        return url_list

    # static folder config
    api_app.mount("/static", app=StaticFiles(directory='static'), name="static")

    # startup and shutdown connection to DB
    # see https://motor.readthedocs.io/en/stable/tutorial-asyncio.html
    api_app.add_event_handler('startup', motor_startup)
    api_app.add_event_handler('shutdown', motor_shutdown)
    # multiprocessing context change that we're no longer using
    # api_app.add_event_handler('startup', multiproc_context)

    # include subrouters of the FastAPI app
    api_app.include_router(index_api)
    api_app.include_router(ab_api)
    api_app.include_router(hysx_api)
    api_app.include_router(ml_api)

    return api_app


# entrypoint!
app = create_fastapi_app()
