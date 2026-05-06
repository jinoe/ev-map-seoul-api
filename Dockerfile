# 1. 파이썬 가벼운 버전(slim)을 베이스 이미지로 사용
FROM python:3.10-slim

# 2. 컨테이너 내부에서 작업할 기본 폴더 세팅
WORKDIR /app

# 3. 환경 변수 설정 (파이썬이 출력 로그를 버퍼링 없이 즉시 터미널에 뿌리도록 설정)
ENV PYTHONUNBUFFERED=1

# 4. 의존성 패키지 목록 파일 복사 및 설치
# (가상환경 .venv 폴더 자체를 복사하는 것보다 requirements.txt로 설치하는 것이 도커 표준입니다.)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. 프로젝트 전체 소스 코드를 컨테이너 내부로 복사
COPY . .

# 6. 도커 컨테이너가 외부로 노출할 포트 지정 (FastAPI용 400번 포트)
EXPOSE 400

# 7. 컨테이너가 켜질 때 실행할 명령어
# 외부 접속을 받으려면 --host를 반드시 0.0.0.0으로 열어야 합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "400"]