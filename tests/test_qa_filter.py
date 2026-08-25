from jdscraper.extract.qa_filter import QADecision, classify_role


def test_sdet_title_is_kept():
    decision = classify_role(
        title="Senior SDET",
        description="Build Playwright suites for payments APIs.",
        location="Bengaluru, Karnataka",
    )
    assert decision.keep is True
    assert decision.role_family == "sdet"


def test_test_automation_architect_is_kept():
    decision = classify_role(
        title="Automation Test Architect",
        description="Own the Java Selenium and REST Assured framework.",
        location="Bangalore",
    )
    assert decision.keep is True
    assert decision.role_family == "test_automation"


def test_manual_qa_engineer_is_kept():
    decision = classify_role(
        title="QA Engineer",
        description="Functional testing of the web and mobile apps.",
        location="Bengaluru",
    )
    assert decision.keep is True
    assert decision.role_family == "qa"


def test_software_engineer_without_test_signal_is_dropped():
    decision = classify_role(
        title="Senior Software Engineer",
        description="Build microservices in Go and Kubernetes.",
        location="Bengaluru",
    )
    assert decision.keep is False
    assert decision.reason == "not_qa"


def test_intern_sdet_is_dropped():
    decision = classify_role(
        title="SDET Intern",
        description="Learn Selenium and write tests.",
        location="Bangalore",
    )
    assert decision.keep is False
    assert decision.reason == "junior_title"


def test_manufacturing_quality_without_software_test_is_dropped():
    decision = classify_role(
        title="Quality Engineer",
        description="Incoming inspection, PPAP, and shop-floor quality control.",
        location="Bengaluru",
    )
    assert decision.keep is False
    assert decision.reason == "not_software_qa"


def test_bosch_software_test_role_is_kept():
    decision = classify_role(
        title="Software Test Engineer - ADAS",
        description="HIL test automation with Python for automotive ECUs.",
        location="Bengaluru",
    )
    assert decision.keep is True
    assert decision.role_family == "software_testing"


def test_pune_only_location_is_dropped():
    decision = classify_role(
        title="SDET",
        description="API automation with REST Assured.",
        location="Pune, Maharashtra",
    )
    assert decision.keep is False
    assert decision.reason == "wrong_city"


def test_multi_city_including_bangalore_is_kept():
    decision = classify_role(
        title="QA Automation Engineer",
        description="Cypress and JavaScript.",
        location="Pune / Bengaluru / Hyderabad",
    )
    assert decision.keep is True


def test_decision_is_dataclass_shape():
    decision = classify_role("SDET", "Playwright", "Bangalore")
    assert isinstance(decision, QADecision)
