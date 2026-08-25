from jdscraper.extract.fields import extract_fields


def test_extracts_year_range():
    fields = extract_fields(
        title="SDET",
        description="8-12 years of experience in test automation with Java and Selenium.",
        company_domain="fintech",
    )
    assert fields.years_min == 8
    assert fields.years_max == 12


def test_extracts_plus_years_as_min_only():
    fields = extract_fields(
        title="QA Lead",
        description="Minimum 10+ years in quality engineering.",
        company_domain="saas",
    )
    assert fields.years_min == 10
    assert fields.years_max is None


def test_extracts_tech_stack_from_description():
    fields = extract_fields(
        title="SDET",
        description="Hands-on Playwright, TypeScript, REST Assured, AWS and GitHub Actions.",
        company_domain="saas",
    )
    assert "Playwright" in fields.tech_stack
    assert "TypeScript" in fields.tech_stack
    assert "REST Assured" in fields.tech_stack
    assert "AWS" in fields.tech_stack
    assert "GitHub Actions" in fields.tech_stack


def test_javascript_is_not_counted_as_java():
    fields = extract_fields(
        title="SDET",
        description="Cypress and JavaScript only.",
        company_domain="saas",
    )
    assert "JavaScript" in fields.tech_stack
    assert "Java" not in fields.tech_stack


def test_prefers_job_domain_over_company_when_jd_is_specific():
    fields = extract_fields(
        title="SDET - Payments",
        description="Automate UPI and card checkout flows.",
        company_domain="ecommerce",
    )
    assert fields.domain == "fintech"


def test_falls_back_to_company_domain():
    fields = extract_fields(
        title="QA Engineer",
        description="Regression testing of the portal.",
        company_domain="aerospace",
    )
    assert fields.domain == "aerospace"


def test_does_not_treat_silicon_valley_as_semiconductor():
    fields = extract_fields(
        title="Staff Software Engineer in Test",
        description="Join Okta in Silicon Valley and Bengaluru. Selenium, Java, AWS.",
        company_domain="saas",
    )
    assert fields.domain == "saas"
    assert "Selenium" in fields.tech_stack


def test_normalizes_yrs_shorthand():
    fields = extract_fields(
        title="Test Architect",
        description="Exp: 12 to 16 Yrs. Selenium, TestNG.",
        company_domain="it_services",
    )
    assert fields.years_min == 12
    assert fields.years_max == 16
    assert "Selenium" in fields.tech_stack
    assert "TestNG" in fields.tech_stack
