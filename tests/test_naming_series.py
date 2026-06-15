"""
Tests for the enhanced naming series / number sequence system.

Covers:
- Indian fiscal year helper
- Format string tokens ({prefix}, {year}, {fy}, {month}, {####})
- Default format backward compatibility
- Year-wise reset
- FY boundaries (March 31 vs April 1)
- Padding variations
- SQLite compatibility (no SELECT FOR UPDATE)
"""

from datetime import date, datetime

from sqlalchemy.dialects import postgresql

from backend_core.app.models_v2 import NumberSequence
from backend_core.app.services.inventory_service import (
    _apply_format,
    _build_postgres_sequence_upsert,
    get_indian_fiscal_year,
    get_next_sequence,
)

# ===========================================================================
# TestIndianFiscalYear
# ===========================================================================


class TestIndianFiscalYear:
    """Tests for get_indian_fiscal_year() helper."""

    def test_april_starts_new_fy(self):
        # April 2025 is in FY2526 (Apr 2025 - Mar 2026)
        assert get_indian_fiscal_year(date(2025, 4, 1)) == "FY2526"

    def test_march_is_previous_fy(self):
        # March 2026 is still in FY2526 (Apr 2025 - Mar 2026)
        assert get_indian_fiscal_year(date(2026, 3, 31)) == "FY2526"

    def test_january_is_previous_fy(self):
        # January 2026 is in FY2526
        assert get_indian_fiscal_year(date(2026, 1, 15)) == "FY2526"

    def test_december_same_fy_as_april(self):
        # December 2025 is in FY2526 (same FY as April 2025)
        assert get_indian_fiscal_year(date(2025, 12, 31)) == "FY2526"

    def test_april_2026_is_new_fy(self):
        # April 2026 starts FY2627
        assert get_indian_fiscal_year(date(2026, 4, 1)) == "FY2627"

    def test_century_boundary(self):
        # March 2100 should be FY9900 (Apr 2099 - Mar 2100)
        assert get_indian_fiscal_year(date(2100, 3, 1)) == "FY9900"

    def test_april_2099_to_march_2100(self):
        assert get_indian_fiscal_year(date(2099, 4, 1)) == "FY9900"

    def test_defaults_to_today(self):
        # Should not raise when called without arguments
        result = get_indian_fiscal_year()
        assert result.startswith("FY")
        assert len(result) == 6

    def test_accepts_datetime_object(self):
        dt = datetime(2025, 6, 15, 10, 30, 0)
        assert get_indian_fiscal_year(dt) == "FY2526"


# ===========================================================================
# TestApplyFormat
# ===========================================================================


class TestApplyFormat:
    """Tests for _apply_format() internal helper."""

    def test_prefix_token(self):
        result = _apply_format("{prefix}/{####}", "GRN", 4, 1)
        assert result.startswith("GRN/")

    def test_year_token(self):
        result = _apply_format("{prefix}-{year}-{####}", "LOT", 4, 42, ref_date=date(2026, 5, 1))
        assert result == "LOT-2026-0042"

    def test_fy_token(self):
        result = _apply_format("GRN/{fy}/{####}", "GRN", 4, 1, ref_date=date(2025, 6, 1))
        assert result == "GRN/FY2526/0001"

    def test_month_token(self):
        result = _apply_format("{prefix}-{year}-{month}-{####}", "LOT", 4, 1, ref_date=date(2026, 5, 18))
        assert result == "LOT-2026-05-0001"

    def test_padding_two_hashes(self):
        result = _apply_format("{prefix}/{##}", "DN", 2, 1)
        assert result.endswith("/01")

    def test_padding_six_hashes(self):
        result = _apply_format("{prefix}/{######}", "DN", 6, 1)
        assert result.endswith("/000001")

    def test_padding_large_number(self):
        result = _apply_format("{prefix}/{####}", "DN", 4, 9999)
        assert result.endswith("/9999")

    def test_padding_overflow(self):
        # Number wider than padding still shows full number
        result = _apply_format("{prefix}/{##}", "DN", 2, 999)
        assert result.endswith("/999")

    def test_all_tokens_combined(self):
        result = _apply_format(
            "{prefix}/{fy}/{month}/{####}",
            "GRN",
            4,
            7,
            ref_date=date(2025, 11, 3),
        )
        assert result == "GRN/FY2526/11/0007"


# ===========================================================================
# TestGetNextSequence — backward compatibility
# ===========================================================================


class TestGetNextSequenceDefault:
    """Existing callers without format_str should still work."""

    def test_creates_new_sequence(self, db):
        seq1 = get_next_sequence(db, "compat_test", "TST")
        assert "TST" in seq1
        assert "/000001" in seq1

    def test_increments(self, db):
        get_next_sequence(db, "compat_inc", "TST")
        seq2 = get_next_sequence(db, "compat_inc", "TST")
        assert seq2.endswith("/000002")

    def test_no_year(self, db):
        seq = get_next_sequence(db, "compat_no_year", "NTY", year_wise=False)
        parts = seq.split("/")
        assert len(parts) == 2  # PREFIX/NUMBER
        assert parts[0] == "NTY"

    def test_year_wise_includes_year(self, db):
        seq = get_next_sequence(db, "compat_year", "YR")
        parts = seq.split("/")
        assert len(parts) == 3  # PREFIX/YEAR/NUMBER
        assert parts[1].isdigit()
        assert len(parts[1]) == 4


