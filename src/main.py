# import native Python packages
import multiprocessing

# import third party packages
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

# import custom local stuff
from instance.config import GCP_FILE
from src.api.index import index_api
from src.api.autobracket import ab_api
from src.api.haveyouseenx import hysx_api
from src.api.mildredleague import ml_api
from src.api.users import users_api
from src.db.startup import motor_startup, motor_shutdown

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
            {"url": "http://127.0.0.1:8000/", "description": "Testing environment."},
            {"url": "https://dev-api.tarpey.dev/", "description": "Staging environment."},
            {"url": "https://api.tarpey.dev/", "description": "Production environment"},
        ],
        default_response_class=ORJSONResponse,
    )

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
    api_app.include_router(users_api)

    return api_app


# entrypoint!
app = create_fastapi_app()
