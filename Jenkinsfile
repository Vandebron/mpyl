pipeline {
    agent { node { label 'jenkins-test-dind-agent' } }

    stages {
        stage('Initialise') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                echo "Running dagster..."
                sh "pipenv install -d --skip-lock"
                sh "pipenv run run"
            }
        }
    }
}