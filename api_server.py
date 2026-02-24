from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main_pipeline import diagnose

app = FastAPI()

# Allow React frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DiagnoseRequest(BaseModel):
    symptoms: list[str]

@app.post("/diagnose")
def run_diagnosis(req: DiagnoseRequest):

    result = diagnose(req.symptoms)

    return result
from tree_of_thoughts import get_tot

class UpdateRequest(BaseModel):
    tree: list
    answers: dict

@app.post("/update_tree")
def update_tree(req: UpdateRequest):

    tot = get_tot()

    updated_tree = tot.update_tree_with_answers(req.tree, req.answers)

    final = tot.get_final_diagnosis(updated_tree)

    return {
        "tree": updated_tree,
        "final": final
    }