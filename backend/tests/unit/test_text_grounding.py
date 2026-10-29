from app.utils.text import normalize_whitespace, validate_excerpt_in_text


def test_normalize_whitespace():
    raw = "  Jane   Doe \n\n Senior   Engineer\t "
    assert normalize_whitespace(raw) == "Jane Doe Senior Engineer"


def test_validate_excerpt_exact_and_normalized():
    full_text = """
    EXPERIENCE
    Senior Software Engineer | ACME Corp | 2021 - Present
    - Architected high-throughput async data ingestion using FastAPI and PostgreSQL.
    - Integrated SAP SuccessFactors for enterprise talent records.
    """
    excerpt = "Architected high-throughput async data ingestion using FastAPI and PostgreSQL."
    assert validate_excerpt_in_text(excerpt, full_text) is True


def test_validate_excerpt_case_and_spacing_tolerance():
    full_text = "Experienced with SQLAlchemy 2.0 async sessions and database migration tools."
    excerpt = "experienced with sqlalchemy 2.0 async sessions"
    assert validate_excerpt_in_text(excerpt, full_text) is True


def test_rejects_hallucinated_excerpt():
    full_text = "Experienced in frontend development using Vue.js and Tailwind CSS."
    # The candidate never mentioned Python or PyTorch
    hallucinated = "Led 10-person machine learning team using Python and PyTorch."
    assert validate_excerpt_in_text(hallucinated, full_text) is False
