# Developer instructions

## ..run example pipeline

1. Install dependencies
    ```shell
    pipenv install -d
    ```
2. Run the Dagit UI
    ```shell
    dagit --workspace ./workspace.yml 
    ```

## ..run tests and checks
To run linting (`pylint`), type checking (`mypy`) and testing (`pytest`) in one go, run:
```shell
pipenv run validate
```
## ..create a pull request build
After every push, if all validation passes, a test release is pushed to https://test.pypi.org/project/mpyl/.
The naming of the version follows a `<pr_number>.<build_number>` pattern.

A pull request build can be used in `Pipfile` via
```shell
pipenv install --index https://test.pypi.org/simple/ mpyl==<PR_NUMBER>.*
```
Resulting in:
```toml
[[source]]
url = "https://test.pypi.org/simple"
verify_ssl = false
name = "test"

[packages]
mpyl = { version = "==28.403", index = "test" }
```
## ..create a new release
Using the [Github cli](https://cli.github.com/), run:
```shell
gh release create 0.0.2 --generate-notes
```
which will trigger a build and release to https://pypi.org/project/mpyl/

## ..troubleshoot Python setup

1. Check if you're in the correct `venv`
   To check this, run first:
    ```shell
    pipenv shell
    ```
   Then check if the correct virtual environment (named `pympl`) is launched.
2. Check your `bashrc` (or `zshrc`) if you have any overrides of environmental variables like `PIPENV_PIPFILE`. If so,
   remove those, source your bash config and try Step 1. again
3. To see if everything is running as intended, execute
    ```shell
    pipenv run test
    ```
   which should now succeed.