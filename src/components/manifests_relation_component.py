from pathlib import Path
from typing import List

from charmed_kubeflow_chisme.components.component import Component
from charms.resource_dispatcher.v0.kubernetes_manifests import (
    KubernetesManifest,
    KubernetesManifestsRequirer,
)
from ops import ActiveStatus, CharmBase, StatusBase


class KubernetesManifestRelationComponent(Component):
    """
    A Component that wraps the requirer side of the resource_dispatcher charm library.
    """

    def __init__(
        self, charm: CharmBase, name: str, relation_name: str, manifests_paths: List[Path]
    ):
        super().__init__(charm, name)
        self.relation_name = relation_name
        self.manifests_paths = manifests_paths

        self.kubernetes_manifests_requirer = KubernetesManifestsRequirer(
            charm, relation_name, self._get_manifests_items()
        )

    def _get_manifests_items(self) -> List[KubernetesManifest]:
        """
        Reads the Kubernetes manifests contents from the manifests_paths
        and creates a KubernetesManifest item for each manifest.

        Returns: List of KubernetesManifest.
        """
        manifests_items = []
        for manifest_path in self.manifests_paths:
            content = Path(manifest_path).read_text()
            manifest_item = KubernetesManifest(manifest_content=content)
            manifests_items.append(manifest_item)
        return manifests_items

    def get_status(self) -> StatusBase:
        return ActiveStatus()
