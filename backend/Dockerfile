# Build: docker build -t retailvision-backend backend/
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
# lớp riêng cho phụ thuộc để lần build sau không tải lại khi chỉ sửa mã
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q -DskipTests package && cp target/retailvision-backend-*.jar /build/app.jar

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 --no-create-home rv
USER rv
WORKDIR /app
COPY --from=build /build/app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "/app/app.jar"]
