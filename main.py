"""
Giraffe Agent helper entry point.

The FastAPI application entry point is:
    api.main:app

Run the API server with:
    uv run uvicorn api.main:app --reload

Interactive API docs will be available at:
    http://localhost:8000/docs
"""


def main() -> None:
    print("Giraffe Agent")
    print("FastAPI entry point: api.main:app")
    print("Run: uv run uvicorn api.main:app --reload")
    print("Docs: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
