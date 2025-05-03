from fastapi import FastAPI
from api import users, requests_routes, items, auth, support, hse_auth


app = FastAPI(
    title="SmartLocker API",
    description="API для мобильного приложения бронирования и выдачи оборудования",
    version="1.0.0"
)

app.include_router(users.router)
app.include_router(requests_routes.router)
app.include_router(items.router)
app.include_router(auth.router)
app.include_router(support.router)
app.include_router(hse_auth.router)