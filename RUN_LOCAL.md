# RUN_LOCAL.md – Hướng dẫn chạy Lab 04 (Analytics Service)

Tài liệu này giúp người khác clone repo sạch và chạy lại service Analytics (A5) trong Docker.

---

## 1. Clone repo

```bash
git clone <repo-url>
cd lab-04-tuan9242
```

---

## 2. Cài dependencies cho Newman/Prism/Spectral

```bash
npm install
```

---

## 3. Build Docker image

```bash
docker build -t fit4110/analytics-service:lab04 .
```

---

## 4. Run container

```bash
docker run --rm -d \
  --name fit4110-analytics-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/analytics-service:lab04
```

Mở terminal khác, kiểm tra:

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "analytics-service",
  "time": "2026-06-02T03:00:00Z"
}
```

---

## 5. Chạy Newman test trên container

Để chạy toàn bộ bài test hợp đồng trên Postman:

```bash
npm run test:local
```

Report sinh tại:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

---

## 6. Dừng container

Vì chúng ta chạy với cờ `-d` (detached), hãy dừng nó bằng lệnh:

```bash
docker stop fit4110-analytics-lab04
```

---

## 7. Lệnh nhanh (Makefile)

Nếu có cài sẵn `make`, bạn có thể dùng các lệnh:

```bash
make build
make run-detached
make test-local
make stop
```
