pipeline {
    agent { node { label 'mpyl-dind-agent' } }
    options {
        ansiColor('xterm')
    }
    stages {
        stage('Initialize Parameters') {
            when { expression { return params.BUILD_PARAMS == null || params.BUILD_PARAMS == ""  } }
            steps {
                script {
                    properties([parameters([
                        string(name: 'BUILD_PARAMS', defaultValue: '--all', description: 'Build parameters passed along with the run. Example: --help or --all'),
                        string(name: 'MPYL_CONFIG_BRANCH', defaultValue: 'main', description: 'Branch to use for mpyl_config repository')
                    ])])
                    currentBuild.result = 'NOT_BUILT'
                    currentBuild.description = "Parameters can be set now"
                    currentBuild.displayName = "#${BUILD_NUMBER}-(Parameter load)"
                    echo("The build parameters have been created. Ready for real build.")
                    currentBuild.getRawBuild().getExecutor().interrupt(Result.NOT_BUILT)
                    sleep(1)
                }
            }
        }
        stage('Build') {
           environment {
                DOCKER_REGISTRY = credentials('91751de6-20aa-4b12-8459-6e16094a233a')
                GITHUB_TOKEN = credentials('github-pat-mpyl-vandebronjenkins')
                MPYL_GITHUB_APP_PRIVATE_KEY = credentials('mpyl_pipeline_github_app_private_key')
                SLACK_TOKEN = credentials('JENKINS_MPYL_APP_OAUTH_TOKEN')
                MPYL_JIRA_TOKEN = credentials('MPYL_JIRA_TOKEN')
                AWS_ACCESS_KEY_ID = credentials('AWS_ACCESS_KEY_ID')
                AWS_SECRET_ACCESS_KEY = credentials('AWS_SECRET_ACCESS_KEY')
            }
            steps {
                script {
                    def gitconfig = scm.userRemoteConfigs.getAt(0)
                    git(branch: params.MPYL_CONFIG_BRANCH, credentialsId: gitconfig.getCredentialsId(), url: 'https://github.com/Vandebron/mpyl_config.git')
                    def config = readFile('mpyl_config.yml')
                    git(branch: env.BRANCH_NAME, credentialsId: gitconfig.getCredentialsId(), url: gitconfig.getUrl())
                    sh("rm -rf .git/refs/main")
                    writeFile(file: 'mpyl_config.yml', text: config)
                    withKubeConfig([credentialsId: 'jenkins-rancher-service-account-kubeconfig-test']) {
                        wrap([$class: 'BuildUser']) {
                            sh "pipenv clean"
                            sh "pipenv install --ignore-pipfile --skip-lock --site-packages --index https://test.pypi.org/simple/ 'mpyl==$CHANGE_ID.*'"
                            sh "pipenv install -d --skip-lock"
                            sh "pipenv run mpyl projects lint --all"
                            sh "pipenv run mpyl health"
                            sh "pipenv run mpyl build status"
                            sh "pipenv run run-ci ${params.BUILD_PARAMS}"
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                def testResults = findFiles(glob: "tests/projects/**/*test*/*.xml")
                for (xml in testResults) {
                    touch xml.getPath()
                    junit "${xml.getPath()}"
                }
            }
        }
    }
}
