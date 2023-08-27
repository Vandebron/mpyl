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

## ..code style

We use the [black formatter](https://black.readthedocs.io/en/stable/getting_started.html) in our codebase.
Check the instructions on how to set it up for your
IDE [here](https://black.readthedocs.io/en/stable/integrations/editors.html).

## ..create a new release

§§1. Check the latest [release number](https://github.com/Vandebron/mpyl/releases) 
2. Add the new release number to [mpyl/cli/releases/releases.txt](src/mpyl/cli/releases/releases.txt)
3. Create a new release notes file in [releases/notes/](releases/notes/) and name it `<version>.md`
Noteworthy changes should be added to this file. Think: new cli commands, new features, breaking changes, upgrade 
instructions, etc.
4. Merge all PRs that you want to include in the release to `main`
5. Using the [Github cli](https://cli.github.com/), run: 
   ```shell
   gh release create <version> --generate-notes
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

## ..installing a test release of MPyL
Test versions of MPyL are published for every pull request to [test pypi](https://test.pypi.org/project/mpyl/).
To install a test release, run:
```shell
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mpyl==<version>
```

## ..running the mpyl sourcecode against another repository

For a shorter feedback loop, you can run the mpyl sourcecode against another repository.
To test the mpyl sourcecode against the peculiarities of your own repository, you can run the following command:

```shell
PIPENV_PIPFILE=/<absolute_path_to_mpyl_repo>/Pipfile pipenv run cli-ext build status
```
Assign PIPENV_PIPFILE to the absolute path of your Pipfile and run the command.
⚠️Note that an `.env` file needs to be present in the root if this repository, containing the following variable:

```shell
PYTHONPATH=/<absolute_path_to_mpyl_repo>/src
```