# Contributing

To make contributions to this charm, you'll need a working [development setup](https://juju.is/docs/sdk/dev-setup).

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

## Testing

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

```shell
tox run -e format        # update your code according to linting rules
tox run -e lint          # code style
tox run -e static        # static type checking
tox run -e unit          # unit tests
tox run -e integration   # integration tests
tox                      # runs 'format', 'lint', 'static', and 'unit' environments
```

## Build the charm

Build the charm in this git repository using:

```shell
charmcraft pack
```

## Upgrading
This charm follows the Charmed Kubeflow versioning with the channel ckf-1.x/<risk> for Kubeflow 1.x versions.
On upgrades, the PodDefault yaml in `/src/templatest/poddefault.yaml` should be upgraded if needed to work with the corresponding Kubeflow Notebooks version.
The entrypoint in the PodDefault, composed of the `command` and `args` values, is a jupyter lab command. A version of Kubeflow Notebook
images contains a pinned version of jupyter, so the command might change with a change in the jupyter version.
<!-- You may want to include any contribution/style guidelines in this document>
