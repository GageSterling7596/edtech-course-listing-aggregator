from datetime import date

from src.edtech_aggregator import CourseListing, decide_report


def test_report_keeps_open_courses_and_flags_the_next_two_weeks():
    listings = [
        CourseListing("Video editing", "Media Lab", "https://example.test/a", date(2026, 11, 2), "cohort"),
        CourseListing("Sound design", "Media Lab", "https://example.test/b", date(2026, 12, 20), "self-paced"),
        CourseListing("Archived class", "Media Lab", "https://example.test/c", date(2026, 10, 1), "cohort"),
    ]

    report = decide_report(listings, date(2026, 10, 25))

    assert [item.title for item in report.open_courses] == ["Video editing", "Sound design"]
    assert [item.title for item in report.due_soon] == ["Video editing"]
    assert report.educator_report == "2 open courses; 1 due within 14 days."
