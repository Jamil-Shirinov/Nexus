"""
FastAPI web application for Nexus AI Council
Provides REST API and web dashboard for compliance deliberation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime
import uuid

from nexus_council_standalone import NexusCouncil
from web3_audit import get_audit_trail


# Pydantic models for API
class CaseData(BaseModel):
    objective: str = ""
    jurisdictions: str = ""
    timeline: str = ""
    conflict: str = ""


class QueryRequest(BaseModel):
    query: Optional[str] = None
    include_audit: bool = False
    case_data: Optional[CaseData] = None


class DebateResponse(BaseModel):
    session_id: str
    query: str
    legal_analysis: Optional[str]
    tax_analysis: Optional[str]
    growth_analysis: Optional[str]
    debate_rounds: List[Dict[str, str]]
    final_decision: str
    consensus: bool
    dissents: List[str]
    debate_hash: Optional[str]
    audit_tx: Optional[Dict[str, Any]]


class AuditRequest(BaseModel):
    debate_hash: str
    session_id: Optional[str]


def build_structured_query(request: QueryRequest) -> str:
    """Normalize the case submission into a single query string for the council."""
    if request.case_data:
        case_data = request.case_data
        sections = []

        if case_data.objective.strip():
            sections.append(f"Objective: {case_data.objective.strip()}")
        if case_data.jurisdictions.strip():
            sections.append(f"Jurisdictions: {case_data.jurisdictions.strip()}")
        if case_data.timeline.strip():
            sections.append(f"Timeline: {case_data.timeline.strip()}")
        if case_data.conflict.strip():
            sections.append(f"Alternatives: {case_data.conflict.strip()}")

        if sections:
            return "\n".join(["Business compliance scenario:", *sections])

    if request.query and request.query.strip():
        return request.query.strip()

    raise HTTPException(status_code=422, detail="Please provide a case objective before submitting.")


# Initialize FastAPI app
app = FastAPI(
    title="Nexus AI Council",
    description="AI General Counsel for Business Compliance",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
council: Optional[NexusCouncil] = None
audit_trail = get_audit_trail()
sessions: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize council on startup"""
    global council
    print("🚀 Starting Nexus AI Council server...")
    council = NexusCouncil()
    print("✅ Server ready!")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web dashboard"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus AI Council</title>
    <style>
        :root {
            --sky-deep: #0f62ca;
            --sky-mid: #42acef;
            --sky-light: #e8fbff;
            --grass-bright: #9ee15b;
            --grass-deep: #59a834;
            --panel-border: rgba(255, 255, 255, 0.78);
            --panel-shadow: 0 28px 65px rgba(53, 130, 191, 0.18);
            --text-strong: #16507b;
            --text-soft: #4b7fa2;
            --text-light: #f4fdff;
            --highlight: rgba(255, 255, 255, 0.9);
            --field-text: #16354d;
            --field-placeholder: #38556c;
            --gloss-blue: linear-gradient(180deg, #f8feff 0%, #c5f0ff 30%, #5fc2f7 52%, #2d78d5 100%);
            --gloss-green: linear-gradient(180deg, #fbfff6 0%, #d7ffd4 32%, #7ae89e 55%, #39b861 100%);
            --liquid-field: linear-gradient(180deg, rgba(236, 246, 252, 0.98) 0%, rgba(219, 236, 246, 0.96) 34%, rgba(182, 218, 235, 0.88) 68%, rgba(210, 232, 243, 0.96) 100%);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            min-height: 100%;
        }

        body {
            font-family: 'Segoe UI', 'Trebuchet MS', Arial, Helvetica, sans-serif;
            background:
                radial-gradient(circle at 87% 10%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0) 10%),
                radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.42), rgba(255, 255, 255, 0) 12%),
                linear-gradient(180deg, #0f62ca 0%, #2d92e8 27%, #74d0ff 54%, #d6f7ff 76%, #f8fffb 100%);
            min-height: 100vh;
            color: var(--text-strong);
            padding: 28px 24px 96px;
            position: relative;
            overflow-x: hidden;
            text-rendering: optimizeLegibility;
        }

        body::before {
            content: '';
            position: fixed;
            inset: auto -8% 8% -8%;
            height: 24vh;
            background:
                radial-gradient(circle at 18% 62%, rgba(179, 245, 163, 0.82), rgba(179, 245, 163, 0) 22%),
                radial-gradient(circle at 55% 52%, rgba(145, 229, 107, 0.9), rgba(145, 229, 107, 0) 30%),
                radial-gradient(circle at 86% 60%, rgba(164, 240, 119, 0.86), rgba(164, 240, 119, 0) 20%),
                linear-gradient(180deg, rgba(175, 234, 103, 0.88) 0%, rgba(88, 168, 46, 0.96) 100%);
            border-radius: 50% 50% 0 0 / 100% 100% 0 0;
            filter: saturate(120%);
            z-index: 0;
        }

        body::after {
            content: '';
            position: fixed;
            left: 0;
            right: 0;
            bottom: 17vh;
            height: 72px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.68), rgba(255, 255, 255, 0) 68%);
            filter: blur(20px);
            opacity: 0.9;
            z-index: 0;
        }

        .aero-scene {
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
        }

        .sun-flare,
        .sun-glint,
        .sky-bubble,
        .horizon-line {
            position: absolute;
        }

        .sun-flare {
            top: 60px;
            right: 72px;
            width: 110px;
            height: 110px;
            border-radius: 50%;
            background:
                radial-gradient(circle, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.85) 26%, rgba(255, 255, 255, 0.08) 62%, rgba(255, 255, 255, 0) 74%);
            box-shadow:
                0 0 0 18px rgba(255, 255, 255, 0.08),
                0 0 36px rgba(255, 255, 255, 0.58),
                0 0 72px rgba(255, 255, 255, 0.45);
        }

        .sun-glint {
            top: 72px;
            right: 36px;
            width: 210px;
            height: 210px;
            background:
                radial-gradient(circle, rgba(255, 255, 255, 0.46), rgba(255, 255, 255, 0) 62%);
            filter: blur(6px);
        }

        .sky-bubble {
            border-radius: 50%;
            background:
                radial-gradient(circle at 32% 25%, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.12) 28%, rgba(255, 255, 255, 0.04) 48%, rgba(255, 255, 255, 0.22) 100%);
            border: 1px solid rgba(255, 255, 255, 0.54);
            box-shadow:
                inset 12px 16px 24px rgba(255, 255, 255, 0.45),
                inset -12px -18px 24px rgba(62, 135, 210, 0.18),
                0 16px 30px rgba(21, 107, 180, 0.16);
            opacity: 0.8;
        }

        .bubble-large {
            top: 138px;
            left: 58%;
            width: 120px;
            height: 120px;
        }

        .bubble-small {
            top: 408px;
            left: 18%;
            width: 74px;
            height: 74px;
            opacity: 0.55;
        }

        .horizon-line {
            left: 0;
            right: 0;
            bottom: 19vh;
            height: 36px;
            background:
                radial-gradient(circle at 5% 90%, rgba(78, 144, 44, 0.95), rgba(78, 144, 44, 0) 18px),
                radial-gradient(circle at 16% 88%, rgba(92, 151, 51, 0.98), rgba(92, 151, 51, 0) 16px),
                radial-gradient(circle at 28% 90%, rgba(78, 144, 44, 0.95), rgba(78, 144, 44, 0) 18px),
                radial-gradient(circle at 43% 90%, rgba(92, 151, 51, 0.98), rgba(92, 151, 51, 0) 16px),
                radial-gradient(circle at 58% 92%, rgba(78, 144, 44, 0.95), rgba(78, 144, 44, 0) 18px),
                radial-gradient(circle at 72% 90%, rgba(86, 149, 48, 0.96), rgba(86, 149, 48, 0) 20px),
                radial-gradient(circle at 86% 88%, rgba(78, 144, 44, 0.95), rgba(78, 144, 44, 0) 18px),
                linear-gradient(180deg, rgba(117, 183, 61, 0.18), rgba(57, 117, 28, 0.74));
            opacity: 0.8;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 48px;
            padding: 58px 0 38px;
        }

        .hero-kicker {
            font-size: 0.98rem;
            font-weight: 700;
            color: #113a5d;
            letter-spacing: 0.08em;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.92),
                0 0 14px rgba(255, 255, 255, 0.36),
                0 8px 18px rgba(9, 60, 117, 0.12);
            margin-bottom: 16px;
        }

        .header h1 {
            font-size: clamp(3rem, 6vw, 5rem);
            margin-bottom: 14px;
            font-weight: 700;
            color: #0f3252;
            letter-spacing: 0.04em;
            -webkit-text-stroke: 1px rgba(228, 246, 255, 0.74);
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.96),
                0 3px 0 rgba(210, 236, 255, 0.82),
                0 0 22px rgba(255, 255, 255, 0.34),
                0 16px 28px rgba(9, 73, 138, 0.18);
        }

        .header p {
            font-size: 1.2rem;
            opacity: 0.95;
        }

        .hero-subtitle,
        .hero-meta {
            max-width: 760px;
            margin: 0 auto;
            color: #1b4d75;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.94),
                0 0 12px rgba(255, 255, 255, 0.28),
                0 8px 18px rgba(8, 62, 120, 0.1);
        }

        .hero-subtitle {
            font-size: 1.22rem;
            line-height: 1.7;
            margin-bottom: 12px;
        }

        .hero-meta {
            font-size: 0.95rem;
            color: #2b628d;
            margin-bottom: 24px;
        }

        .hero-chips {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 12px;
        }

        .hero-chip {
            padding: 10px 16px;
            border-radius: 999px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(223, 248, 255, 0.34));
            border: 1px solid rgba(255, 255, 255, 0.82);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.96),
                0 12px 28px rgba(37, 104, 168, 0.12);
            font-size: 0.92rem;
            font-weight: 600;
            color: #19496e;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.94),
                0 0 8px rgba(255, 255, 255, 0.18);
        }

        .case-file-section,
        .agent-card,
        .decision-section,
        .audit-section,
        .loading-card {
            position: relative;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.4), rgba(225, 246, 255, 0.25) 52%, rgba(155, 215, 247, 0.18) 100%);
            backdrop-filter: blur(18px) saturate(145%);
            border: 1px solid var(--panel-border);
            box-shadow:
                var(--panel-shadow),
                inset 0 1px 0 rgba(255, 255, 255, 0.96),
                inset 0 -18px 30px rgba(112, 190, 237, 0.12);
        }

        .case-file-section::before,
        .agent-card::before,
        .decision-section::before,
        .audit-section::before,
        .loading-card::before {
            content: '';
            position: absolute;
            inset: 1px 1px auto 1px;
            height: 46%;
            border-radius: inherit;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(255, 255, 255, 0.08));
            pointer-events: none;
        }

        .case-file-section {
            border-radius: 34px;
            padding: 34px 34px 30px;
            margin-bottom: 36px;
        }

        .case-file-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 18px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(173, 228, 255, 0.55);
        }

        .case-file-header h2 {
            font-size: 2rem;
            font-weight: 600;
            color: #111111;
            text-shadow: none;
        }

        .case-file-badge {
            padding: 10px 16px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(223, 247, 255, 0.32));
            border: 1px solid rgba(255, 255, 255, 0.92);
            border-radius: 999px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.98);
            font-size: 0.92rem;
            font-weight: 700;
            color: #111111;
            letter-spacing: 0.04em;
            text-shadow: none;
        }

        .case-file-intro {
            font-size: 1.02rem;
            line-height: 1.7;
            color: #111111;
            text-shadow: none;
            margin-bottom: 24px;
        }

        .input-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin-bottom: 28px;
        }

        .input-field {
            display: flex;
            flex-direction: column;
        }

        .field-label {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: #255b86;
            display: flex;
            align-items: center;
            gap: 8px;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.92),
                0 0 10px rgba(255, 255, 255, 0.42);
        }

        .field-label .field-icon {
            font-size: 1.1rem;
        }

        .field-label .field-purpose {
            font-size: 0.78rem;
            font-weight: 400;
            color: rgba(54, 120, 160, 0.86);
            margin-left: auto;
            font-style: italic;
        }

        .field-input {
            padding: 16px 18px;
            font-size: 15px;
            line-height: 1.55;
            font-weight: 600;
            border: 1px solid rgba(176, 212, 232, 0.96);
            border-radius: 26px;
            background: var(--liquid-field);
            color: var(--field-text);
            caret-color: #0d4e7c;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
            font-family: inherit;
            box-shadow:
                inset 0 1px 0 rgba(248, 252, 255, 0.92),
                inset 0 -12px 20px rgba(91, 166, 223, 0.18),
                inset 0 10px 18px rgba(255, 255, 255, 0.18),
                0 18px 34px rgba(54, 125, 188, 0.14),
                0 0 0 3px rgba(202, 232, 247, 0.32);
        }

        .field-input:focus {
            outline: none;
            border-color: rgba(186, 239, 255, 0.98);
            transform: translateY(-1px);
            box-shadow:
                inset 0 2px 0 rgba(255, 255, 255, 1),
                inset 0 -16px 20px rgba(83, 165, 219, 0.18),
                0 22px 34px rgba(46, 124, 191, 0.18),
                0 0 0 5px rgba(143, 226, 255, 0.28),
                0 0 30px rgba(198, 244, 255, 0.42);
        }

        .field-input::placeholder {
            color: var(--field-placeholder);
            font-size: 14px;
            font-weight: 600;
            opacity: 1;
        }

        textarea.field-input {
            min-height: 114px;
            resize: vertical;
        }

        .submit-section {
            display: flex;
            justify-content: center;
            padding-top: 6px;
        }

        .submit-btn,
        .mint-btn {
            position: relative;
            overflow: hidden;
            color: #133754;
            border: 1px solid rgba(255, 255, 255, 0.98);
            padding: 16px 38px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 999px;
            cursor: pointer;
            transition: transform 0.28s ease, box-shadow 0.28s ease, opacity 0.28s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-family: inherit;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.96),
                0 0 10px rgba(255, 255, 255, 0.22);
            box-shadow:
                inset 0 2px 0 rgba(255, 255, 255, 0.96),
                inset 0 -18px 22px rgba(25, 89, 161, 0.26),
                0 20px 38px rgba(37, 107, 176, 0.25),
                0 0 0 4px rgba(255, 255, 255, 0.18);
        }

        .submit-btn::before,
        .mint-btn::before {
            content: '';
            position: absolute;
            inset: 2px 3px auto 3px;
            height: 54%;
            border-radius: 999px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.08));
            pointer-events: none;
        }

        .submit-btn {
            min-width: 280px;
            background: var(--gloss-blue);
        }

        .mint-btn {
            background: var(--gloss-green);
        }

        .submit-btn:hover,
        .mint-btn:hover {
            transform: translateY(-3px) scale(1.01);
            box-shadow:
                inset 0 2px 0 rgba(255, 255, 255, 0.96),
                inset 0 -18px 22px rgba(25, 89, 161, 0.26),
                0 26px 44px rgba(37, 107, 176, 0.3),
                0 0 0 5px rgba(255, 255, 255, 0.16);
        }

        .submit-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .agents-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 34px;
        }

        .agent-card {
            border-radius: 30px;
            padding: 24px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .agent-card:hover {
            transform: translateY(-4px);
            box-shadow:
                0 32px 70px rgba(53, 130, 191, 0.22),
                inset 0 1px 0 rgba(255, 255, 255, 0.96),
                inset 0 -18px 30px rgba(112, 190, 237, 0.12);
        }

        .agent-card.active {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-4px) scale(1.015); }
        }

        .agent-header {
            display: flex;
            align-items: center;
            margin-bottom: 16px;
        }

        .agent-avatar {
            font-size: 2.5rem;
            margin-right: 15px;
            filter: drop-shadow(0 6px 12px rgba(255, 255, 255, 0.28));
        }

        .agent-info h3 {
            font-size: 1.24rem;
            margin-bottom: 5px;
            color: #20597f;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.92),
                0 0 12px rgba(255, 255, 255, 0.34);
        }

        .agent-info p {
            font-size: 0.92rem;
            color: var(--text-soft);
        }

        .agent-content {
            max-height: 320px;
            overflow-y: auto;
            padding: 18px 18px 20px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(222, 248, 255, 0.62) 48%, rgba(194, 233, 248, 0.4) 100%);
            border: 1px solid rgba(255, 255, 255, 0.85);
            border-radius: 24px;
            box-shadow:
                inset 0 2px 0 rgba(255, 255, 255, 0.96),
                inset 0 -14px 22px rgba(108, 179, 224, 0.12),
                0 16px 28px rgba(56, 126, 191, 0.1);
            font-size: 0.95rem;
            line-height: 1.6;
            color: #275d82;
        }

        .agent-content strong,
        #decisionContent strong {
            color: #12558d;
        }

        .agent-content::-webkit-scrollbar {
            width: 10px;
        }

        .agent-content::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, rgba(121, 203, 243, 0.95), rgba(61, 132, 198, 0.9));
            border-radius: 999px;
            border: 2px solid rgba(255, 255, 255, 0.66);
        }

        .decision-section {
            border-radius: 34px;
            padding: 34px;
            margin-bottom: 34px;
            color: var(--text-strong);
        }

        .decision-section h2,
        .audit-section h3 {
            color: #26628b;
            text-shadow:
                0 1px 0 rgba(255, 255, 255, 0.95),
                0 0 16px rgba(255, 255, 255, 0.44);
        }

        #decisionContent {
            color: #25597e;
            line-height: 1.75;
        }

        .audit-section {
            border-radius: 30px;
            padding: 26px;
            text-align: center;
        }

        .audit-hash {
            font-family: monospace;
            font-size: 0.82rem;
            word-break: break-all;
            margin: 15px 0;
            padding: 14px 16px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(222, 247, 255, 0.62));
            border: 1px solid rgba(255, 255, 255, 0.92);
            border-radius: 22px;
            box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.98);
            color: #20648c;
        }

        .examples {
            margin-top: 20px;
        }

        .example-btn {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(223, 247, 255, 0.4));
            border: 1px solid rgba(255, 255, 255, 0.84);
            color: var(--text-strong);
            padding: 10px 16px;
            margin: 5px;
            border-radius: 999px;
            cursor: pointer;
            transition: transform 0.2s ease, background 0.2s ease;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.98);
        }

        .example-btn:hover {
            transform: translateY(-2px);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(215, 242, 255, 0.54));
        }

        .loading {
            text-align: center;
            padding: 6px 0 28px;
            margin-bottom: 18px;
        }

        .loading-card {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 24px 26px;
            border-radius: 28px;
        }

        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.46);
            border-top: 4px solid #2d7ed9;
            border-radius: 50%;
            width: 46px;
            height: 46px;
            animation: spin 0.95s linear infinite;
            box-shadow: 0 0 18px rgba(255, 255, 255, 0.3);
            margin: 0 auto 2px;
        }

        .loading-title {
            font-size: 1.08rem;
            font-weight: 600;
            color: var(--text-strong);
        }

        .loading-caption {
            font-size: 0.94rem;
            color: var(--text-soft);
            max-width: 380px;
            line-height: 1.6;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (max-width: 980px) {
            body {
                padding: 20px 16px 84px;
            }

            .input-grid {
                grid-template-columns: 1fr;
            }

            .case-file-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .header {
                padding-top: 38px;
            }

        .sun-flare,
        .sun-glint,
        .bubble-small {
            display: none;
        }
        }

        @media (max-width: 720px) {
            .container {
                max-width: 100%;
            }

            .agents-grid {
                grid-template-columns: 1fr;
            }

            .case-file-section,
            .decision-section,
            .audit-section,
            .agent-card {
                padding: 24px 20px;
            }

            .hero-subtitle {
                font-size: 1.06rem;
            }

            .submit-btn,
            .mint-btn {
                width: 100%;
            }

            .submit-section {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="aero-scene" aria-hidden="true">
        <div class="sun-flare"></div>
        <div class="sun-glint"></div>
        <div class="sky-bubble bubble-large"></div>
        <div class="sky-bubble bubble-small"></div>
        <div class="horizon-line"></div>
    </div>
    <div class="container">
        <div class="header">
            <p class="hero-kicker">Bright Compliance Guidance For Modern Teams</p>
            <h1>Nexus Council</h1>
            <p class="hero-subtitle">Clean technology, calm visuals, and clear legal tradeoffs for every case you submit.</p>
            <p class="hero-meta">Powered By SpoonOS Multi-Agent Framework</p>
            <div class="hero-chips">
                <span class="hero-chip">Clear Risk Signals</span>
                <span class="hero-chip">Friendly Liquid Controls</span>
                <span class="hero-chip">Nature And Tech Balance</span>
            </div>
        </div>
        
        <div class="case-file-section">
            <div class="case-file-header">
                <h2>📁 Case File Submission</h2>
                <span class="case-file-badge">Confidential</span>
            </div>
            <p class="case-file-intro">Frame the objective, map the jurisdictions, capture the timing pressure, and compare the paths so the council can return a bright, balanced recommendation.</p>

            <form id="caseForm">
            <div class="input-grid">
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">🎯</span>
                        Core Objective
                        <span class="field-purpose">Primary Goal</span>
                    </label>
                    <textarea 
                        id="objectiveInput" 
                        class="field-input" 
                        placeholder="Example: Transport 5,000 lbs of hemp biomass to a processing lab."
                        required
                    ></textarea>
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">📍</span>
                        Key Jurisdictions
                        <span class="field-purpose">Legal Zones</span>
                    </label>
                    <input 
                        type="text"
                        id="jurisdictionsInput" 
                        class="field-input" 
                        placeholder="Example: Origin Oregon, Transit Idaho, Destination Florida"
                    />
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">⏱️</span>
                        Timeline And Constraints
                        <span class="field-purpose">Time Pressure</span>
                    </label>
                    <input 
                        type="text"
                        id="timelineInput" 
                        class="field-input" 
                        placeholder="Example: Deliver within 10 days to secure a $50k bonus."
                    />
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">⚔️</span>
                        Conflict And Alternatives
                        <span class="field-purpose">Options And Risk</span>
                    </label>
                    <textarea 
                        id="conflictInput" 
                        class="field-input" 
                        placeholder="Example: Option A is faster but riskier. Option B is safer but misses the deadline."
                    ></textarea>
                </div>
            </div>
            
            <div class="submit-section">
                <button id="submitBtn" class="submit-btn" type="submit">
                    <span>📊</span>
                    <span id="submitBtnLabel">Submit Case To Council</span>
                </button>
            </div>
            </form>
        </div>
        
        <div id="loadingSection" class="loading" style="display: none;">
            <div class="loading-card">
                <div class="spinner"></div>
                <p class="loading-title">The council is weighing the case.</p>
                <p class="loading-caption">A bright summary with legal, tax, and growth viewpoints will appear in a moment.</p>
            </div>
        </div>
        
        <div class="agents-grid" id="agentsGrid">
            <div class="agent-card" id="legalCard">
                <div class="agent-header">
                    <div class="agent-avatar">⚖️</div>
                    <div class="agent-info">
                        <h3>Dr. Miranda Blackstone</h3>
                        <p>Legal Scholar</p>
                    </div>
                </div>
                <div class="agent-content" id="legalContent">
                    Ready for a new case.
                </div>
            </div>
            
            <div class="agent-card" id="taxCard">
                <div class="agent-header">
                    <div class="agent-avatar">💰</div>
                    <div class="agent-info">
                        <h3>Harold P. Pennywhistle</h3>
                        <p>Tax Comptroller</p>
                    </div>
                </div>
                <div class="agent-content" id="taxContent">
                    Ready for a new case.
                </div>
            </div>
            
            <div class="agent-card" id="growthCard">
                <div class="agent-header">
                    <div class="agent-avatar">🚀</div>
                    <div class="agent-info">
                        <h3>Blake Morrison</h3>
                        <p>Growth Hacker</p>
                    </div>
                </div>
                <div class="agent-content" id="growthContent">
                    Ready for a new case.
                </div>
            </div>
        </div>
        
        <div class="decision-section" id="decisionSection" style="display: none;">
            <h2 style="margin-bottom: 20px;">Council Guidance</h2>
            <div id="decisionContent"></div>
        </div>
        
        <div class="audit-section" id="auditSection" style="display: none;">
            <h3>🔐 Audit Trail</h3>
            <p style="opacity: 0.86; margin: 10px 0; color: var(--text-soft);">Record the council outcome when you are ready to preserve it.</p>
            <div class="audit-hash" id="auditHash"></div>
            <button class="mint-btn" onclick="mintAudit()">
                ⛓️ Record Audit Trail
            </button>
        </div>
    </div>
    
    <script>
        let currentSession = null;
        let currentHash = null;

        function buildStructuredQuery(caseData) {
            const sections = [];

            if (caseData.objective) {
                sections.push(`Objective: ${caseData.objective}`);
            }
            if (caseData.jurisdictions) {
                sections.push(`Jurisdictions: ${caseData.jurisdictions}`);
            }
            if (caseData.timeline) {
                sections.push(`Timeline: ${caseData.timeline}`);
            }
            if (caseData.conflict) {
                sections.push(`Alternatives: ${caseData.conflict}`);
            }

            return ['Business compliance scenario:', ...sections].join('\\n');
        }

        function setSubmitting(isSubmitting) {
            const submitBtn = document.getElementById('submitBtn');
            const submitBtnLabel = document.getElementById('submitBtnLabel');

            submitBtn.disabled = isSubmitting;
            submitBtn.setAttribute('aria-busy', isSubmitting ? 'true' : 'false');
            submitBtnLabel.textContent = isSubmitting
                ? 'Council Deliberating...'
                : 'Submit Case to Council';

            document.getElementById('loadingSection').style.display = isSubmitting ? 'block' : 'none';
            document.querySelectorAll('.agent-card').forEach(card => {
                card.classList.toggle('active', isSubmitting);
            });
        }

        function resetResults() {
            currentSession = null;
            currentHash = null;

            document.getElementById('legalContent').textContent = 'Council is reviewing the case...';
            document.getElementById('taxContent').textContent = 'Council is reviewing the case...';
            document.getElementById('growthContent').textContent = 'Council is reviewing the case...';
            document.getElementById('decisionContent').textContent = '';
            document.getElementById('auditHash').textContent = '';
            document.getElementById('decisionSection').style.display = 'none';
            document.getElementById('auditSection').style.display = 'none';
        }
        
        async function submitQuery(event) {
            if (event) {
                event.preventDefault();
            }

            // Get all 4 input field values
            const objective = document.getElementById('objectiveInput').value.trim();
            const jurisdictions = document.getElementById('jurisdictionsInput').value.trim();
            const timeline = document.getElementById('timelineInput').value.trim();
            const conflict = document.getElementById('conflictInput').value.trim();
            
            // Validate at least the core objective is provided
            if (!objective) {
                alert('Please provide at least the Core Objective for your case.');
                return;
            }
            
            const caseData = {
                objective,
                jurisdictions,
                timeline,
                conflict
            };

            resetResults();
            setSubmitting(true);
            
            try {
                const response = await fetch('/api/debate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: buildStructuredQuery(caseData),
                        include_audit: false,
                        case_data: caseData
                    })
                });
                
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.detail || `Request failed with status ${response.status}`);
                }

                currentSession = data.session_id;
                currentHash = data.debate_hash;
                
                // Update agent cards
                document.getElementById('legalContent').innerHTML = 
                    formatAgentResponse(data.legal_analysis || 'Processing...');
                document.getElementById('taxContent').innerHTML = 
                    formatAgentResponse(data.tax_analysis || 'Processing...');
                document.getElementById('growthContent').innerHTML = 
                    formatAgentResponse(data.growth_analysis || 'Processing...');
                
                // Show decision
                document.getElementById('decisionContent').innerHTML = 
                    formatDecision(data.final_decision);
                document.getElementById('decisionSection').style.display = 'block';
                
                // Show audit section
                if (data.debate_hash) {
                    document.getElementById('auditHash').textContent = data.debate_hash;
                    document.getElementById('auditSection').style.display = 'block';
                }

                document.getElementById('decisionSection').scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                setSubmitting(false);
            }
        }
        
        async function mintAudit() {
            if (!currentHash) {
                alert('No audit hash available');
                return;
            }
            
            try {
                const response = await fetch('/api/mint-audit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        debate_hash: currentHash,
                        session_id: currentSession 
                    })
                });
                
                const data = await response.json();
                alert(`✅ Audit minted!\\nTransaction: ${data.tx_hash}`);
                
            } catch (error) {
                alert('Error minting audit: ' + error.message);
            }
        }
        
        function formatAgentResponse(text) {
            if (!text) return 'Processing...';
            return text
                .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\n/g, '<br>')
                .replace(/•/g, '&bull;')
                .replace(/✅/g, '✅')
                .replace(/❌/g, '❌')
                .replace(/⚠️/g, '⚠️');
        }
        
        function formatDecision(text) {
            if (!text) return 'Processing decision...';
            return formatAgentResponse(text);
        }

        window.addEventListener('DOMContentLoaded', () => {
            document.getElementById('caseForm').addEventListener('submit', submitQuery);
        });
    </script>
