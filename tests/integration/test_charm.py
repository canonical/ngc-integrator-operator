#!/usr/bin/env python3
# Copyright 2024 Ubuntu
# See LICENSE file for licensing details.

import logging
import time
from pathlib import Path

import lightkube
import pytest
import yaml
from charmed_kubeflow_chisme.kubernetes import KubernetesResourceHandler
from lightkube import codecs
from lightkube.generic_resource import (
    create_namespaced_resource,
    load_in_cluster_generic_resources,
)
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
CHARM_NAME = METADATA["name"]
RESOURCE_DISPATCHER_CHARM_NAME = "resource-dispatcher"
METACONTROLLER_CHARM_NAME = "metacontroller-operator"
TESTING_LABELS = ["user.kubeflow.org/enabled"]
PODDEFAULTS_CRD_TEMPLATE = "./tests/integration/crds/poddefaults.yaml"
PODDEFAULT_FILE = yaml.safe_load(Path("./src/templates/poddefault.yaml").read_text())
PODDEFAULT_NAME = PODDEFAULT_FILE["metadata"]["name"]
NAMESPACE_FILE = "./tests/integration/namespace.yaml"


PodDefault = create_namespaced_resource("kubeflow.org", "v1alpha1", "PodDefault", "poddefaults")


def _safe_load_file_to_text(filename: str) -> str:
    """Returns the contents of filename if it is an existing file, else it returns filename."""
    try:
        text = Path(filename).read_text()
    except FileNotFoundError:
        text = filename
    return text


def delete_all_from_yaml(yaml_text: str, lightkube_client: lightkube.Client = None):
    """Deletes all k8s resources listed in a YAML file via lightkube.

    Args:
        yaml_file (str or Path): Either a string filename or a string of valid YAML.  Will attempt
                                 to open a filename at this path, failing back to interpreting the
                                 string directly as YAML.
        lightkube_client: Instantiated lightkube client or None
    """

    if lightkube_client is None:
        lightkube_client = lightkube.Client()

    for obj in codecs.load_all_yaml(yaml_text):
        lightkube_client.delete(type(obj), obj.metadata.name)


@pytest.fixture(scope="session")
def lightkube_client() -> lightkube.Client:
    client = lightkube.Client(field_manager=CHARM_NAME)
    return client


def deploy_k8s_resources(template_files: str):
    lightkube_client = lightkube.Client(field_manager=CHARM_NAME)
    k8s_resource_handler = KubernetesResourceHandler(
        field_manager=CHARM_NAME, template_files=template_files, context={}
    )
    load_in_cluster_generic_resources(lightkube_client)
    k8s_resource_handler.apply()


@pytest.fixture(scope="session")
def namespace(lightkube_client: lightkube.Client):
    yaml_text = _safe_load_file_to_text(NAMESPACE_FILE)
    yaml_rendered = yaml.safe_load(yaml_text)
    for label in TESTING_LABELS:
        yaml_rendered["metadata"]["labels"][label] = "true"
    obj = codecs.from_dict(yaml_rendered)
    lightkube_client.apply(obj)

    yield obj.metadata.name

    delete_all_from_yaml(yaml_text, lightkube_client)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the ngc-integrator charm and deploy it together with related charms."""

    deploy_k8s_resources([PODDEFAULTS_CRD_TEMPLATE])

    # Build and deploy charm from local source folder
    built_charm_path = await ops_test.build_charm(".")

    # Deploy the charm and wait for active/idle status
    await ops_test.model.deploy(
        entity_url=built_charm_path,
        application_name=CHARM_NAME,
        trust=True,
    )

    await ops_test.model.wait_for_idle(
        apps=[CHARM_NAME], status="active", raise_on_blocked=True, timeout=300
    )

    # Deploy resource-dispatcher charm and related charms
    await ops_test.model.deploy(
        entity_url=METACONTROLLER_CHARM_NAME,
        channel="latest/edge",
        trust=True,
    )
    await ops_test.model.wait_for_idle(
        apps=[METACONTROLLER_CHARM_NAME],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=120,
    )

    await ops_test.model.deploy(
        entity_url=RESOURCE_DISPATCHER_CHARM_NAME,
        channel="latest/edge",
        trust=True,
    )

    await ops_test.model.wait_for_idle(
        apps=[RESOURCE_DISPATCHER_CHARM_NAME],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=1200,
        idle_period=60,
    )

    await ops_test.model.relate(
        f"{CHARM_NAME}:pod-defaults", f"{RESOURCE_DISPATCHER_CHARM_NAME}:pod-defaults"
    )

    await ops_test.model.wait_for_idle(
        apps=[CHARM_NAME, RESOURCE_DISPATCHER_CHARM_NAME],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=300,
    )


@pytest.mark.abort_on_fail
async def test_new_user_namespace_has_poddefault(
    ops_test: OpsTest, lightkube_client: lightkube.Client, namespace: str
):
    """Test that the Kubeflow user namespace has the PodDefault object."""
    time.sleep(30)  # sync can take up to 10 seconds for reconciliation loop to trigger

    pod_default = lightkube_client.get(PodDefault, PODDEFAULT_NAME, namespace=namespace)
    assert pod_default is not None
