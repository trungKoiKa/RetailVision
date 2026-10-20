# Edge giả cho demo: chỉ cần paho-mqtt, không cần camera hay model.
# Build từ gốc repo: docker build -f deploy/server/fake-edge.Dockerfile .
FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home rv && pip install --no-cache-dir paho-mqtt==2.1.0
WORKDIR /app
COPY edge/retailvision ./retailvision
USER rv
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "retailvision.tools.fake_publisher"]
