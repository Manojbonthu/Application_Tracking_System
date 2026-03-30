import json
import re
import spacy
from spacy.matcher import PhraseMatcher
from typing import List, Dict
import os

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[NLP] en_core_web_sm not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

# Load skills taxonomy from JSON at runtime (not hardcoded in logic)
TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "skills_taxonomy.json")
_all_skills: List[str] = []
_skill_set: set = set()

def _load_taxonomy():
    global _all_skills, _skill_set
    try:
        with open(TAXONOMY_PATH, "r") as f:
            taxonomy = json.load(f)
        for category_skills in taxonomy.values():
            _all_skills.extend(category_skills)
        _skill_set = {s.lower() for s in _all_skills}
        print(f"[NLP] Loaded {len(_all_skills)} skills from taxonomy.")
    except Exception as e:
        print(f"[NLP] Could not load taxonomy: {e}")

_load_taxonomy()

# Build PhraseMatcher
_matcher = None

def _build_matcher():
    global _matcher
    if nlp is None:
        return
    _matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in _all_skills]
    _matcher.add("SKILLS", patterns)
    print("[NLP] PhraseMatcher built.")

_build_matcher()


# Synonym normalization map
SYNONYMS: Dict[str, str] = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "dl": "deep learning",
    "cv": "computer vision",
    "rnn": "recurrent neural network",
    "cnn": "convolutional neural network",
    "rl": "reinforcement learning",
    "llm": "large language model",
    "genai": "generative ai",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "sklearn": "scikit-learn",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "pg": "postgresql",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "node.js": "nodejs",
    "express.js": "express",
    "next.js": "nextjs",
    "ci/cd": "ci cd",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
}


def normalize_skill(skill: str) -> str:
    lower = skill.lower().strip()
    return SYNONYMS.get(lower, lower)


def extract_skills_from_text(text: str) -> List[str]:
    """
    Multi-method skill extraction:
    1. spaCy PhraseMatcher (taxonomy-based, runtime loaded)
    2. Context pattern extraction (sentences with trigger words)
    3. Section-based parsing (Skills section content)
    """
    found_skills = set()

    if nlp is None or _matcher is None:
        # Fallback: simple regex scan against taxonomy
        text_lower = text.lower()
        for skill in _all_skills:
            if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
                found_skills.add(skill.lower())
        return list(found_skills)

    doc = nlp(text[:100000])  # limit to 100k chars for performance

    # Method 1 — PhraseMatcher
    matches = _matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        found_skills.add(span.text.lower())

    # Method 2 — Context pattern extraction
    trigger_words = [
        "proficient in", "experience in", "skilled in", "expertise in",
        "knowledge of", "worked with", "using", "familiar with",
        "hands-on", "background in"
    ]
    text_lower = text.lower()
    for trigger in trigger_words:
        idx = text_lower.find(trigger)
        while idx != -1:
            snippet = text[idx + len(trigger): idx + len(trigger) + 100]
            # Extract words/phrases from snippet up to punctuation or newline
            parts = re.split(r'[,.\n;]', snippet)
            if parts:
                candidates = re.split(r'\s+and\s+|\s+or\s+|/', parts[0])
                for c in candidates:
                    c = c.strip().lower()
                    if 2 < len(c) < 40 and c in _skill_set:
                        found_skills.add(c)
            idx = text_lower.find(trigger, idx + 1)

    # Method 3 — Section parsing
    section_pattern = re.compile(
        r'(?:technical\s+)?skills?\s*[:\-]?\s*(.*?)(?=\n\n|\Z)',
        re.IGNORECASE | re.DOTALL
    )
    section_match = section_pattern.search(text)
    if section_match:
        section_text = section_match.group(1)
        tokens = re.split(r'[,|•\n/]', section_text)
        for token in tokens:
            token = token.strip().lower()
            if 1 < len(token) < 40 and token in _skill_set:
                found_skills.add(token)

    # Normalize all found skills
    normalized = set()
    for skill in found_skills:
        normalized.add(normalize_skill(skill))

    return sorted(list(normalized))


def extract_skills_with_source(text: str) -> List[Dict[str, str]]:
    """Returns list of dicts with skill_name and source."""
    skills = extract_skills_from_text(text)
    return [{"skill_name": s, "source": "nlp"} for s in skills]
