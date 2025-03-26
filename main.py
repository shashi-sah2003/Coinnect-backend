from fastapi import FastAPI
from src.payman.paymanRouter import router as paymanai_router
import uvicorn

app = FastAPI()

app.include_router(paymanai_router)

@app.get("/")
async def main():
    return {"Hello from coinnect-backend!"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000, reload=True)
