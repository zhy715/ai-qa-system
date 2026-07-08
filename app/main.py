from fastapi import FastAPI

app = FastAPI(title="AI知识库问答系统", version="0.1.0")


@app.get("/")
def root():
    return {"message": "AI知识库问答系统"}


@app.get("/health")
def health():
    return {"status": "ok"}
