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
The entrypoint in the PodDefault, composed of the `command` and `args` values, is a `jupyter lab` command. The `args` values consist of flags that are only compatible with the version of `jupyter lab` that gets installed by the NGC container image that we support, any change on that version could mean a change in those flags.
Check the flags for the `jupyter lab` version in the version of the NGC container image that we are upgrading to by doing:
```
docker run -it <NGC image:targeted version> bash -c "jupyter lab --help-all"
```
<!-- You may want to include any contribution/style guidelines in this document>
