"""
AI-Assisted CC Prompt Builder — Phase 1 (MP40 / REQ-078)
Three endpoints: build, refine, finalize.
"""
import json
import secrets
import uuid
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.ai_provider import call_ai

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BuilderInput(BaseModel):
    input: str  # PL's raw stream-of-consciousness text


class QuestionItem(BaseModel):
    id: str
    question: str
    answer: str = ""
    required: bool = True


class BuilderResponse(BaseModel):
    session_id: str
    template_type: str
    questions: List[dict]
    prompt_draft: str


class RefineInput(BaseModel):
    session_id: str
    original_input: str
    template_type: str
    questions: List[dict]
    prompt_draft: str


class RefineResponse(BaseModel):
    questions: List[dict]
    prompt_draft: str


class FinalizeInput(BaseModel):
    session_id: str
    original_input: str
    template_type: str
    questions: List[dict]
    prompt_draft: str


class FinalizeResponse(BaseModel):
    prompt_final: str
    pth: str


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_BUILD = """You are a MetaPM sprint prompt architect for a software portfolio.
PL will give you rough input describing a task, bug, or feature.

Your job:
1. Identify which template type fits best:
   bug_fix | diagnosis | new_feature | sprint_scope |
   spec_readiness | architecture | governance | session_init

2. Fill in as much of the CC prompt structure as possible from PL's input.
   A CC prompt must contain: Bootstrap Gate reference, Phase 0 powershell block,
   Session Start Signal, Requirements section with acceptance criteria,
   Machine BVs (cc_machine assertions), pl_visual BVs for PL UAT,
   Handoff block, Session End Signal, Deliverable Report.

3. Apply 5Q analysis to find gaps:
   Q1: What does a browser user see/click/get? (one sentence)
   Q2: What would a curl test assert -- exact field, exact value?
   Q3: Exact input to exact output?
   Q4: What will CC most likely implement only partially?
   Q4A: What exact observable state proves it is complete?
   Q4B: Every boundary -- every element, page, condition this must hold?
   Q4C: What must NOT be true if correctly implemented?
   Q4D (frontend): Full chain: action, handler, API call, DB write, result?

4. Return a JSON object with these exact keys:
   {
     "template_type": "...",
     "questions": [
       {"id": "q1", "question": "...", "answer": "", "required": true},
       ...
     ],
     "prompt_draft": "... full markdown CC prompt ..."
   }

Ask 3-7 targeted questions. Each question targets a specific gap in the spec.
Label each with which 5Q category it addresses (Q1-Q4D).
Return ONLY valid JSON. No preamble, no explanation outside the JSON."""

SYSTEM_PROMPT_REFINE = """You are a MetaPM sprint prompt architect for a software portfolio.
PL has answered some of the follow-up questions you asked.

Your job:
1. Incorporate the answered questions into the prompt draft — update the
   relevant sections (requirements, BVs, acceptance criteria, etc.).
2. Remove questions that are fully addressed by PL's answers.
3. Add new questions ONLY if a PL answer reveals a new gap.
4. Return the same JSON structure:
   {
     "questions": [
       {"id": "q1", "question": "...", "answer": "...", "required": true},
       ...
     ],
     "prompt_draft": "... updated full markdown CC prompt ..."
   }

Return ONLY valid JSON. No preamble, no explanation outside the JSON."""

SYSTEM_PROMPT_FINALIZE = """You are a MetaPM sprint prompt architect for a software portfolio.
PL has answered all questions. Produce the FINAL polished CC prompt.

Polish the draft into a production-ready CC sprint prompt:
- Ensure all PL answers are incorporated.
- All sections present: Bootstrap Gate, Phase 0, Session Start Signal,
  Requirements with acceptance criteria, Machine BVs, pl_visual BVs,
  Handoff block, Session End Signal, Deliverable Report.
- Clean formatting, consistent markdown.
- Remove any placeholders or TODOs that PL answers resolve.

Return ONLY the final prompt markdown. No JSON wrapper. No preamble."""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/prompt-builder", response_model=BuilderResponse)
async def build_prompt(body: BuilderInput):
    """Take PL's raw input, return template type, questions, and prompt draft."""
    logger.info(f"[PromptBuilder] build called, input length={len(body.input)}")

    raw = await call_ai(SYSTEM_PROMPT_BUILD, body.input)

    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"[PromptBuilder] AI returned invalid JSON: {exc}\n{text[:500]}")
        raise HTTPException(status_code=502, detail="AI returned invalid JSON")

    session_id = str(uuid.uuid4())
    return BuilderResponse(
        session_id=session_id,
        template_type=parsed.get("template_type", "unknown"),
        questions=parsed.get("questions", []),
        prompt_draft=parsed.get("prompt_draft", ""),
    )


@router.post("/prompt-builder/refine", response_model=RefineResponse)
async def refine_prompt(body: RefineInput):
    """Take session state with PL answers, return updated questions + draft."""
    answered = sum(1 for q in body.questions if q.get("answer", "").strip())
    logger.info(f"[PromptBuilder] refine called, session={body.session_id}, answered={answered}")

    user_message = json.dumps({
        "original_input": body.original_input,
        "template_type": body.template_type,
        "questions": body.questions,
        "current_draft": body.prompt_draft,
    })

    raw = await call_ai(SYSTEM_PROMPT_REFINE, user_message)

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"[PromptBuilder] AI refine returned invalid JSON: {exc}\n{text[:500]}")
        raise HTTPException(status_code=502, detail="AI returned invalid JSON on refine")

    return RefineResponse(
        questions=parsed.get("questions", body.questions),
        prompt_draft=parsed.get("prompt_draft", body.prompt_draft),
    )


@router.post("/prompt-builder/finalize", response_model=FinalizeResponse)
async def finalize_prompt(body: FinalizeInput):
    """Validate all required answers are filled, return final prompt + PTH."""
    logger.info(f"[PromptBuilder] finalize called, session={body.session_id}")

    # Validation gate
    unanswered = [
        q.get("id", "?")
        for q in body.questions
        if q.get("required", True) and not q.get("answer", "").strip()
    ]
    if unanswered:
        raise HTTPException(
            status_code=400,
            detail={"error": "unanswered_required", "question_ids": unanswered},
        )

    user_message = json.dumps({
        "original_input": body.original_input,
        "template_type": body.template_type,
        "questions": body.questions,
        "current_draft": body.prompt_draft,
    })

    final_prompt = await call_ai(SYSTEM_PROMPT_FINALIZE, user_message)

    pth = "".join(secrets.choice("0123456789ABCDEF") for _ in range(4))
    logger.info(f"[PromptBuilder] finalize complete, PTH={pth}")

    return FinalizeResponse(prompt_final=final_prompt, pth=pth)
