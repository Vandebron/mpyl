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
                sh "dagster job execute -f mpyl-test-runner.py"
            }
        }
    }
}