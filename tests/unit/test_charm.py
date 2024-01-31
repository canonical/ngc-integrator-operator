# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import yaml
from ops.model import ActiveStatus, ErrorStatus
from ops.testing import Harness

from charm import PODDEFAULT_FILE, PODDEFAULTS_RELATION, NgcIntegratorCharm
from lib.charms.resource_dispatcher.v0.kubernetes_manifests import KUBERNETES_MANIFESTS_FIELD


@pytest.fixture
def harness() -> Harness:
    harness = Harness(NgcIntegratorCharm)
    return harness


def test_not_leader(harness):
    """Test when we are not the leader."""
    harness.begin_with_initial_hooks()
    # Assert that we are not Active, and that the leadership-gate is the cause.
    assert not isinstance(harness.charm.model.unit.status, ActiveStatus)
    assert harness.charm.model.unit.status.message.startswith("[leadership-gate]")


def test_kubernetes_manifest_relation_data(harness):
    """Test that the manifest data is sent correctly to the pod-defaults relation"""
    # Arrange
    other_app = "other"
    harness.set_leader(True)
    harness.begin_with_initial_hooks()

    # Mock:
    # * leadership_gate to be active and executed
    harness.charm.leadership_gate.get_status = MagicMock(return_value=ActiveStatus())

    # Act
    relation_id = harness.add_relation(relation_name=PODDEFAULTS_RELATION, remote_app=other_app)

    # Assert
    actual_manifests = get_manifests_from_relation(harness, relation_id, harness.model.app)

    assert actual_manifests == [yaml.safe_load(Path(PODDEFAULT_FILE).read_text())]
    assert isinstance(harness.charm.model.unit.status, ActiveStatus)


@patch("charm.PODDEFAULT_FILE", "non_existent_file.yaml")
def test_incorrect_manifest_path_error_status(harness):
    """
    Test when the manifest file is not found, the charm goes to error
    with the correct error message.
    """
    # Arrange
    harness.set_leader(True)

    # Assert
    with pytest.raises(FileNotFoundError):
        # Act
        harness.begin_with_initial_hooks()
        assert isinstance(harness.charm.model.unit.status, ErrorStatus)


@patch("charm.PODDEFAULT_FILE", "./tests/unit/invalid.yaml")
def test_invalid_yaml_error_status(harness):
    """Test when the manifest file is not a valid yaml, the charm goes to error."""
    # Arrange
    harness.set_leader(True)

    # Assert
    with pytest.raises(yaml.parser.ParserError):
        # Act
        harness.begin_with_initial_hooks()
        assert isinstance(harness.charm.model.unit.status, ErrorStatus)


def get_manifests_from_relation(harness, relation_id, this_app) -> List[dict]:
    """Returns the list of KubernetesManifests from a service-account relation on a harness."""
    raw_relation_data = harness.get_relation_data(relation_id=relation_id, app_or_unit=this_app)
    actual_manifests = json.loads(raw_relation_data[KUBERNETES_MANIFESTS_FIELD])
    return actual_manifests
