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
                echo "Running dagit..."
                sh "dagit --workspace ./workspace.yml"
            }
        }
    }
}