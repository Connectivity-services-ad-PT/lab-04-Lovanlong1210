# 🗺️ Hướng Dẫn Từng Bước Lab 04 - Đóng gói Docker (Dành cho Team Analytics)

Chào mừng bạn đến với Lab 04! Ở Lab 03, bạn đã tạo ra bộ Test bằng Postman để kiểm thử API Contract. Trong Lab 04 này, mục tiêu của chúng ta là **code một API thật (Service thật)**, sau đó **đóng gói nó vào Docker**, chạy lên và dùng lại bộ Test ở Lab 03 để đảm bảo mọi thứ vẫn xanh (pass).

Dưới đây là hướng dẫn từng bước "cầm tay chỉ việc" để bạn hoàn thành bài Lab này:

---

## Bước 1: Mang "tài sản" từ Lab 03 sang Lab 04

Bạn cần copy các file từ Lab 03 sang đúng thư mục tương ứng ở Lab 04:

1. Copy file `contracts/openapi.yaml` (hoặc `analytics.openapi.yaml`) từ Lab 03 sang mục `contracts/` của Lab 04.
2. Copy thư mục `postman/collections/` (chứa file test JSON của Analytics) từ Lab 03 sang Lab 04.
3. Copy thư mục `postman/environments/` từ Lab 03 sang Lab 04. Đặc biệt lưu ý file `local.postman_environment.json`.

---

## Bước 2: Đổi tên app từ `iot_app` thành `analytics_app`

Mặc định repo Lab 04 đang chứa code mẫu của nhóm IoT (`src/iot_app`). Bạn cần đổi nó thành của nhóm Analytics.

1. Đổi tên thư mục `src/iot_app` thành `src/analytics_app`.
2. Mở file `src/analytics_app/main.py` và sửa code bên trong. Nhiệm vụ của bạn là code bằng Python (FastAPI) các endpoint sao cho khớp với hợp đồng OpenAPI của bạn (ví dụ: `GET /health`, `POST /events`, `GET /alerts`, v.v.)
3. Đảm bảo code của bạn trả về đúng các trường dữ liệu như `eventId`, `status`, `items`... để Postman test có thể **Pass**.

> **Mẹo nhỏ:** Bạn chưa cần kết nối Database phức tạp (TimescaleDB) trong Lab 04. Bạn có thể dùng list/dict trong RAM (biến toàn cục) để lưu tạm dữ liệu (mock data) miễn là API chạy đúng logic Contract!

---

## Bước 3: Cập nhật `Dockerfile`

Mở file `Dockerfile` ở thư mục gốc và sửa lại dòng CMD cuối cùng để nó chạy đúng thư mục `analytics_app`:

**Tìm dòng cuối cùng:**
```dockerfile
CMD ["sh", "-c", "uvicorn iot_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]
```
**Sửa thành:**
```dockerfile
CMD ["sh", "-c", "uvicorn analytics_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]
```

---

## Bước 4: Cập nhật file `.env.example` và `.dockerignore`

- **`.dockerignore`**: File này giúp loại bỏ các file rác không cần đưa vào Docker. Thường đã được cấu hình sẵn (như bỏ qua `node_modules`, `.venv`, `.git`). Bạn không cần sửa nhiều.
- **`.env.example`**: Đây là file mẫu chứa cấu hình. Nếu Analytics của bạn cần biến môi trường nào (ví dụ `AUTH_TOKEN=local-dev-token`, `API_KEY=...`), hãy khai báo vào đây.

---

## Bước 5: Cập nhật các file cấu hình `package.json` và `Makefile`

Bạn cần cập nhật tên collection và environment trong `package.json` để lệnh test chạy đúng.

**Trong `package.json`**, tìm phần `"scripts"` và sửa lại các lệnh test chỉ đến đúng file Postman của Analytics:

```json
"test:local": "newman run postman/collections/FIT4110_lab03_analytics.postman_collection.json -e postman/environments/FIT4110_lab03_local.postman_environment.json -r cli,junit,htmlextra --reporter-junit-export reports/newman-lab04-local.xml --reporter-htmlextra-export reports/newman-lab04-local.html"
```

**Trong `Makefile`**, đổi tên image mặc định trên cùng:
```makefile
IMAGE_NAME ?= fit4110/analytics-service:lab04
CONTAINER_NAME ?= fit4110-analytics-lab04
```

---

## Bước 6: Build Image và Chạy Container

Mở Terminal và gõ lần lượt các lệnh sau:

**1. Build Docker Image:**
```bash
docker build -t fit4110/analytics-service:lab04 .
```
*(Nếu bạn đã cấu hình Makefile, bạn chỉ cần gõ `make build`)*

**2. Chạy Container lên:**
```bash
docker run --rm -d --name fit4110-analytics-lab04 -p 8000:8000 --env-file .env.example fit4110/analytics-service:lab04
```
*(Hoặc gõ `make run-detached`)*

**3. Kiểm tra xem service đã sống chưa:**
Mở trình duyệt hoặc dùng curl:
```bash
curl http://localhost:8000/health
```
Nếu hiện ra JSON `{ "status": "ok", ... }` là bạn đã thành công đóng gói!

---

## Bước 7: Chạy Newman Test đập vào Container

Bây giờ API thật của bạn đang chạy trong Docker ở cổng 8000. Hãy dùng Postman/Newman để kiểm tra xem nó có làm đúng hợp đồng không.

Chạy lệnh:
```bash
npm run test:local
```
*(Lưu ý: Môi trường `local.postman_environment.json` phải có `baseUrl` là `http://localhost:8000`)*

Nếu tất cả các test (Functional, Auth, Negative...) đều xanh rờn (Pass), chúc mừng bạn!

---

## Bước 8: Tag Image và Viết RUN_LOCAL.md

**1. Tag Image theo chuẩn yêu cầu:**
```bash
docker tag fit4110/analytics-service:lab04 ghcr.io/<tên-github-của-bạn>/team-analytics:v0.1.0-team-analytics
```

**2. Viết file `RUN_LOCAL.md`:**
Hãy viết file này ngắn gọn (3-5 bước) để một người không biết gì vào repo cũng biết cách chạy service của bạn bằng Docker. Mở file `RUN_LOCAL.md` và chỉnh sửa lại theo các bước ở **Bước 6**.

---

## Bước 9: Nộp Bài 🚀

Kiểm tra lại xem bạn đã có đủ:
- [ ] `Dockerfile`, `.dockerignore`, `.env.example`
- [ ] `RUN_LOCAL.md`
- [ ] Report HTML/XML trong thư mục `reports/` (sau khi chạy test)
- [ ] Ảnh chụp log màn hình Terminal chạy container.

Commit và Push lên GitHub!

```bash
git add .
git commit -m "lab04: init analytics service docker packaging and test reports"
git push
```

Chúc bạn hoàn thành Lab 04 rực rỡ! 🎯
