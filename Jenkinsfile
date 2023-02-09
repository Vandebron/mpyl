pipeline {
    agent { dockerfile true }

    stages {
        stage('Initialise') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                echo "Running dagster..."
                sh "pipenv run run"
            }
        }
    }
}