"""Which findings get published."""

from pr_reviewer.domain.findings import PublishOptions, fingerprint, select_findings
from support.builders import bundle, finding


def test_select_drops_findings_outside_the_diff_and_counts_them():
    # Arrange
    findings = [finding(), finding(line=99), finding(file="other.py")]

    # Act
    selected = select_findings(findings, bundle(), PublishOptions())

    # Assert
    assert [(f.file, f.line) for f in selected.kept] == [("app.py", 10)]
    assert selected.outside_diff == 2


def test_select_applies_confidence_and_severity_filters():
    # Arrange
    findings = [
        finding(confidence="low"),
        finding(severity="low", title="minor"),
        finding(severity="critical", title="major"),
    ]

    # Act
    selected = select_findings(findings, bundle(), PublishOptions(min_severity="medium"))

    # Assert
    assert [f.title for f in selected.kept] == ["major"]
    assert selected.filtered == 2


def test_select_orders_by_severity_caps_the_list_and_declares_the_overflow():
    # Arrange
    findings = [
        finding(severity="low", title="c"),
        finding(severity="critical", title="a"),
        finding(severity="medium", title="b"),
    ]

    # Act
    selected = select_findings(findings, bundle(), PublishOptions(max_findings=2))

    # Assert
    assert [f.title for f in selected.kept] == ["a", "b"]
    assert selected.over_limit == 1


def test_fingerprint_is_stable_across_line_moves_and_whitespace():
    # Act / Assert
    assert fingerprint(finding(line=10)) == fingerprint(finding(line=12, title=" Query  inside a LOOP "))
    assert fingerprint(finding()) != fingerprint(finding(file="b.py"))
