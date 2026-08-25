from dataclasses import dataclass, field
import re


YEAR_RANGE = re.compile(
    r"(?:exp(?:erience)?[:\s]*)?(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*(?:\+?\s*)?(?:years?|yrs?)\b",
    re.I,
)
YEAR_PLUS = re.compile(
    r"(?:minimum\s+|min(?:imum)?\s+|at least\s+)?(\d{1,2})\s*\+\s*(?:years?|yrs?)\b",
    re.I,
)
YEAR_MIN = re.compile(
    r"(?:minimum|min(?:imum)?|at least)\s+(\d{1,2})\s*(?:years?|yrs?)\b",
    re.I,
)

TECH_TERMS = (
    "Playwright",
    "Selenium",
    "Cypress",
    "Appium",
    "REST Assured",
    "RestAssured",
    "TestNG",
    "JUnit",
    "PyTest",
    "pytest",
    "Cucumber",
    "SpecFlow",
    "WebdriverIO",
    "TypeScript",
    "JavaScript",
    "Java",
    "Python",
    "C#",
    "Kotlin",
    "AWS",
    "Azure",
    "GCP",
    "GitHub Actions",
    "Jenkins",
    "GitLab CI",
    "Azure DevOps",
    "CI/CD",
    "Docker",
    "Kubernetes",
    "Postman",
    "JMeter",
    "k6",
    "Gatling",
    "BrowserStack",
    "Sauce Labs",
    "Testim",
    "Tosca",
    "UFT",
    "Robot Framework",
    "MCP",
    "GitHub Copilot",
)

DOMAIN_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fintech", ("upi", "card checkout", "fintech", "payments api", "payment gateway")),
    ("semiconductor", ("rtl", "vlsi", "silicon validation", "dft", "semiconductor", "soc design")),
    ("aerospace", ("avionics", "aerospace", "do-178")),
    ("automotive", ("adas", "automotive", "autosar", "iso 26262")),
    ("healthcare", ("hipaa", "medical device", "ehr", "healthcare")),
    ("ecommerce", ("marketplace", "ecommerce", "e-commerce")),
    ("saas", ("saas", "multi-tenant", "b2b platform")),
)


@dataclass(slots=True)
class ExtractedFields:
    years_min: int | None = None
    years_max: int | None = None
    tech_stack: list[str] = field(default_factory=list)
    domain: str = ""


def _extract_years(text: str) -> tuple[int | None, int | None]:
    if match := YEAR_RANGE.search(text):
        lo, hi = int(match.group(1)), int(match.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)
    if match := YEAR_PLUS.search(text):
        return int(match.group(1)), None
    if match := YEAR_MIN.search(text):
        return int(match.group(1)), None
    return None, None


def _extract_tech(text: str) -> list[str]:
    found: list[str] = []
    for term in TECH_TERMS:
        if not re.search(rf"(?<![A-Za-z0-9+#]){re.escape(term)}(?![A-Za-z0-9+#])", text, re.I):
            continue
        canonical = "REST Assured" if term.lower() in {"rest assured", "restassured"} else term
        if canonical.lower() == "pytest":
            canonical = "PyTest"
        if canonical not in found:
            found.append(canonical)
    return found


def _hint_in(blob: str, hint: str) -> bool:
    if " " in hint or "-" in hint:
        return hint in blob
    return re.search(rf"\b{re.escape(hint)}\b", blob) is not None


def _extract_domain(text: str, company_domain: str) -> str:
    blob = text.lower()
    for domain, hints in DOMAIN_HINTS:
        if any(_hint_in(blob, hint) for hint in hints):
            return domain
    return company_domain or ""


def extract_fields(title: str, description: str, company_domain: str = "") -> ExtractedFields:
    blob = f"{title}\n{description}"
    years_min, years_max = _extract_years(blob)
    return ExtractedFields(
        years_min=years_min,
        years_max=years_max,
        tech_stack=_extract_tech(blob),
        domain=_extract_domain(blob, company_domain),
    )
