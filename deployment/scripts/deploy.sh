#!/bin/bash

# Two Very Auto v3.0 - 배포 스크립트
# 환경별 자동 배포 및 롤백 지원

set -euo pipefail

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="$PROJECT_ROOT/docker"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

# 환경 변수 기본값
ENVIRONMENT="${ENVIRONMENT:-development}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io/your-org/two-very-auto}"
KUBECTL_CONTEXT="${KUBECTL_CONTEXT:-}"
NAMESPACE="${NAMESPACE:-two-very-auto-${ENVIRONMENT}}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"

# 도움말 출력
show_help() {
    cat << EOF
Two Very Auto v3.0 배포 스크립트

사용법: $0 [옵션]

옵션:
    -e, --environment ENVIRONMENT    배포 환경 (development, staging, production)
    -t, --tag TAG                   Docker 이미지 태그
    -r, --registry REGISTRY         Docker 레지스트리 URL
    -k, --kube-context CONTEXT      kubectl 컨텍스트
    -n, --namespace NAMESPACE       Kubernetes 네임스페이스
    -d, --dry-run                   실제 배포 없이 검증만 실행
    -s, --skip-tests                테스트 건너뛰기
    --no-rollback                   실패 시 롤백 비활성화
    --rollback VERSION              특정 버전으로 롤백
    --status                        배포 상태 확인
    -h, --help                      이 도움말 출력

예제:
    $0 -e production -t v1.2.3
    $0 --environment staging --dry-run
    $0 --rollback v1.2.2
    $0 --status

환경 변수:
    ENVIRONMENT                     배포 환경
    IMAGE_TAG                       Docker 이미지 태그
    DOCKER_REGISTRY                 Docker 레지스트리
    KUBECTL_CONTEXT                 kubectl 컨텍스트
    DRY_RUN                        드라이런 모드
    SKIP_TESTS                     테스트 건너뛰기

EOF
}

# 명령행 인수 파싱
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--registry)
                DOCKER_REGISTRY="$2"
                shift 2
                ;;
            -k|--kube-context)
                KUBECTL_CONTEXT="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --no-rollback)
                ROLLBACK_ON_FAILURE="false"
                shift
                ;;
            --rollback)
                ROLLBACK_VERSION="$2"
                shift 2
                ;;
            --status)
                STATUS_ONLY="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 전제 조건 확인
check_prerequisites() {
    log_info "전제 조건 확인 중..."

    # 필수 도구 확인
    local tools=("docker" "kubectl" "jq")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool 이 설치되지 않음"
            exit 1
        fi
    done

    # Docker 데몬 확인
    if ! docker info &> /dev/null; then
        log_error "Docker 데몬이 실행 중이지 않음"
        exit 1
    fi

    # kubectl 컨텍스트 설정
    if [[ -n "$KUBECTL_CONTEXT" ]]; then
        kubectl config use-context "$KUBECTL_CONTEXT"
    fi

    # Kubernetes 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes 클러스터에 연결할 수 없음"
        exit 1
    fi

    log_success "모든 전제 조건 충족"
}

