from dataclasses import dataclass


JUNIOR_TERMS = (
    "intern",
    "internship",
    "fresher",
    "graduate",
    "campus",
    "apprentice",
    "trainee",
)

BANGALORE_TOKENS = (
    "bengaluru",
    "bangalore",
    "banagalore",
    "banglore",
    "blr",
)

OTHER_CITY_TOKENS = (
    "pune",
    "hyderabad",
    "mumbai",
    "chennai",
    "delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "kochi",
    "coimbatore",
    "indore",
    "chandigarh",
    "remote",
)

SDET_TITLE = (
    "sdet",
    "software development engineer in test",
    "software engineer in test",
    "software development engineer - test",
)

AUTOMATION_TITLE = (
    "test automation",
    "automation test",
    "automation engineer",
    "qa automation",
    "automation architect",
    "test architect",
    "automation lead",
)

QA_TITLE = (
    "quality assurance",
    "quality engineer",
    "quality engineering",
    "qa engineer",
    "qa lead",
    "qa manager",
    "qa analyst",
    "quality analyst",
    "sqa",
)

SOFTWARE_TEST_TITLE = (
    "software test",
    "software tester",
    "test engineer",
    "testing engineer",
    "test lead",
    "test manager",
    "test specialist",
    "verification and validation",
    "v&v",
)

SOFTWARE_QA_SIGNALS = (
    "selenium",
    "playwright",
    "cypress",
    "appium",
    "rest assured",
    "pytest",
    "testng",
    "junit",
    "specflow",
    "cucumber",
    "webdriver",
    "automation framework",
    "sdet",
    "api test",
    "api automation",
    "ui automation",
    "test automation",
    "quality engineering",
    "software test",
    "hil test",
    "functional testing",
    "regression testing",
)

MANUFACTURING_QC = (
    "incoming inspection",
    "ppap",
    "shop-floor",
    "shop floor",
    "quality control",
    "ncr",
    "fai",
    "supplier quality",
    "process quality",
    "line quality",
)


@dataclass(frozen=True, slots=True)
class QADecision:
    keep: bool
    role_family: str | None = None
    reason: str = ""


def _norm(text: str) -> str:
    return " ".join((text or "").lower().replace("-", " ").split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _is_bangalore(location: str) -> bool:
    loc = _norm(location)
    if not loc:
        return False
    if _contains_any(loc, BANGALORE_TOKENS):
        return True
    # Bare "India" is not enough; a non-Bangalore Indian city is a reject.
    if _contains_any(loc, OTHER_CITY_TOKENS):
        return False
    return False


def classify_role(title: str, description: str, location: str) -> QADecision:
    title_n = _norm(title)
    desc_n = _norm(description)
    blob = f"{title_n} {desc_n}"

    if _contains_any(title_n, JUNIOR_TERMS):
        return QADecision(keep=False, reason="junior_title")

    if not _is_bangalore(location):
        return QADecision(keep=False, reason="wrong_city")

    family: str | None = None
    if _contains_any(title_n, SDET_TITLE):
        family = "sdet"
    elif _contains_any(title_n, AUTOMATION_TITLE):
        family = "test_automation"
    elif _contains_any(title_n, SOFTWARE_TEST_TITLE):
        family = "software_testing"
    elif _contains_any(title_n, QA_TITLE) or title_n == "qa" or " qa " in f" {title_n} ":
        family = "qa"

    if family is None:
        return QADecision(keep=False, reason="not_qa")

    has_software_signal = _contains_any(blob, SOFTWARE_QA_SIGNALS)
    looks_like_factory_qc = _contains_any(desc_n, MANUFACTURING_QC) and not has_software_signal
    vague_quality_title = family == "qa" and "quality engineer" in title_n
    if looks_like_factory_qc or (vague_quality_title and not has_software_signal):
        return QADecision(keep=False, reason="not_software_qa")

    return QADecision(keep=True, role_family=family)
