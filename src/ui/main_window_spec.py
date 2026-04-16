from operations.models import RenameOutcome
from ui.rename_actions import perform_rename_with_refs


def should_delegate_single_rename_to_apply_rename_with_references(tmp_path, mocker):
    old_path = tmp_path / "old.png"
    mock_outcome = RenameOutcome(renamed=True, new_path=tmp_path / "new.png", references_updated=2)
    mock_apply = mocker.patch(
        "ui.rename_actions.apply_rename_with_references", return_value=mock_outcome
    )

    result = perform_rename_with_refs(old_path, "new.png", tmp_path, True, False)

    assert result == 2
    mock_apply.assert_called_once()
    call_args = mock_apply.call_args
    assert call_args.args[0] == old_path
    assert call_args.args[1] == "new.png"
    assert call_args.args[2] == tmp_path
