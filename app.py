from fastapi import FastAPI

app = FastAPI()


# endpoint to check the health of the application
@app.get("/health")
def health_check():
    return {"status": "ok"}


# endpoint to get application info
@app.get("/info")
def app_info():
    return {
        "app": "Stock Portfolio Manager",
        "version": "1.0.0",
        "description": "An application to manage and analyze stock portfolios."
    }

# main endpoint that frontend interacts with
@app.get("/portfolio")
def get_portfolio():
    return {"message": "Portfolio data will be here."}

