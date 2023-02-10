pipeline {
    agent { node { label 'jenkins-test-dind-agent' } }

    stages {
        stage('Initialise') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
           environment {
                DOCKER_REGISTRY = credentials('91751de6-20aa-4b12-8459-6e16094a233a')
            }
            steps {
                echo "Running dagster..."
                sh "pipenv install -d --skip-lock"
                sh "pipenv run run"
            }
        }
    }
}