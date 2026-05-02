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
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #fff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .case-file-section {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        }
        
        .case-file-header {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }
        
        .case-file-header h2 {
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(45deg, #fff, #e0e0e0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .case-file-badge {
            margin-left: 20px;
            padding: 5px 12px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            letter-spacing: 1px;
        }
        
        .input-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .input-field {
            display: flex;
            flex-direction: column;
        }
        
        .field-label {
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: rgba(255, 255, 255, 0.95);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .field-label .field-icon {
            font-size: 1.1rem;
        }
        
        .field-label .field-purpose {
            font-size: 0.75rem;
            font-weight: 400;
            opacity: 0.7;
            margin-left: auto;
            font-style: italic;
        }
        
        .field-input {
            padding: 12px 15px;
            font-size: 15px;
            border: 2px solid rgba(255, 255, 255, 0.25);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.08);
            color: white;
            transition: all 0.3s ease;
            font-family: inherit;
        }
        
        .field-input:focus {
            outline: none;
            border-color: rgba(255, 255, 255, 0.5);
            background: rgba(255, 255, 255, 0.12);
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
        }
        
        .field-input::placeholder {
            color: rgba(255, 255, 255, 0.5);
            font-size: 14px;
        }
        
        textarea.field-input {
            min-height: 80px;
            resize: vertical;
        }
        
        .submit-section {
            display: flex;
            justify-content: center;
            padding-top: 10px;
        }
        
        .submit-btn {
            background: linear-gradient(45deg, #764ba2, #667eea);
            color: white;
            border: none;
            padding: 14px 50px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 10px 30px rgba(118, 75, 162, 0.4);
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(118, 75, 162, 0.5);
        }
        
        .submit-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .agents-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .agent-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            transition: transform 0.3s;
        }
        
        .agent-card.active {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        
        .agent-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .agent-avatar {
            font-size: 2.5rem;
            margin-right: 15px;
        }
        
        .agent-info h3 {
            font-size: 1.2rem;
            margin-bottom: 5px;
        }
        
        .agent-info p {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .agent-content {
            max-height: 300px;
            overflow-y: auto;
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            font-size: 0.9rem;
            line-height: 1.6;
        }
        
        .decision-section {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        .audit-section {
            background: rgba(0, 255, 100, 0.1);
            border: 2px solid rgba(0, 255, 100, 0.3);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        .audit-hash {
            font-family: monospace;
            font-size: 0.8rem;
            word-break: break-all;
            margin: 15px 0;
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 5px;
        }
        
        .mint-btn {
            background: linear-gradient(45deg, #00c853, #00e676);
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 16px;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .mint-btn:hover {
            transform: translateY(-2px);
        }
        
        .examples {
            margin-top: 20px;
        }
        
        .example-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 10px 15px;
            margin: 5px;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .example-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .loading {
            text-align: center;
            padding: 20px;
        }
        
        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top: 3px solid white;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ NEXUS</h1>
            <p>AI General Counsel for Business Compliance</p>
            <p style="font-size: 0.9rem; opacity: 0.7; margin-top: 5px;">Powered by SpoonOS Multi-Agent Framework</p>
        </div>
        
        <div class="case-file-section">
            <div class="case-file-header">
                <h2>📁 Case File Submission</h2>
                <span class="case-file-badge">CONFIDENTIAL</span>
            </div>

            <form id="caseForm">
            <div class="input-grid">
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">🎯</span>
                        The Core Objective
                        <span class="field-purpose">Primary goal</span>
                    </label>
                    <textarea 
                        id="objectiveInput" 
                        class="field-input" 
                        placeholder="e.g., Transporting 5,000 lbs of hemp biomass to a processing lab."
                        required
                    ></textarea>
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">📍</span>
                        Key Jurisdictions
                        <span class="field-purpose">Legal zones</span>
                    </label>
                    <input 
                        type="text"
                        id="jurisdictionsInput" 
                        class="field-input" 
                        placeholder="e.g., Origin: Oregon, Transit: Idaho, Dest: Florida"
                    />
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">⏱️</span>
                        Timeline & Constraints
                        <span class="field-purpose">Time pressures</span>
                    </label>
                    <input 
                        type="text"
                        id="timelineInput" 
                        class="field-input" 
                        placeholder="e.g., Must deliver in 10 days to get a $50k bonus."
                    />
                </div>
                
                <div class="input-field">
                    <label class="field-label">
                        <span class="field-icon">⚔️</span>
                        Conflict / Alternatives
                        <span class="field-purpose">Options & risks</span>
                    </label>
                    <textarea 
                        id="conflictInput" 
                        class="field-input" 
                        placeholder="e.g., Option A is fast but risky (through strict states). Option B is safe but we miss the deadline."
                    ></textarea>
                </div>
            </div>
            
            <div class="submit-section">
                <button id="submitBtn" class="submit-btn" type="submit">
                    <span>📊</span>
                    <span id="submitBtnLabel">Submit Case to Council</span>
                </button>
            </div>
            </form>
        </div>
        
        <div id="loadingSection" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p style="margin-top: 20px;">Council is deliberating...</p>
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
                    Awaiting query...
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
                    Awaiting query...
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
                    Awaiting query...
                </div>
            </div>
        </div>
        
        <div class="decision-section" id="decisionSection" style="display: none;">
            <h2 style="margin-bottom: 20px;">Council Decision</h2>
            <div id="decisionContent"></div>
        </div>
        
        <div class="audit-section" id="auditSection" style="display: none;">
            <h3>🔐 Audit Trail</h3>
            <p style="opacity: 0.8; margin: 10px 0;">Immutable record of council decision</p>
            <div class="audit-hash" id="auditHash"></div>
            <button class="mint-btn" onclick="mintAudit()">
                ⛓️ Mint to Blockchain
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