# 환경별 설정 로드
load_environment_config() {
    log_info "환경 설정 로드 중: $ENVIRONMENT"

    local config_file="$DEPLOYMENT_DIR/config/$ENVIRONMENT.env"
    
    if [[ -f "$config_file" ]]; then
        set -a
        source "$config_file"
        set +a
        log_success "환경 설정 로드 완료: $config_file"
    else
        log_warn "환경 설정 파일 없음: $config_file"
    fi

    # 네임스페이스 업데이트
    NAMESPACE="two-very-auto-${ENVIRONMENT}"
    
    # 레지스트리 인증 확인
    if [[ "$DOCKER_REGISTRY" == ghcr.io/* ]]; then
        if [[ -z "${GITHUB_TOKEN:-}" ]]; then
            log_error "GITHUB_TOKEN 환경변수가 필요함"
            exit 1
        fi
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin
    fi
}

# 이미지 빌드 및 푸시
build_and_push_images() {
    if [[ "$SKIP_TESTS" == "false" ]]; then
        log_info "테스트 실행 중..."
        
        # Python 테스트
        if command -v python3 &> /dev/null; then
            cd "$PROJECT_ROOT"
            python3 -m pytest python/tests/ -v || {
                log_error "Python 테스트 실패"
                exit 1
            }
        fi
        
        log_success "테스트 통과"
    fi

    log_info "Docker 이미지 빌드 중..."

    # 웹 애플리케이션 이미지 빌드
    local web_image="$DOCKER_REGISTRY-web:$IMAGE_TAG"
    log_info "웹 이미지 빌드: $web_image"
    
    docker build -t "$web_image" -f "$DOCKER_DIR/Dockerfile.web" "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        docker push "$web_image"
        log_success "웹 이미지 푸시 완료: $web_image"
    fi

    # AI 엔진 이미지 빌드
    local ai_image="$DOCKER_REGISTRY-ai:$IMAGE_TAG"
    log_info "AI 이미지 빌드: $ai_image"
    
    docker build -t "$ai_image" -f "$DOCKER_DIR/Dockerfile.ai" "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        docker push "$ai_image"
        log_success "AI 이미지 푸시 완료: $ai_image"
    fi
}

# Kubernetes 매니페스트 준비
prepare_manifests() {
    log_info "Kubernetes 매니페스트 준비 중..."

    local manifest_dir="$DEPLOYMENT_DIR/kubernetes"
    local temp_manifest="/tmp/k8s-manifest-$ENVIRONMENT.yaml"

    # 매니페스트 템플릿 복사 및 치환
    if [[ -f "$manifest_dir/$ENVIRONMENT.yml" ]]; then
        cp "$manifest_dir/$ENVIRONMENT.yml" "$temp_manifest"
    else
        log_error "매니페스트 파일 없음: $manifest_dir/$ENVIRONMENT.yml"
        exit 1
    fi

    # 변수 치환
    sed -i.bak \
        -e "s|{{IMAGE_TAG}}|$IMAGE_TAG|g" \
        -e "s|{{DOCKER_REGISTRY}}|$DOCKER_REGISTRY|g" \
        -e "s|{{NAMESPACE}}|$NAMESPACE|g" \
        -e "s|{{ENVIRONMENT}}|$ENVIRONMENT|g" \
        "$temp_manifest"

    rm "$temp_manifest.bak" 2>/dev/null || true

    echo "$temp_manifest"
}

# Kubernetes 배포 실행
deploy_to_kubernetes() {
    local manifest_file="$1"
    
    log_info "Kubernetes 배포 실행 중..."

    # 네임스페이스 생성 (존재하지 않는 경우)
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        if [[ "$DRY_RUN" == "false" ]]; then
            kubectl create namespace "$NAMESPACE"
            log_success "네임스페이스 생성: $NAMESPACE"
        else
            log_info "[DRY-RUN] 네임스페이스 생성 예정: $NAMESPACE"
        fi
    fi

    # 배포 실행
    if [[ "$DRY_RUN" == "false" ]]; then
        kubectl apply -f "$manifest_file" -n "$NAMESPACE"
        log_success "Kubernetes 배포 완료"
    else
        log_info "[DRY-RUN] Kubernetes 배포 시뮬레이션:"
        kubectl apply --dry-run=client -f "$manifest_file" -n "$NAMESPACE"
    fi
}

# 배포 상태 확인
wait_for_deployment() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi

    log_info "배포 상태 확인 중..."

    local deployments=("two-very-auto-web" "two-very-auto-ai")
    
    for deployment in "${deployments[@]}"; do
        log_info "배포 대기 중: $deployment"
        
        if kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=600s; then
            log_success "$deployment 배포 완료"
        else
            log_error "$deployment 배포 실패"
            return 1
        fi
    done

    # 헬스 체크
    log_info "헬스 체크 실행 중..."
    sleep 30  # 서비스가 완전히 시작될 시간 제공

    local service_url
    if [[ "$ENVIRONMENT" == "production" ]]; then
        service_url="https://two-very-auto.com/api/health"
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        service_url="https://staging.two-very-auto.com/api/health"
    else
        # 포트 포워딩을 통한 로컬 헬스 체크
        kubectl port-forward service/two-very-auto-web-service 8080:80 -n "$NAMESPACE" &
        local port_forward_pid=$!
        sleep 5
        service_url="http://localhost:8080/api/health"
    fi

    local max_attempts=12
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$service_url" &> /dev/null; then
            log_success "헬스 체크 통과"
            
            # 포트 포워딩 정리
            if [[ "$ENVIRONMENT" == "development" && -n "${port_forward_pid:-}" ]]; then
                kill $port_forward_pid 2>/dev/null || true
            fi
            
            return 0
        fi

        log_warn "헬스 체크 실패 (시도 $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    log_error "헬스 체크 최종 실패"
    
    # 포트 포워딩 정리
    if [[ "$ENVIRONMENT" == "development" && -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid 2>/dev/null || true
    fi
    
    return 1
}

# 롤백 실행
perform_rollback() {
    local rollback_version="${1:-}"
    
    log_warn "롤백 실행 중..."

    if [[ -n "$rollback_version" ]]; then
        log_info "특정 버전으로 롤백: $rollback_version"
        
        # 특정 버전으로 이미지 태그 변경
        kubectl set image deployment/two-very-auto-web \
            web="$DOCKER_REGISTRY-web:$rollback_version" \
            -n "$NAMESPACE"
        
        kubectl set image deployment/two-very-auto-ai \
            ai-engine="$DOCKER_REGISTRY-ai:$rollback_version" \
            -n "$NAMESPACE"
    else
        log_info "이전 버전으로 롤백"
        
        # 이전 리비전으로 롤백
        kubectl rollout undo deployment/two-very-auto-web -n "$NAMESPACE"
        kubectl rollout undo deployment/two-very-auto-ai -n "$NAMESPACE"
    fi

    # 롤백 완료 대기
    kubectl rollout status deployment/two-very-auto-web -n "$NAMESPACE"
    kubectl rollout status deployment/two-very-auto-ai -n "$NAMESPACE"
    
    log_success "롤백 완료"
}

# 배포 상태 확인
show_deployment_status() {
    log_info "배포 상태 확인: $ENVIRONMENT"

    echo "=== 네임스페이스 정보 ==="
    kubectl get namespace "$NAMESPACE" 2>/dev/null || echo "네임스페이스 없음: $NAMESPACE"

    echo -e "\n=== 배포 상태 ==="
    kubectl get deployments -n "$NAMESPACE" 2>/dev/null || echo "배포 없음"

    echo -e "\n=== 파드 상태 ==="
    kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || echo "파드 없음"

    echo -e "\n=== 서비스 상태 ==="
    kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "서비스 없음"

    echo -e "\n=== 인그레스 상태 ==="
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "인그레스 없음"

    echo -e "\n=== 최근 이벤트 ==="
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10 2>/dev/null || echo "이벤트 없음"
}

# 정리 작업
cleanup() {
    local exit_code=$?
    
    # 임시 파일 정리
    rm -f /tmp/k8s-manifest-*.yaml
    
    if [[ $exit_code -ne 0 ]]; then
        log_error "배포 중 오류 발생 (종료 코드: $exit_code)"
        
        if [[ "$ROLLBACK_ON_FAILURE" == "true" && "$DRY_RUN" == "false" ]]; then
            log_warn "자동 롤백 실행 중..."
            perform_rollback || log_error "롤백도 실패"
        fi
    fi
    
    exit $exit_code
}

# 메인 배포 함수
main() {
    # 시그널 핸들러 등록
    trap cleanup EXIT INT TERM

    log_info "Two Very Auto v3.0 배포 시작"
    log_info "환경: $ENVIRONMENT, 태그: $IMAGE_TAG, 드라이런: $DRY_RUN"

    # 상태 확인만 하는 경우
    if [[ "${STATUS_ONLY:-false}" == "true" ]]; then
        show_deployment_status
        exit 0
    fi

    # 롤백만 하는 경우
    if [[ -n "${ROLLBACK_VERSION:-}" ]]; then
        check_prerequisites
        load_environment_config
        perform_rollback "$ROLLBACK_VERSION"
        exit 0
    fi

    # 일반 배포 프로세스
    check_prerequisites
    load_environment_config
    build_and_push_images

    local manifest_file
    manifest_file=$(prepare_manifests)

    deploy_to_kubernetes "$manifest_file"

    if ! wait_for_deployment; then
        log_error "배포 검증 실패"
        exit 1
    fi

    log_success "배포 성공 완료!"
    log_info "환경: $ENVIRONMENT"
    log_info "이미지 태그: $IMAGE_TAG"
    log_info "네임스페이스: $NAMESPACE"
    
    # 배포 정보 출력
    show_deployment_status
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi