"""Tests for display formatting utilities."""
from rich.console import Console
from rich.table import Table

from operations.display import display_results_table, print_reference_result, print_statistics
from operations.models import BatchReferenceResult, ProcessingResult, RenameStatus


def _make_result(
    status: RenameStatus,
    source: str = "src.png",
    proposed: str = "prop.png",
    final: str = "final.png",
) -> ProcessingResult:
    return ProcessingResult(source=source, proposed=proposed, final=final, status=status)


def should_print_table_with_correct_columns(mocker):
    console = mocker.Mock(spec=Console)

    display_results_table(console, [], dry_run=False)

    console.print.assert_called_once()
    table = console.print.call_args[0][0]
    assert isinstance(table, Table)
    column_names = [col.header for col in table.columns]
    assert "Source" in column_names
    assert "Proposed" in column_names
    assert "Final" in column_names
    assert "Status" in column_names


def should_include_dry_run_in_table_title(mocker):
    console = mocker.Mock(spec=Console)

    display_results_table(console, [], dry_run=True)

    table = console.print.call_args[0][0]
    assert "dry-run" in table.title


def should_include_apply_in_table_title_when_not_dry_run(mocker):
    console = mocker.Mock(spec=Console)

    display_results_table(console, [], dry_run=False)

    table = console.print.call_args[0][0]
    assert "apply" in table.title


def should_add_row_for_each_result(mocker):
    console = mocker.Mock(spec=Console)
    results = [
        _make_result(RenameStatus.RENAMED, "a.png", "b.png", "b.png"),
        _make_result(RenameStatus.UNCHANGED, "c.png", "c.png", "c.png"),
    ]

    display_results_table(console, results, dry_run=False)

    table = console.print.call_args[0][0]
    assert table.row_count == 2


def should_display_renamed_status(mocker):
    console = mocker.Mock(spec=Console)
    results = [_make_result(RenameStatus.RENAMED)]

    display_results_table(console, results, dry_run=False)

    table = console.print.call_args[0][0]
    assert table.row_count == 1


def should_display_collision_status(mocker):
    console = mocker.Mock(spec=Console)
    results = [_make_result(RenameStatus.COLLISION)]

    display_results_table(console, results, dry_run=False)

    table = console.print.call_args[0][0]
    assert table.row_count == 1


def should_display_error_status(mocker):
    console = mocker.Mock(spec=Console)
    results = [_make_result(RenameStatus.ERROR)]

    display_results_table(console, results, dry_run=False)

    table = console.print.call_args[0][0]
    assert table.row_count == 1


def should_print_statistics_with_correct_counts(mocker):
    console = mocker.Mock(spec=Console)
    results = [
        _make_result(RenameStatus.RENAMED),
        _make_result(RenameStatus.RENAMED),
        _make_result(RenameStatus.UNCHANGED),
        _make_result(RenameStatus.COLLISION),
        _make_result(RenameStatus.ERROR),
    ]

    print_statistics(console, results)

    console.print.assert_called_once()
    output = console.print.call_args[0][0]
    assert "2 renamed" in output
    assert "1 unchanged" in output
    assert "1 collision" in output
    assert "1 error" in output


def should_print_statistics_with_all_zeros_for_empty_list(mocker):
    console = mocker.Mock(spec=Console)

    print_statistics(console, [])

    console.print.assert_called_once()
    output = console.print.call_args[0][0]
    assert "0 renamed" in output
    assert "0 unchanged" in output


def should_print_no_references_when_total_is_zero(mocker):
    console = mocker.Mock(spec=Console)
    ref_result = BatchReferenceResult(total_references=0, files_updated=0)

    print_reference_result(console, ref_result, dry_run=False)

    console.print.assert_called_once()
    output = console.print.call_args[0][0]
    assert "No markdown references found" in output


def should_print_would_update_when_dry_run(mocker):
    console = mocker.Mock(spec=Console)
    ref_result = BatchReferenceResult(total_references=3, files_updated=2)

    print_reference_result(console, ref_result, dry_run=True)

    console.print.assert_called_once()
    output = console.print.call_args[0][0]
    assert "Would update" in output
    assert "3" in output
    assert "2" in output


def should_print_updated_when_not_dry_run(mocker):
    console = mocker.Mock(spec=Console)
    ref_result = BatchReferenceResult(total_references=5, files_updated=3)

    print_reference_result(console, ref_result, dry_run=False)

    console.print.assert_called_once()
    output = console.print.call_args[0][0]
    assert "Updated" in output
    assert "5" in output
    assert "3" in output
