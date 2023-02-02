pipeline {
    agent { docker { image 'python:3.9.16-slim-buster' } }

    environment {
        PYENV_SHELL="bash"
        PIPENV_YES="true"
        PIPENV_NOSPIN="YES"
    }

    stages {
        stage('Initialise') {
            steps {
                checkout scm
                echo "Installing pipenv..."
                sh "pip3 install pipenv --user"
            }
        }
        stage('Build') {
            steps {
                echo "Installing dependencies..."
                sh "pipenv install --skip-lock"
                echo "Building project..."
                sh "pipenv run build"
                echo "Running dagit..."
                sh "dagit --workspace ./workspace.yml"
            }
        }
    }
}