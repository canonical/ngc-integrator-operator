#!/usr/bin/env python3
# Copyright 2024 Ubuntu
# See LICENSE file for licensing details.

"""Charm the application."""

import json
import logging
from pathlib import Path

import ops
import yaml
from charmed_kubeflow_chisme.components import (
    CharmReconciler, LeadershipGateComponent)
from components.manifests_relation_component import KubernetesManifestRelationBroadcasterComponent

logger = logging.getLogger(__name__)

PODDEFAULT_FILE = "src/templates/podefault.yaml"
PODDEFAULTS_RELATION = "pod-defaults"

class NgcIntegratorCharm(ops.CharmBase):
    """A Juju charm for NGC Containers integration with Kubeflow."""

    def __init__(self, *args):
        super().__init__(*args)

        # Charm logic
        self.charm_reconciler = CharmReconciler(self)

        self.leadership_gate = self.charm_reconciler.add(
            component=LeadershipGateComponent(
                charm=self,
                name="leadership-gate",
            ),
            depends_on=[],
        )

        self.manifests_broadcaster = self.charm_reconciler.add(
            component = KubernetesManifestRelationBroadcasterComponent(
                charm=self,
                name="manifests-relation-broadcaster",
                relation_name=PODDEFAULTS_RELATION,
                manifests_paths=[PODDEFAULT_FILE]
            ),
            depends_on=[self.leadership_gate]
        )


        self.charm_reconciler.install_default_event_handlers()


if __name__ == "__main__":  # pragma: nocover
    ops.main(NgcIntegratorCharm)  # type: ignore
