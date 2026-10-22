# ClientBridge

**Sipariş Senkronizasyonu ve Entegrasyon İzleme Paneli**

ClientBridge, NovaShop Commerce üzerinden gelen sipariş webhook'larını alan, siparişleri PostgreSQL veritabanına kaydeden, arka plan worker'ları aracılığıyla CRM sistemine aktaran ve uygulamanın sağlık durumunu izleyen bir entegrasyon uygulamasıdır.

React tabanlı kullanıcı arayüzü, FastAPI backend, PostgreSQL veritabanı ve arka plan işleme yapısını bir araya getirir. Proje; güvenilir asenkron işleme, yinelenen webhook kontrolü, hata yönetimi, yeniden deneme ve worker kurtarma mekanizmalarına odaklanır.

## Ekran Görüntüleri

### Dashboard

![ClientBridge Dashboard](docs/images/dashboard.png)

### Siparişler ve Aktivite Özeti

![ClientBridge Siparişler ve Aktivite](docs/images/orders-activity.png)

## Özellikler

- **Sipariş takibi:** Siparişlerin durumlarını ve ilgili bilgileri görüntüleme.
- **Asenkron işleme:** Webhook isteğini kabul ettikten sonra CRM senkronizasyonunu arka planda yürütme.
- **Kalıcı kayıt:** Siparişleri işleme başlamadan önce PostgreSQL veritabanına kaydetme.
- **Webhook idempotency:** Aynı siparişin aynı kayıtlı verilerle tekrar gönderilmesinde `202 Accepted`, kayıtlı verilerle çelişen bir istek gönderilmesinde `409 Conflict` yanıtı verme.
- **Worker koordinasyonu:** Birden fazla worker'ın siparişleri eş zamanlı almasını önlemeye yardımcı olmak için `SELECT ... FOR UPDATE SKIP LOCKED` kullanma.
- **Retry mekanizması:** HTTP `429`, HTTP `5xx` ve timeout gibi geçici hatalarda yapılandırılmış yeniden deneme uygulama.
- **Recovery mekanizması:** Uygun durumdaki eski işlemleri yeniden işlenebilir hâle getirme.
- **Lease koruması:** İşlem sahipliğini kaybetmiş eski worker'ların güncel kayıtları değiştirmesini önlemeye yardımcı olma.
- **Sistem sağlığı:** Veritabanı, CRM erişilebilirliği ve worker heartbeat durumlarını kontrol etme.
- **Docker Compose:** Veritabanı, migrasyon, API ve worker servislerini birlikte çalıştırma.
- **Otomatik testler:** pytest testleri ve GitHub Actions CI iş akışı.

## Proje Mimarisi

```text
NovaShop Commerce
        |
        | Order Webhook
        v
   FastAPI Backend
        |
        | Siparişi doğrula ve kaydet
        | HTTP 202 döndür
        v
    PostgreSQL
        |
        v
 Background Worker
        |
        | Idempotency-Key ile CRM isteği
        v
      Mock CRM
        |
        +---- Başarılı ------> SYNCED
        |
        +---- Geçici hata ---> Retry
        |
        +---- Retry sınırı --> FAILED
```

## Sipariş İşleme Akışı

1. API, sipariş webhook isteğini alır ve doğrular.
2. Sipariş, PostgreSQL veritabanına `PENDING` durumuyla kaydedilir.
3. Yeni sipariş kabul edildiğinde API `202 Accepted` yanıtı döndürür.
4. Worker, `SELECT ... FOR UPDATE SKIP LOCKED` kullanarak uygun siparişi işlem için alır.
5. Sipariş, `Idempotency-Key` başlığı kullanılarak CRM'e gönderilir.
6. Senkronizasyon başarılı olduğunda siparişin durumu `SYNCED` olur.
7. HTTP `429`, HTTP `5xx` ve timeout gibi geçici hatalarda yapılandırmaya bağlı olarak yeniden deneme yapılabilir.
8. Recovery mekanizması, uygun durumdaki eski işlemleri tekrar işlenebilir hâle getirebilir.
9. Lease ve işlem sahipliği kontrolleri, eski worker'ların güncel işlem sonuçlarını ezmesini önlemeye yardımcı olur.

