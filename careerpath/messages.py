"""User-facing wording: fallback, privacy notice, suggested prompts.

Owner: Sisindri Rachakonda (interface, usability, wording). Keeping all copy in one file lets
usability feedback change wording without touching logic.
"""

SUGGESTED_QUESTIONS = [
    "How do I prepare for a behavioral interview?",
    "How can I improve my résumé if I have little experience?",
    "I'm looking for software engineer jobs in Plano. Where do I start?",
    "How do I ask someone for an informational interview?",
    "Which skills should I learn to move into data analysis?",
    "How do I explain a career change to an employer?",
    "Tailor my résumé to this job.",
]

SUPPORTED_TOPICS = [
    "Résumé improvement",
    "Interview preparation",
    "Job search planning",
    "Networking",
    "Skill development",
    "Career transitions",
    "ATS formatting",
]

PRIVACY_NOTICE = (
    "**Privacy notice.** If you upload a résumé, its text (with your name, email, phone and links "
    "replaced by placeholders) is sent to the selected model provider "
    "so the model can analyse and rewrite it. CareerPath Guide keeps your résumé in this browser "
    "session's memory only and does not log it. If you do not want that, use the Career Q&A chat "
    "without uploading."
)

LIMITS_NOTE = (
    "CareerPath Guide gives general career guidance only. It cannot guarantee interviews or job offers, "
    "and it does not give legal, medical, financial, or mental-health advice."
)

OUT_OF_SCOPE = (
    "I can only help with career-preparation topics, so I can't answer that one well. "
    "I can help with: " + ", ".join(SUPPORTED_TOPICS) + ". "
    "Try one of the suggested questions, or rephrase your question about your career."
)

BLOCKED = {
    "legal": "I can't give legal advice. For questions about contracts, discrimination, or your legal rights, "
    "please consult a licensed attorney or your local employment agency.",
    "medical": "I can't give medical advice. Please talk to a qualified health professional.",
    "financial": "I can't give financial, tax, or investment advice. Please consult a qualified financial professional.",
    "mental_health": "I can't give mental-health advice. If you are struggling, please reach out to a qualified "
    "professional or your school's counseling service. In the U.S. you can call or text 988 at any time "
    "if you are in crisis.",
    "guarantee": "I can't guarantee interviews or job offers. I can help you prepare so you present yourself as "
    "clearly and honestly as possible.",
    "scrape_apply": "I don't scrape job boards or submit applications for you. I can explain how to search "
    "effectively, and you can paste a job description for me to analyse against your résumé.",
}

MODE_B_NEEDS_INPUT = (
    "To tailor or check a résumé I need two things: **upload your résumé** (PDF, DOCX or TXT) and "
    "**paste the job description** in the side panel, then press **Analyse**."
)

OFFLINE_NOTE = (
    "_Offline mode: no API key is configured, so this is the best-matching passage from the knowledge base "
    "rather than a model-written answer. Add a key in `.env` for full answers._"
)

ATS_DISCLAIMER = (
    "ATS-readiness (heuristic): these checks reflect common parsing guidance, not any vendor's real "
    "algorithm. Real systems differ, and no score guarantees an interview."
)

TAILOR_DISCLAIMER = (
    "These are suggested rewrites of your own experience. Review each one: only accepted changes are "
    "exported. Never keep a change that claims something that isn't true for you."
)
