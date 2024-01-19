# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
from ops.testing import Harness
from ops.model import ActiveStatus, BlockedStatus
import yaml
from charm import NgcIntegratorCharm, PODDEFAULTS_RELATION, PODDEFAULT_FILE
from components.manifests_relation_component import KubernetesManifestRelationBroadcasterComponent
from lib.charms.kubernetes_manifests.v0.kubernetes_manifests import (
    KUBERNETES_MANIFESTS_FIELD,
    KubernetesManifest)
import pytest

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
    relation_id = harness.add_relation(
        relation_name=PODDEFAULTS_RELATION, remote_app=other_app
    )

    # Assert
    actual_manifests = get_manifests_from_relation(harness, relation_id, harness.model.app)

    assert actual_manifests == [yaml.safe_load(Path(PODDEFAULT_FILE).read_text())]
    assert isinstance(harness.charm.model.unit.status, ActiveStatus)




def get_manifests_from_relation(harness, relation_id, this_app) -> List[dict]:
    """Returns the list of KubernetesManifests from a service-account relation on a harness."""
    raw_relation_data = harness.get_relation_data(relation_id=relation_id, app_or_unit=this_app)
    actual_manifests = json.loads(raw_relation_data[KUBERNETES_MANIFESTS_FIELD])
    return actual_manifests