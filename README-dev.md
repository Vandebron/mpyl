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