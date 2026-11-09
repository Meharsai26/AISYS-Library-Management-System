import pytest

from app.services.member_import import validate_member_csv


def test_valid_members_with_default_status():
    content = (
        b"card_number,display_name\n"
        b"M001,Alice\n"
        b"M002,Bob\n"
    )

    result = validate_member_csv(content)

    assert len(result["valid_rows"]) == 2
    assert result["errors"] == []
    assert result["valid_rows"][0]["status"] == "ACTIVE"


def test_missing_required_column():
    content = b"card_number\nM001\n"

    with pytest.raises(ValueError, match="Required columns"):
        validate_member_csv(content)


def test_invalid_member_status():
    content = (
        b"card_number,display_name,status\n"
        b"M001,Alice,UNKNOWN\n"
    )

    result = validate_member_csv(content)

    assert len(result["valid_rows"]) == 0
    assert result["errors"][0]["row"] == 2
    assert "Invalid member status" in result["errors"][0]["reason"]


def test_duplicate_card_number_within_csv():
    content = (
        b"card_number,display_name\n"
        b"M001,Alice\n"
        b"M001,Bob\n"
    )

    result = validate_member_csv(content)

    assert len(result["valid_rows"]) == 1
    assert len(result["errors"]) == 1
    assert "Duplicate card_number" in result["errors"][0]["reason"]


def test_missing_member_name():
    content = (
        b"card_number,display_name\n"
        b"M001,\n"
    )

    result = validate_member_csv(content)

    assert result["valid_rows"] == []
    assert "Invalid display_name" in result["errors"][0]["reason"]


def test_extra_csv_columns():
    content = (
        b"card_number,display_name\n"
        b"M001,Alice,Unexpected\n"
    )

    result = validate_member_csv(content)

    assert result["valid_rows"] == []
    assert "Unexpected extra columns" in result["errors"][0]["reason"]


def test_invalid_utf8_encoding():
    with pytest.raises(ValueError, match="UTF-8"):
        validate_member_csv(b"\xff\xfe")


def test_duplicate_header_names():
    content = (
        b"card_number,card_number,display_name\n"
        b"M001,M002,Alice\n"
    )

    with pytest.raises(ValueError, match="Duplicate CSV column names"):
        validate_member_csv(content)