## Kullanılan Teknolojiler

| Teknoloji | Kullanım amacı |
|---|---|
| React | Kullanıcı arayüzü |
| Vite | Frontend geliştirme ve derleme |
| JavaScript ve CSS | Arayüz mantığı ve tasarımı |
| Python 3.11 | Backend geliştirme |
| FastAPI | REST API ve webhook endpoint'leri |
| PostgreSQL | Kalıcı veri saklama |
| SQLAlchemy 2.0 | ORM ve asenkron veritabanı işlemleri |
| asyncpg | Asenkron PostgreSQL bağlantısı |
| Alembic | Veritabanı migrasyonları |
| Pydantic v2 | Veri doğrulama ve ayarlar |
| HTTPX | HTTP istekleri ve CRM iletişimi |
| pytest | Otomatik testler |
| pytest-asyncio | Asenkron test desteği |
| Docker Compose | Servisleri birlikte çalıştırma |
| GitHub Actions | Sürekli entegrasyon (CI) |

## Dosya ve Klasör Yapısı

```text
ClientBridge/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   └── images/
│       ├── dashboard.png
│       └── orders-activity.png
├── frontend/
│   ├── src/
│   └── package.json
├── clientbridge/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── workers/
│   │   │   └── polling_worker.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic.ini
│   └── requirements.txt
├── requirements.txt
└── README.md
```

## Kurulum

### Gereksinimler

- Python 3.11
- Git
- Docker Desktop ve Docker Compose
- Frontend'i yerel olarak çalıştırmak için Node.js ve npm

### 1. Projeyi Klonlayın

```bash
git clone https://github.com/ekinalkan1334-engineering/ClientBridge.git
cd ClientBridge
```

### 2. Ortam Değişkenlerini Ayarlayın

Backend ve Docker yapılandırması için gerekli ortam değişkenlerini projenin `.env` dosyasında tanımlayın. Gerçek şifreleri, erişim anahtarlarını ve gizli bilgileri GitHub'a yüklemeyin.

Yerel Python geliştirme ortamını oluşturmak için proje kök dizininde:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Docker Servislerini Başlatın

`docker-compose.yml` dosyasının bulunduğu dizinde:

```bash
docker compose up --build -d
```

Servis durumlarını kontrol etmek için:

```bash
docker compose ps
```

API ve worker loglarını görüntülemek için:

```bash
docker compose logs --tail=100 api worker
```

Mevcut Docker Compose yapılandırmasında API, bilgisayarda `8001` portundan erişilebilir.

### 4. Sistem Sağlığını Kontrol Edin

```bash
curl http://127.0.0.1:8001/health/ready
```

Sağlıklı durumda endpoint `200 OK` yanıtı döndürür ve veritabanı, CRM ve worker kontrollerinin başarılı olduğunu bildirir.

### 5. Swagger UI

Tarayıcıda aşağıdaki adresi açın:

http://127.0.0.1:8001/docs

### 6. Frontend'i Başlatın

Frontend'i ayrı olarak çalıştırmak için `frontend` klasörüne gidin:

```bash
npm install
npm run dev
```

Vite terminalde yerel adresi gösterecektir. Frontend'in API adresinin çalışan backend yapılandırmasıyla eşleştiğinden emin olun.

## API Endpoint'leri

| Metot | Endpoint | Amaç |
|---|---|---|
| `POST` | `/webhooks/orders` | Sipariş webhook'u almak |
| `GET` | `/orders` | Siparişleri listelemek |
| `GET` | `/health/ready` | Uygulamanın hazır olma durumunu kontrol etmek |
| `GET` | `/docs` | Swagger dokümantasyonunu açmak |

### Webhook Yinelenme Davranışı

| Senaryo | Beklenen yanıt |
|---|---|
| Yeni ve geçerli sipariş | `202 Accepted` |
| Aynı sipariş kimliği ve aynı kayıtlı e-posta/tutar | `202 Accepted` |
| Aynı sipariş kimliği, ancak farklı kayıtlı e-posta veya tutar | `409 Conflict` |

