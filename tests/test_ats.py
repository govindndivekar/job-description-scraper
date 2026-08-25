from jdscraper.ats.detect import detect_ats
from jdscraper.ats.greenhouse import parse_greenhouse_jobs
from jdscraper.ats.lever import parse_lever_jobs
from jdscraper.ats.workday import parse_workday_jobs


GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 99,
            "title": "Senior SDET",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/99",
            "location": {"name": "Bengaluru, India"},
            "offices": [{"name": "Bengaluru", "location": "Bengaluru, India"}],
            "content": "<p>8-12 years. Playwright and Java.</p>",
        },
        {
            "id": 100,
            "title": "Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/100",
            "location": {"name": "Bengaluru, India"},
            "content": "<p>Go services.</p>",
        },
    ]
}

LEVER_PAYLOAD = [
    {
        "id": "abc",
        "text": "QA Automation Engineer",
        "hostedUrl": "https://jobs.lever.co/acme/abc",
        "categories": {"location": "Bangalore", "team": "QA"},
        "descriptionPlain": "Cypress and TypeScript. 5-8 years.",
    }
]

WORKDAY_PAYLOAD = {
    "jobPostings": [
        {
            "title": "Software Test Engineer",
            "externalPath": "/job/Bengaluru/Software-Test-Engineer_JR-1",
            "locationsText": "Bengaluru, Karnataka, India",
            "bulletFields": ["JR-1"],
        }
    ]
}


def test_parse_greenhouse_keeps_location_and_html_description():
    jobs = parse_greenhouse_jobs(GREENHOUSE_PAYLOAD, company="Acme")
    assert [job.external_id for job in jobs] == ["99", "100"]
    assert jobs[0].title == "Senior SDET"
    assert jobs[0].location == "Bengaluru, India"
    assert "Playwright" in jobs[0].description
    assert jobs[0].url.endswith("/99")
    assert jobs[0].source == "greenhouse"


def test_parse_lever_jobs():
    jobs = parse_lever_jobs(LEVER_PAYLOAD, company="Acme")
    assert len(jobs) == 1
    assert jobs[0].title == "QA Automation Engineer"
    assert jobs[0].location == "Bangalore"
    assert jobs[0].source == "lever"


def test_parse_workday_jobs_builds_url():
    jobs = parse_workday_jobs(
        WORKDAY_PAYLOAD,
        company="Bosch",
        board_url="https://bosch.wd3.myworkdayjobs.com/bosch_in",
    )
    assert len(jobs) == 1
    assert jobs[0].title == "Software Test Engineer"
    assert "Bengaluru" in jobs[0].location
    assert jobs[0].url.endswith("/job/Bengaluru/Software-Test-Engineer_JR-1")
    assert jobs[0].source == "workday"


def test_detect_greenhouse_board():
    hit = detect_ats("https://boards.greenhouse.io/atlassian/jobs/123", "")
    assert hit.kind == "greenhouse"
    assert hit.slug == "atlassian"


def test_detect_greenhouse_embed_in_html():
    html = '<script src="https://boards.greenhouse.io/embed/job_board/js?for=postman"></script>'
    hit = detect_ats("https://www.postman.com/company/careers/", html)
    assert hit.kind == "greenhouse"
    assert hit.slug == "postman"


def test_detect_lever():
    hit = detect_ats("https://jobs.lever.co/razorpay", "<html></html>")
    assert hit.kind == "lever"
    assert hit.slug == "razorpay"


def test_detect_workday():
    hit = detect_ats("https://intel.wd1.myworkdayjobs.com/External", "")
    assert hit.kind == "workday"
    assert hit.slug == "intel"
    assert hit.site == "External"


def test_detect_ashby():
    hit = detect_ats("https://jobs.ashbyhq.com/openai", "")
    assert hit.kind == "ashby"
    assert hit.slug == "openai"


def test_unknown_stays_generic():
    hit = detect_ats("https://www.example.com/careers", "<html><a href='/jobs'>Jobs</a></html>")
    assert hit.kind == "generic"
    assert hit.slug is None
