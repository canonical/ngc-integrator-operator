#!/usr/bin/env python3
# Copyright 2024 Ubuntu
# See LICENSE file for licensing details.

import logging
from contextlib import nullcontext as does_not_raise
from pathlib import Path

import pytest
import tenacity
import yaml
from charmed_kubeflow_chisme.kubernetes import (
    KubernetesResourceHandler,
    create_charm_default_labels,
)
from lightkube.generic_resource import create_namespaced_resource
from lightkube.resources.core_v1 import Namespace
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

ADMISSION_WEBHOOK_CHARM_NAME = "admission-webhook"
METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
CHARM_NAME = METADATA["name"]
RESOURCE_DISPATCHER_CHARM_NAME = "resource-dispatcher"
METACONTROLLER_CHARM_NAME = "metacontroller-operator"
PODDEFAULT_FILE = yaml.safe_load(Path("./src/templates/poddefault.yaml").read_text())
PODDEFAULT_NAME = PODDEFAULT_FILE["metadata"]["name"]
NAMESPACE_FILE = "./tests/integration/namespace.yaml"
NAMESPACE_NAME = yaml.safe_load(Path(NAMESPACE_FILE).read_text())["metadata"]["name"]

PodDefault = create_namespaced_resource("kubeflow.org", "v1alpha1", "PodDefault", "poddefaults")


@pytest.fixture(scope="module")
def k8s_resource_handler(ops_test: OpsTest) -> KubernetesResourceHandler:
    k8s_resource_handler = KubernetesResourceHandler(
        field_manager=CHARM_NAME,
        template_files=[NAMESPACE_FILE],
        labels=create_charm_default_labels(
            application_name=CHARM_NAME,
            model_name=ops_test.model.name,
            scope="namespace",
        ),
        resource_types={Namespace},
        context={},
    )
    return k8s_resource_handler


@pytest.fixture(scope="module")
def namespace(k8s_resource_handler: KubernetesResourceHandler):
    k8s_resource_handler.apply()
    yield NAMESPACE_NAME

    k8s_resource_handler.delete()


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the ngc-integrator charm and deploy it together with related charms."""

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

    # Deploy admission webhook to get the poddefaults CRD
    await ops_test.model.deploy(
        entity_url=ADMISSION_WEBHOOK_CHARM_NAME,
        channel="latest/edge",
        trust=True,
    )
    await ops_test.model.wait_for_idle(
        apps=[ADMISSION_WEBHOOK_CHARM_NAME],
        status="active",
        raise_on_blocked=False,
        raise_on_error=True,
        timeout=120,
    )

    await ops_test.model.deploy(
        entity_url=METACONTROLLER_CHARM_NAME,
        channel="latest/edge",
        trust=True,
    )
    await ops_test.model.wait_for_idle(
        apps=[METACONTROLLER_CHARM_NAME],
        status="active",
        raise_on_blocked=False,
        raise_on_error=True,
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
        raise_on_error=True,
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
        raise_on_error=True,
        timeout=300,
    )


@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=15),
    stop=tenacity.stop_after_delay(30),
    reraise=True,
)
@pytest.mark.abort_on_fail
async def test_new_user_namespace_has_poddefault(
    ops_test: OpsTest, k8s_resource_handler: KubernetesResourceHandler, namespace: str
):
    """Test that the Kubeflow user namespace has the PodDefault with the expected attributes."""
    with does_not_raise():
        pod_default = k8s_resource_handler.lightkube_client.get(
            PodDefault, PODDEFAULT_NAME, namespace=namespace
        )

    name = pod_default.get("metadata", {}).get("name", {})
    assert name == PODDEFAULT_FILE["metadata"]["name"]

    selector_label = pod_default.get("spec", {}).get("selector", {}).get("matchLabels")
    assert selector_label == PODDEFAULT_FILE["spec"]["selector"]["matchLabels"]
