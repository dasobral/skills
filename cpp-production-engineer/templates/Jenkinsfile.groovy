// ── Jenkins Pipeline — C++ Production Build ───────────────────────────────────
// Stage order (mandatory per coding-standards.md §9):
//   Checkout → Build → Test → Static Analysis → Archive
//
// Requirements:
//   - SonarQube scanner configured in Jenkins global tools as "SonarQube"
//   - SonarQube server configured in Jenkins system settings as "sonarqube"
//   - Credentials stored in Jenkins credential store (never hard-coded here)
// ─────────────────────────────────────────────────────────────────────────────

pipeline {
    agent any

    environment {
        BUILD_DIR   = 'build'
        SONAR_TOKEN = credentials('sonarqube-token')  // Jenkins credential binding
    }

    stages {

        // ── Stage 1: Checkout ───────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ── Stage 2: Build ──────────────────────────────────────────────────
        stage('Build') {
            steps {
                sh """
                    cmake -S . -B ${BUILD_DIR} \
                        -DCMAKE_BUILD_TYPE=Debug \
                        -DENABLE_COVERAGE=ON
                    cmake --build ${BUILD_DIR} --parallel \$(nproc)
                """
            }
        }

        // ── Stage 3: Test ───────────────────────────────────────────────────
        stage('Test') {
            steps {
                sh """
                    cd ${BUILD_DIR}
                    ctest --output-on-failure --parallel \$(nproc)
                """
            }
            post {
                always {
                    // Publish JUnit test results
                    junit allowEmptyResults: true,
                          testResults: "${BUILD_DIR}/**/*test-results*.xml"
                }
            }
        }

        // ── Stage 4: Static Analysis (SonarQube) ───────────────────────────
        // SonarQube Blocker issues FAIL the build (abortPipeline: true).
        // Critical issues are at minimum WARNING findings.
        // NEVER suppress or ignore Blocker findings.
        stage('Static Analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh """
                        sonar-scanner \
                            -Dsonar.projectKey=<<PROJECT_KEY>> \
                            -Dsonar.sources=src \
                            -Dsonar.tests=tests \
                            -Dsonar.cfamily.compile-commands=${BUILD_DIR}/compile_commands.json \
                            -Dsonar.cfamily.gcov.reportsPath=${BUILD_DIR} \
                            -Dsonar.login=${SONAR_TOKEN}
                    """
                }
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ── Stage 5: Archive ────────────────────────────────────────────────
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: "${BUILD_DIR}/src/**/*.a,${BUILD_DIR}/src/**/*.so,${BUILD_DIR}/src/**/<<EXECUTABLE_NAME>>",
                                 allowEmptyArchive: true
            }
        }
    }

    post {
        failure {
            // Notify on failure (configure as appropriate for your environment)
            echo "Build failed — investigate SonarQube quality gate or test failures."
        }
        always {
            cleanWs()
        }
    }
}
