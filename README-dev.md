## Run tests and checks
To run linting (`pylint`), type checking (`mypy`) and testing (`pytest`) in one go, run: 
```shell
pipenv run validate
```

## Creating a pull request build
After every push, if all validation passes, a test release is pushed to https://test.pypi.org/project/mpyl/. The naming of the version follows follows a '<pr_number><build_number>' pattern.

A pull request build can be used in `Pipfile` as follows:
```toml
[[source]]
url = "https://test.pypi.org/simple"
verify_ssl = false
name = "test"

[packages]
mpyl = { version = "==28.post403", index = "test" }
```

## Creating a new release
Using the [Github cli](https://cli.github.com/), run:
```shell
gh release create 0.0.2 --generate-notes
```
which will trigger a build and release to https://pypi.org/project/mpyl/

## Troubleshooting Python setup

1. Check if you're in the correct `venv`
   To check this, run first:
    ```shell
    pipenv shell
    ```
   Then check if the correct virtual environment (named `pympl`) is launched.
2. Check your `bashrc` (or `zshrc`) if you have any overrides of environmental variables like `PIPENV_PIPFILE`. If so, remove those, source your bash config and try Step 1. again
3. To see if everything is running as intended, execute
    ```shell
    pipenv run test
    ```
   which should now succeed.
