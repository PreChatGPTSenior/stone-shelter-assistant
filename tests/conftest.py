"""Select existing search checks by their acceptance criterion markers."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--acceptance",
        action="append",
        default=[],
        metavar="AC-ID",
        help="Select checks associated with an AC; repeat to select the union.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    requested: list[str] = config.getoption("acceptance")
    if not requested:
        return
    associations = {
        item: {marker.args[0] for marker in item.iter_markers("acceptance")}
        for item in items
    }
    known = set().union(*associations.values())
    unknown = set(requested) - known
    if unknown:
        raise pytest.UsageError(
            "No collected checks for acceptance criteria: " + ", ".join(sorted(unknown))
        )
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        (selected if associations[item].intersection(requested) else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