Mevcut uygulamada yinelenen sipariş kontrolü, kayıtlı müşteri e-postası ve toplam tutarı karşılaştırır. Gelen isteğin ürünlerini ve para birimi dâhil tüm alanlarını karşılaştırmaz.

## Güvenilirlik ve Testler

### Otomatik Testler

Backend dizininde, sanal ortam etkin durumdayken:

```bash
python -m pytest -q
```

**Son kaydedilen test sonucu:** `13 passed, 1 warning`.

Testler başarılı tamamlanmıştır. Uyarı, test ortamındaki bir AnyIO API öğesinin kullanımdan kaldırılmasına ilişkin bilgilendirmedir.

### Çalışma Zamanında Denenen Senaryolar

- **Worker çökmesi ve recovery:** Worker işlem sırasında durdurulduktan sonra ilgili siparişin daha sonra `SYNCED` durumuna ulaştığı gözlemlendi.
- **CRM timeout ve retry:** Kısa timeout ayarıyla bir CRM isteği zaman aşımına uğradı; sonraki deneme başarılı oldu ve sipariş `SYNCED` durumuna ulaştı.
- **Webhook idempotency:** Aynı kayıtlı verilerle tekrarlanan istek `202`, çelişen verilerle gönderilen istek `409` döndürdü.
- **Docker readiness:** Readiness endpoint'i `200 OK` döndürdü ve veritabanı, CRM ve worker kontrolleri başarılı raporlandı.
- **Birden fazla worker:** İki worker container'ı çalıştırıldı. Test siparişi önce tekrar denenebilir bir `429` yanıtı, ardından başarılı bir `200` yanıtı aldı. Son durumda sipariş `SYNCED`, kayıtlı CRM bağlantısı sayısı `1` ve senkronizasyon denemesi sayısı `2` idi.

Birden fazla worker testi, retry mekanizmasının ve nihai senkronizasyonun çalıştığını gösterir. Ancak tek başına mükerrer CRM isteklerinin hiçbir koşulda oluşmayacağını kanıtlamaz. Eş zamanlılık testlerinin ve CRM tarafındaki idempotency davranışının daha ayrıntılı doğrulanması yararlı olacaktır.

## Sürekli Entegrasyon (CI)

GitHub Actions, yapılandırılmış depo olayları tetiklendiğinde otomatik test iş akışını çalıştırır.

Son geliştirme değişiklikleri için kaydedilen iş akışı başarılı tamamlanmıştır.