</body>
</html>
"""


@app.post("/api/debate", response_model=DebateResponse)
async def run_debate(request: QueryRequest, background_tasks: BackgroundTasks):
    """Run council deliberation on query"""
    
    if not council:
        raise HTTPException(status_code=503, detail="Council not initialized")
    
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        normalized_query = build_structured_query(request)
        
        # Run deliberation
        result = await council.deliberate(normalized_query)
        
        # Store audit trail if requested
        audit_tx = None
        if request.include_audit and result.get("debate_hash"):
            audit_tx = await audit_trail.store_audit_on_chain(
                result["debate_hash"],
                metadata={"session_id": session_id, "query": normalized_query}
            )
        
        # Store session
        sessions[session_id] = {
            "result": result,
            "audit_tx": audit_tx,
            "timestamp": datetime.now().isoformat()
        }
        
        # Build response
        return DebateResponse(
            session_id=session_id,
            query=normalized_query,
            legal_analysis=result.get("legal_analysis"),
            tax_analysis=result.get("tax_analysis"),
            growth_analysis=result.get("growth_analysis"),
            debate_rounds=result.get("debate_rounds", []),
            final_decision=result.get("final_decision", ""),
            consensus=result.get("consensus", False),
            dissents=result.get("dissents", []),
            debate_hash=result.get("debate_hash"),
            audit_tx=audit_tx
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mint-audit")
async def mint_audit(request: AuditRequest):
    """Mint audit trail to blockchain"""
    
    try:
        # Store on blockchain
        tx_receipt = await audit_trail.store_audit_on_chain(
            request.debate_hash,
            metadata={"session_id": request.session_id}
        )
        
        return {
            "success": True,
            "tx_hash": tx_receipt.get("transactionHash"),
            "block_number": tx_receipt.get("blockNumber"),
            "message": "Audit trail successfully minted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify/{audit_hash}")
async def verify_audit(audit_hash: str):
    """Verify an audit hash on blockchain"""
    
    try:
        result = await audit_trail.verify_audit(audit_hash)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions():
    """List all deliberation sessions"""
    return {
        "sessions": [
            {
                "session_id": sid,
                "timestamp": data["timestamp"],
                "has_audit": data.get("audit_tx") is not None
            }
            for sid, data in sessions.items()
        ]
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get specific session details"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "council_ready": council is not None,
        "audit_mode": "mock" if audit_trail.mock_mode else "live"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