# ===========================================================================
# TestGetNextSequence — custom format_str
# ===========================================================================


class TestGetNextSequenceFormat:
    """Tests for the new format_str parameter."""

    def test_fy_format(self, db):
        seq = get_next_sequence(db, "fmt_fy", "GRN", format_str="GRN/{fy}/{####}")
        fy = get_indian_fiscal_year()
        assert seq == f"GRN/{fy}/0001"

    def test_prefix_year_format(self, db):
        seq = get_next_sequence(
            db,
            "fmt_prefix_year",
            "LOT",
            format_str="{prefix}-{year}-{####}",
        )
        year = datetime.utcnow().year
        assert seq == f"LOT-{year}-0001"

    def test_month_format(self, db):
        seq = get_next_sequence(
            db,
            "fmt_month",
            "INV",
            format_str="{prefix}/{year}/{month}/{####}",
        )
        now = datetime.utcnow()
        assert seq == f"INV/{now.year}/{now.month:02d}/0001"

    def test_short_padding(self, db):
        seq = get_next_sequence(db, "fmt_short", "X", format_str="{prefix}-{##}")
        assert seq == "X-01"

    def test_long_padding(self, db):
        seq = get_next_sequence(db, "fmt_long", "X", format_str="{prefix}-{########}")
        assert seq == "X-00000001"

    def test_format_str_increments(self, db):
        get_next_sequence(db, "fmt_inc", "GRN", format_str="GRN/{fy}/{####}")
        seq2 = get_next_sequence(db, "fmt_inc", "GRN", format_str="GRN/{fy}/{####}")
        fy = get_indian_fiscal_year()
        assert seq2 == f"GRN/{fy}/0002"

    def test_format_str_stored_on_model(self, db):
        """format_str passed at creation is saved on the NumberSequence row."""
        get_next_sequence(db, "fmt_stored", "TST", format_str="{prefix}/{fy}/{####}")
        row = db.query(NumberSequence).filter_by(sequence_name="fmt_stored").first()
        assert row.format_str == "{prefix}/{fy}/{####}"

    def test_stored_format_used_when_no_param(self, db):
        """If format_str is stored on the row, it is used even if caller omits it."""
        get_next_sequence(db, "fmt_auto", "TST", format_str="{prefix}/{####}")
        # Call again WITHOUT format_str — should use stored format
        seq2 = get_next_sequence(db, "fmt_auto", "TST")
        assert seq2 == "TST/0002"

    def test_param_format_overrides_stored(self, db):
        """format_str passed as parameter overrides the stored one."""
        get_next_sequence(db, "fmt_override", "TST", format_str="{prefix}/{####}")
        # Override with a different format
        seq2 = get_next_sequence(db, "fmt_override", "TST", format_str="{prefix}-{####}")
        assert seq2 == "TST-0002"


# ===========================================================================
# TestYearReset
# ===========================================================================


class TestYearReset:
    """Year-wise reset when calendar year changes."""

    def test_year_change_resets_counter(self, db):
        # Create a sequence with year=2025
        seq_row = NumberSequence(
            sequence_name="yr_reset_test",
            prefix="YR",
            current_number=42,
            year=2025,
            padding=4,
        )
        db.add(seq_row)
        db.flush()

        # Calling now (2026) should reset
        result = get_next_sequence(db, "yr_reset_test", "YR")
        current_year = datetime.utcnow().year
        assert result.endswith("/0001")
        assert str(current_year) in result

        # Verify the row was updated
        db.refresh(seq_row)
        assert seq_row.current_number == 1
        assert seq_row.year == current_year


# ===========================================================================
# TestSQLiteCompatibility
# ===========================================================================


class TestSQLiteCompatibility:
    """Verify no SELECT FOR UPDATE errors on SQLite."""

    def test_multiple_sequences_no_error(self, db):
        """Rapid sequential calls should not fail on SQLite."""
        results = []
        for i in range(10):
            r = get_next_sequence(db, "sqlite_test", "SQ")
            results.append(r)

        # All should be unique
        assert len(set(results)) == 10

        # Should end with sequential numbers
        assert results[0].endswith("/000001")
        assert results[9].endswith("/000010")

    def test_multiple_different_sequences(self, db):
        """Different sequence names should be independent."""
        a1 = get_next_sequence(db, "seq_a", "A")
        b1 = get_next_sequence(db, "seq_b", "B")
        a2 = get_next_sequence(db, "seq_a", "A")

        assert a1.endswith("/000001")
        assert b1.endswith("/000001")
        assert a2.endswith("/000002")


# ===========================================================================
# TestPostgreSQLConcurrencyPath
# ===========================================================================


class TestPostgreSQLConcurrencyPath:
    """Verify the production DB path uses one atomic upsert statement."""

    def test_postgres_sequence_statement_uses_conflict_update(self):
        stmt = _build_postgres_sequence_upsert(
            sequence_name="pg_atomic",
            prefix="PG",
            current_year=2026,
            year_wise=True,
            format_str="{prefix}/{####}",
        )
        compiled = str(stmt.compile(dialect=postgresql.dialect()))

        assert "ON CONFLICT" in compiled
        assert "DO UPDATE" in compiled
        assert "RETURNING" in compiled
        assert "IS DISTINCT FROM" in compiled
