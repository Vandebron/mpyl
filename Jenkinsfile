pipeline {
    agent {
      docker {
        image 'python:3'
      }
    }

//     environment {
// //         PYENV_ROOT="$HOME/.pyenv"
// //         PYENV_SHELL="bash"
// //         PIPENV_YES="true"
// //         PIPENV_NOSPIN="YES"
//     }

    stages {
        stage('Initialise') {
            steps {
                checkout scm
            }
        }
        stage('Build') {
            steps {
                sh 'python --version'
                sh "pipenv install --skip-lock"
                sh "pipenv run build"
                sh "dagit --workspace ./workspace.yml"
            }
        }
    }
}