[ClientBridge GitHub Actions](https://github.com/ekinalkan1334-engineering/ClientBridge/actions)

## Bilinen Sınırlamalar ve Gelecekteki Geliştirmeler

- Ürünler ve para birimi dâhil tüm sipariş alanlarını karşılaştıran daha kapsamlı yinelenen istek kontrolü.
- Eş zamanlı isteklerde CRM tarafı idempotency davranışının daha ayrıntılı test edilmesi.
- Worker çökmesi, timeout ve recovery için daha fazla otomatik entegrasyon testi.
- Gerçek CRM sağlayıcısıyla entegrasyon.
- Kullanıcı girişi ve rol tabanlı yetkilendirme.
- Gelişmiş loglama, metrikler ve alarm mekanizmaları.
- Otomatik deployment ve üretim ortamı yapılandırması.

## Projenin Amacı

ClientBridge; backend geliştirme, asenkron işleme, veritabanı işlemleri, API entegrasyonu, retry ve recovery stratejileri, container yönetimi, otomatik testler ve sürekli entegrasyon konularında uygulamalı deneyim kazanmak amacıyla geliştirilmiştir.

---

**Geliştirici:** Ekin Alkan

**GitHub:** [ekinalkan1334-engineering](https://github.com/ekinalkan1334-engineering)

**Proje deposu:** [ClientBridge](https://github.com/ekinalkan1334-engineering/ClientBridge)

---

# ClientBridge

**Order Synchronization and Integration Monitoring Dashboard**

ClientBridge is an integration application that receives order webhooks from NovaShop Commerce, stores orders in PostgreSQL, synchronizes them with a CRM system through background workers, and monitors application health.

It combines a React-based user interface, a FastAPI backend, PostgreSQL, and background processing. The project focuses on reliable asynchronous processing, duplicate webhook handling, error management, retries, and worker recovery.

## Screenshots

### Dashboard

![ClientBridge Dashboard](docs/images/dashboard.png)

### Orders and Activity Overview

![ClientBridge Orders and Activity](docs/images/orders-activity.png)

## Key Features

- **Order tracking:** View order statuses and related information.
- **Asynchronous processing:** Accept webhooks and perform CRM synchronization in the background.
- **Persistent storage:** Store orders in PostgreSQL before processing begins.
- **Webhook idempotency:** Return `202 Accepted` for repeated submissions with matching stored data and `409 Conflict` when submitted data conflicts with an existing order.
- **Worker coordination:** Use `SELECT ... FOR UPDATE SKIP LOCKED` to help coordinate order claiming across multiple workers.
- **Retry handling:** Support configured retries for transient failures, including HTTP `429`, HTTP `5xx`, and request timeouts.
- **Recovery mechanism:** Make eligible stale processing records available for recovery.
- **Lease protection:** Help prevent stale workers from updating records after losing processing ownership.
- **Health monitoring:** Check database connectivity, CRM reachability, and worker heartbeat freshness.
- **Docker Compose:** Run the database, migration, API, and worker services together.
- **Automated testing:** Include pytest tests and a GitHub Actions CI workflow.

## Architecture

```text
NovaShop Commerce
        |
        | Order Webhook
        v
   FastAPI Backend
        |
        | Validate and persist
        | Return HTTP 202
        v
    PostgreSQL
        |
        v
 Background Worker
        |
        | CRM request with Idempotency-Key
        v
      Mock CRM
        |
        +---- Success ------> SYNCED
        |
        +---- Temporary Error -> Retry
        |
        +---- Retry Limit ----> FAILED
```

## Order Processing Flow

1. The API receives and validates an order webhook.
2. The order is persisted in PostgreSQL with a `PENDING` status.
3. The API returns `202 Accepted` when a new order is accepted.
4. A worker claims an eligible order using `SELECT ... FOR UPDATE SKIP LOCKED`.
5. The worker sends the order to the CRM with an `Idempotency-Key` header.
6. Successful synchronization changes the order status to `SYNCED`.
7. Transient failures such as HTTP `429`, HTTP `5xx`, and timeouts can trigger retries according to the configured policy.
8. Recovery logic can make eligible stale processing records available for processing again.
9. Lease and ownership checks help prevent stale workers from overwriting current processing results.

## Technology Stack

| Technology | Purpose |
|---|---|
| React | User interface |
| Vite | Frontend development and build tooling |
| JavaScript and CSS | Frontend logic and styling |
| Python 3.11 | Backend runtime |
| FastAPI | REST API and webhook endpoints |
| PostgreSQL | Persistent data storage |
| SQLAlchemy 2.0 | ORM and asynchronous database operations |
| asyncpg | Asynchronous PostgreSQL driver |
| Alembic | Database migrations |
| Pydantic v2 | Data validation and settings |
| HTTPX | HTTP requests and CRM communication |
| pytest | Automated testing |
| pytest-asyncio | Asynchronous test support |
| Docker Compose | Multi-service orchestration |
| GitHub Actions | Continuous integration (CI) |

## Repository Structure

```text
ClientBridge/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   └── images/
│       ├── dashboard.png
│       └── orders-activity.png
├── frontend/
│   ├── src/
│   └── package.json
├── clientbridge/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── workers/
│   │   │   └── polling_worker.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic.ini
│   └── requirements.txt
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites

- Python 3.11
- Git
- Docker Desktop with Docker Compose
- Node.js and npm, if running the frontend locally

### 1. Clone the Repository

```bash
git clone https://github.com/ekinalkan1334-engineering/ClientBridge.git
cd ClientBridge
```

### 2. Configure Environment Variables

Configure the environment variables required by the backend and Docker Compose setup in `.env`. Never commit real passwords, access keys, or secrets.

To set up a local Python development environment from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Start the Docker Services

From the directory containing `docker-compose.yml`, run:

```bash
docker compose up --build -d
```

Inspect service status:

```bash
docker compose ps
```

View API and worker logs:

```bash
docker compose logs --tail=100 api worker
```

In the current Docker Compose configuration, the API is exposed on host port `8001`.

### 4. Check Application Readiness

```bash
curl http://127.0.0.1:8001/health/ready
```

When healthy, the endpoint returns `200 OK` and reports successful database, CRM, and worker checks.

### 5. Open Swagger UI

Open the following address in a browser:

http://127.0.0.1:8001/docs

### 6. Run the Frontend

To run the frontend separately, navigate to the `frontend` directory:

```bash
npm install
npm run dev
```

Vite will display the local development URL. Ensure that the frontend API URL matches the running backend configuration.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/webhooks/orders` | Receive an order webhook |
| `GET` | `/orders` | List orders |
| `GET` | `/health/ready` | Check application readiness |
| `GET` | `/docs` | Open Swagger documentation |

### Webhook Duplicate Handling

| Scenario | Expected response |
|---|---|
| New valid order | `202 Accepted` |
| Same order ID with matching stored email and amount | `202 Accepted` |
| Same order ID with a conflicting stored email or amount | `409 Conflict` |

The current implementation compares the stored customer email and total amount when checking duplicate orders. It does not compare every field in the incoming payload, including all item and currency details.

## Reliability and Testing

### Automated Tests

Run the following command from the backend directory with the project virtual environment activated:

```bash
python -m pytest -q
```

**Latest recorded result:** `13 passed, 1 warning`.

The tests completed successfully. The warning was a deprecation notice for an AnyIO API used by the test environment.

### Runtime Scenarios

The following scenarios have been exercised during development:

- **Worker crash and recovery:** After a worker was interrupted during processing, the affected order subsequently reached `SYNCED`.
- **CRM timeout and retry:** With a short timeout configured, a CRM request timed out; a subsequent attempt succeeded and the order reached `SYNCED`.
- **Webhook idempotency:** Repeated requests with matching stored data returned `202`; conflicting requests returned `409`.
- **Docker readiness:** The readiness endpoint returned `200 OK`, reporting successful database, CRM, and worker checks.
- **Multiple workers:** Two worker containers were running. The test order received a retryable `429` response followed by a successful `200` response. The final state was `SYNCED`, with one stored CRM link and two recorded synchronization attempts.

The multiple-worker test demonstrates retry behavior and successful final synchronization. It does not, by itself, prove that duplicate CRM requests can never occur. Further concurrency testing and verification of CRM-side idempotency would be beneficial.

## Continuous Integration

GitHub Actions runs the automated test workflow when configured repository events trigger it.

The latest recorded workflow for the current development changes completed successfully.

[ClientBridge GitHub Actions](https://github.com/ekinalkan1334-engineering/ClientBridge/actions)

## Known Limitations and Future Improvements

- Expand duplicate detection to compare the complete order payload, including items and currency.
- Test CRM-side idempotency more thoroughly under concurrent requests.
- Add more automated integration tests for worker crashes, timeouts, and recovery.
- Integrate with a real CRM provider.
- Add user authentication and role-based authorization.
- Improve logging, metrics, and alerting.
- Add automated deployment and production environment configuration.

## Project Goal

ClientBridge was developed to gain practical experience with backend engineering, asynchronous processing, database transactions, API integration, retry and recovery strategies, container orchestration, automated testing, and continuous integration.

---

**Author:** Ekin Alkan

**GitHub:** [ekinalkan1334-engineering](https://github.com/ekinalkan1334-engineering)

**Repository:** [ClientBridge](https://github.com/ekinalkan1334-engineering/ClientBridge)
