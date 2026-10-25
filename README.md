# ClientBridge

**Sipariş Senkronizasyonu ve Entegrasyon İzleme Paneli**

ClientBridge, NovaShop Commerce üzerinden gelen sipariş webhook'larını alan, siparişleri PostgreSQL veritabanına kaydeden ve arka plan worker'ları aracılığıyla CRM sistemine aktaran asenkron bir entegrasyon uygulamasıdır. Uygulama; hata yönetimi, yeniden deneme, worker koordinasyonu, işlem sahipliği koruması ve sistem sağlığı kontrolleri içerir.

React tabanlı arayüz, FastAPI backend, PostgreSQL, Docker Compose ve GitHub Actions CI kullanır. Projenin amacı, güvenilir backend ve entegrasyon sistemlerinde kullanılan temel tasarım yaklaşımlarını uygulamalı olarak göstermektir.

## Ekran Görüntüleri

### Dashboard

![ClientBridge Dashboard](docs/images/dashboard.png)

### Siparişler ve Aktivite Özeti

![ClientBridge Siparişler ve Aktivite](docs/images/orders-activity.png)

## Özellikler

- **Asenkron sipariş işleme:** Webhook isteklerini kabul edip CRM senkronizasyonunu arka planda yürütme.
- **Kalıcı veri saklama:** Siparişleri işlenmeden önce PostgreSQL'e kaydetme.
- **Webhook tekrar kontrolü:** Aynı kayıtlı e-posta ve tutara sahip tekrarlar için `202 Accepted`, çelişen e-posta veya tutar için `409 Conflict` döndürme.
- **Worker koordinasyonu:** Siparişlerin eşzamanlı alınmasını koordine etmek için `SELECT ... FOR UPDATE SKIP LOCKED` kullanma.
- **Retry mekanizması:** HTTP `429`, HTTP `5xx` ve timeout gibi geçici CRM hatalarında yapılandırılmış yeniden deneme.
- **Lease koruması:** İşlem sahipliğini kaybeden worker'ların güncel kayıtları değiştirmesini önlemeye yardımcı olma.
- **Recovery mekanizması:** Uygun durumdaki eski `PROCESSING` kayıtlarını yeniden işlenebilir hâle getirme.
- **Sistem sağlığı:** Veritabanı, CRM erişilebilirliği ve worker sağlığını kontrol etme.
- **Docker Compose:** Veritabanı, migrasyon, API ve worker servislerini birlikte çalıştırma.
- **Otomatik testler ve CI:** pytest testleri ve GitHub Actions iş akışı.

## Proje Mimarisi

```text
NovaShop Commerce
        |
        | Sipariş Webhook'u
        v
   FastAPI Backend
        |
        | Doğrula ve kaydet
        | HTTP 202 döndür
        v
    PostgreSQL
        |
        v
 Background Workers
        |
        | Idempotency-Key ile CRM isteği
        v
      Mock CRM
        |
        +---- Başarılı -------> SYNCED
        |
        +---- Geçici hata ----> Retry
        |
        +---- Retry sınırı ---> FAILED
```

## Sipariş İşleme Akışı

1. API, sipariş webhook isteğini alır ve doğrular.
2. Sipariş PostgreSQL'e `PENDING` durumuyla kaydedilir.
3. API, sipariş kabul edildiğinde `202 Accepted` döndürür.
4. Worker, uygun siparişi `SELECT ... FOR UPDATE SKIP LOCKED` kullanarak alır.
5. Sipariş CRM'e `Idempotency-Key` başlığıyla gönderilir.
6. Senkronizasyon başarılı olursa sipariş `SYNCED` durumuna geçer.
7. Yeniden denenebilir hatalarda sipariş yapılandırılmış politikaya göre tekrar `PENDING` durumuna alınır.
8. Deneme sınırı aşılırsa sipariş `FAILED` durumuna geçer.
9. Recovery mekanizması, uygun durumdaki eski işlem kayıtlarını tekrar işlenebilir hâle getirebilir.
10. Lease ve sahiplik kontrolleri, eski worker'ların güncel işlem sonuçlarını ezmesini önlemeye yardımcı olur.

## Kullanılan Teknolojiler

| Teknoloji | Kullanım amacı |
|---|---|
| React | Kullanıcı arayüzü |
| Vite | Frontend geliştirme ve derleme |
| JavaScript ve CSS | Arayüz mantığı ve tasarımı |
| Python 3.11 | Backend çalışma ortamı |
| FastAPI | REST API ve webhook endpoint'leri |
| PostgreSQL | Kalıcı veri saklama |
| SQLAlchemy 2.0 | ORM ve asenkron veritabanı işlemleri |
| asyncpg | Asenkron PostgreSQL sürücüsü |
| Alembic | Veritabanı migrasyonları |
| Pydantic v2 | Veri doğrulama ve ayarlar |
| HTTPX | HTTP ve CRM iletişimi |
| pytest | Otomatik testler |
| pytest-asyncio | Asenkron test desteği |
| Docker Compose | Servis orkestrasyonu |
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

Backend ve Docker yapılandırması için gereken ortam değişkenlerini ilgili `.env` dosyasında tanımlayın. Gerçek şifreleri, API anahtarlarını veya diğer gizli bilgileri GitHub'a yüklemeyin.

Proje kök dizininde yerel Python ortamı oluşturmak için:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Docker Servislerini Başlatın

`docker-compose.yml` dosyasının bulunduğu dizinde:

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 api worker
```

Mevcut Docker Compose yapılandırmasında API, bilgisayarda `8001` portundan erişilebilir.

### 4. Sistem Sağlığını Kontrol Edin

Yerel API:

```bash
curl -i http://127.0.0.1:8001/health/ready
```

Canlı deployment:

```bash
curl --max-time 20 -i https://clientbridge-api-6qn6.onrender.com/health/ready
```

Sağlıklı durumda endpoint `200 OK` döndürür ve veritabanı, CRM ve worker kontrollerini raporlar.

### 5. Swagger UI

Yerel API çalışırken tarayıcıda şu adresi açın:

http://127.0.0.1:8001/docs

### 6. Frontend'i Başlatın

`frontend` klasöründe:

```bash
npm install
npm run dev
```

Vite yerel adresi terminalde gösterir. Frontend API adresinin çalışan backend yapılandırmasıyla eşleştiğinden emin olun.

## API Endpoint'leri

| Metot | Endpoint | Amaç |
|---|---|---|
| `POST` | `/webhooks/orders` | Sipariş webhook'u almak |
| `GET` | `/orders` | Siparişleri listelemek |
| `GET` | `/health/ready` | Uygulama sağlığını kontrol etmek |
| `GET` | `/docs` | Swagger dokümantasyonu |

### Webhook Yinelenme Davranışı

| Senaryo | Yanıt |
|---|---|
| Yeni ve geçerli sipariş | `202 Accepted` |
| Aynı sipariş kimliği ve aynı kayıtlı e-posta/tutar | `202 Accepted` |
| Aynı sipariş kimliği fakat farklı kayıtlı e-posta veya tutar | `409 Conflict` |

Mevcut uygulama yinelenen siparişleri kontrol ederken kayıtlı müşteri e-postasını ve toplam tutarı karşılaştırır. Ürünler ve para birimi dâhil tüm alanları karşılaştırmaz.

## Güvenilirlik ve Testler

### Otomatik Testler

Backend dizininde, sanal ortam etkin durumdayken çalıştırın:

```bash
python -m pytest -q
```

Son doğrulanmış odaklı test çalışması:

**`11 passed in 0.81s`**

Çalıştırılan komut:

```bash
python -m pytest tests/test_crm_service.py tests/test_worker_safety.py tests/test_webhooks.py -v
```

Bu 11 test; retry backoff, timeout sınıflandırması, lease ve işlem sahipliği güvenliği, retry sınırı ve webhook davranışlarını kapsadı.

Daha önce ayrı olarak başarılı olan testler:

- PostgreSQL concurrency testi: `1 passed`.
- Recovery service testi: `1 passed`.

Bu sonuçlar ayrı test çalıştırmalarından alınmıştır; mevcut tüm testlerin tek seferde çalıştırıldığı bir sonuç olarak değerlendirilmemelidir.

### Çalışma Zamanında Doğrulananlar

- **Docker servisleri:** API ve veritabanı sağlıklıydı; iki worker konteyneri çalışıyordu.
- **Canlı readiness:** Deployment endpoint'i `200 OK` döndürdü ve veritabanı, CRM ve worker kontrolleri `true` raporladı.
- **GitHub Actions:** CI iş akışı yeşil başarılı durumuyla gözlemlendi.
- **CRM retry davranışı:** Bir test siparişi HTTP `500` hatası aldı, `retry=1` ile `PENDING` durumuna döndü ve daha sonra başarılı senkronizasyon logu (`SYNCED`) görüldü.
- **Worker kesintisi denemesi:** İşlem sırasında bir worker zorla durduruldu. Sipariş daha sonra `PENDING` durumuna döndü ve diğer worker tarafından yeniden alındı; ancak beş deneme sonrasında `FAILED` durumuna ulaştı.
- **Gerçek timeout ve başarı:** Timeout sınıflandırması otomatik testlerde doğrulandı. Gerçek CRM timeout'undan sonra teslimatın başarıyla tamamlandığı uçtan uca senaryo henüz doğrulanmadı.
- **Crash recovery:** Worker çökmesinden sonra siparişin `SYNCED` durumuna ulaştığı başarılı uçtan uca senaryo henüz doğrulanmadı.

Worker kesintisi testi başarılı recovery olarak raporlanmamaktadır. Test siparişinin `FAILED` olması, CRM gecikmesi, retry zamanlaması ve recovery davranışının daha fazla incelenmesi gerektiğini göstermektedir.

### PostgreSQL Worker Eşzamanlılığı

Daha önce başarıyla tamamlanan PostgreSQL concurrency testi (`1 passed`), aynı siparişi eşzamanlı olarak almaya çalışan iki işlemden yalnızca birinin başarılı şekilde siparişi claim etmesini kontrol eder.

Bu test, sipariş claim etme yolunu doğrular; tüm hata senaryolarında mükerrer CRM yan etkilerinin imkânsız olduğunu tek başına kanıtlamaz. CRM tarafındaki idempotency davranışı ayrıca doğrulanmalıdır.

## Sürekli Entegrasyon (CI)

GitHub Actions, yapılandırılmış depo olayları tetiklendiğinde otomatik test iş akışını çalıştırır.

Geliştirme sırasında iş akışı yeşil başarılı durumuyla gözlemlendi.

[ClientBridge GitHub Actions](https://github.com/ekinalkan1334-engineering/ClientBridge/actions)

## Canlı Deployment

Canlı API readiness endpoint'i:

https://clientbridge-api-6qn6.onrender.com/health/ready

Son manuel kontrolde endpoint `200 OK` döndürdü ve veritabanı, CRM ve worker kontrollerini `true` olarak raporladı. Bu, kontrol anındaki sağlığı gösterir; kesintisiz erişilebilirlik garantisi değildir.

## Bilinen Sınırlamalar ve Gelecekteki Geliştirmeler

- Worker çökmesi sonrası siparişin `SYNCED` durumuna ulaştığı başarılı uçtan uca recovery testini tamamlamak.
- Gerçek CRM timeout'u sonrası başarılı teslimat senaryosunu doğrulamak.
- Mock CRM gecikmesi ile istemci timeout ve retry zamanlamasının etkileşimini incelemek.
- Yinelenen sipariş kontrolünü ürünler ve para birimi dâhil tüm payload alanlarını kapsayacak şekilde genişletmek.
- CRM tarafı idempotency davranışını eşzamanlı isteklerle daha ayrıntılı test etmek.
- Gerçek CRM sağlayıcısıyla entegrasyon.
- Kimlik doğrulama, rol tabanlı yetkilendirme, metrikler ve alarm mekanizmaları eklemek.
- Üretim deployment ve operasyonel gereksinimlerini gözden geçirmek.

## Projenin Amacı

ClientBridge; backend geliştirme, asenkron işleme, veritabanı işlemleri, API entegrasyonu, retry ve recovery stratejileri, container orkestrasyonu, otomatik testler ve sürekli entegrasyon konularında uygulamalı deneyim kazanmak amacıyla geliştirilmiştir.

---

**Geliştirici:** Ekin Alkan

**GitHub:** [ekinalkan1334-engineering](https://github.com/ekinalkan1334-engineering)

**Proje deposu:** [ClientBridge](https://github.com/ekinalkan1334-engineering/ClientBridge)

---

# ClientBridge

**Order Synchronization and Integration Monitoring Dashboard**

ClientBridge is an asynchronous integration application that receives order webhooks from NovaShop Commerce, persists orders in PostgreSQL, and synchronizes them with a CRM through background workers. It includes error handling, retries, worker coordination, lease protection, recovery logic, and health checks.

The project combines a React frontend, FastAPI backend, PostgreSQL, Docker Compose, and GitHub Actions CI. Its goal is to demonstrate practical backend and integration patterns used to build reliable asynchronous systems.

## Screenshots

### Dashboard

![ClientBridge Dashboard](docs/images/dashboard.png)

### Orders and Activity Overview

![ClientBridge Orders and Activity](docs/images/orders-activity.png)

## Key Features

- **Asynchronous order processing:** Accept webhooks and perform CRM synchronization in the background.
- **Persistent storage:** Store orders in PostgreSQL before processing.
- **Webhook duplicate handling:** Return `202 Accepted` for matching stored email and amount, and `409 Conflict` for conflicting stored email or amount.
- **Worker coordination:** Use PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` to coordinate order claiming.
- **Retry handling:** Retry transient CRM failures, including HTTP `429`, HTTP `5xx`, and timeouts, according to configured limits.
- **Lease protection:** Help prevent workers that have lost processing ownership from updating current records.
- **Recovery mechanism:** Make eligible stale `PROCESSING` records available for reprocessing.
- **Health monitoring:** Check database connectivity, CRM reachability, and worker health.
- **Docker Compose:** Run the database, migrations, API, and workers together.
- **Automated testing and CI:** Use pytest and GitHub Actions.

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
 Background Workers
        |
        | CRM request with Idempotency-Key
        v
      Mock CRM
        |
        +---- Success -------> SYNCED
        |
        +---- Temporary Error -> Retry
        |
        +---- Retry Limit ----> FAILED
```

## Order Processing Flow

1. The API receives and validates an order webhook.
2. The order is stored in PostgreSQL with a `PENDING` status.
3. The API returns `202 Accepted` when the order is accepted.
4. A worker claims an eligible order using `SELECT ... FOR UPDATE SKIP LOCKED`.
5. The order is sent to the CRM with an `Idempotency-Key` header.
6. Successful synchronization changes the order status to `SYNCED`.
7. Retryable failures return the order to `PENDING` according to the configured policy.
8. Orders exceeding the retry limit become `FAILED`.
9. Recovery logic can make eligible stale processing records available for reprocessing.
10. Lease and ownership checks help prevent stale workers from overwriting current processing results.

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
| pytest | Automated tests |
| pytest-asyncio | Asynchronous test support |
| Docker Compose | Service orchestration |
| GitHub Actions | Continuous integration |

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

Configure the required environment variables in the appropriate `.env` file. Never commit real passwords, API keys, credentials, or other secrets.

Create a local Python environment from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Start Docker Services

From the directory containing `docker-compose.yml`:

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 api worker
```

The current Docker Compose configuration exposes the API on host port `8001`.

### 4. Check Application Readiness

Local API:

```bash
curl -i http://127.0.0.1:8001/health/ready
```

Live deployment:

```bash
curl --max-time 20 -i https://clientbridge-api-6qn6.onrender.com/health/ready
```

A healthy response returns `200 OK` and reports the database, CRM, and worker checks.

### 5. Open Swagger UI

With the local API running, open:

http://127.0.0.1:8001/docs

### 6. Run the Frontend

From the `frontend` directory:

```bash
npm install
npm run dev
```

Vite displays the local URL. Ensure that the frontend API configuration matches the backend URL.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/webhooks/orders` | Receive an order webhook |
| `GET` | `/orders` | List orders |
| `GET` | `/health/ready` | Check application health |
| `GET` | `/docs` | Swagger documentation |

### Webhook Duplicate Handling

| Scenario | Response |
|---|---|
| New valid order | `202 Accepted` |
| Same order ID with matching stored email and amount | `202 Accepted` |
| Same order ID with conflicting stored email or amount | `409 Conflict` |

The current implementation compares the stored customer email and total amount. It does not compare every field in the incoming payload, including all item and currency details.

## Reliability and Testing

### Automated Tests

Run the following from the backend directory with the project virtual environment activated:

```bash
python -m pytest -q
```

The latest verified focused test run was:

**`11 passed in 0.81s`**

Command used:

```bash
python -m pytest tests/test_crm_service.py tests/test_worker_safety.py tests/test_webhooks.py -v
```

These 11 tests covered retry backoff, timeout classification, lease and ownership safety, retry-limit behavior, and webhook handling.

Previously completed separate tests:

- PostgreSQL concurrency test: `1 passed`.
- Recovery-service test: `1 passed`.

These results come from separate test runs and should not be treated as one combined full-suite result.

### Runtime Verification

- **Docker services:** The API and database were healthy, and two worker containers were running.
- **Live readiness:** The deployed endpoint returned `200 OK`, with database, CRM, and worker checks reporting `true`.
- **GitHub Actions:** The CI workflow was observed with a successful green status.
- **CRM retry behavior:** A test order received an HTTP `500` error, returned to `PENDING` with `retry=1`, and was subsequently logged as successfully synchronized (`SYNCED`).
- **Worker interruption attempt:** A worker was force-stopped during order processing. The order later returned to `PENDING` and was claimed by another worker, but ultimately reached `FAILED` after five retry attempts.
- **Real timeout followed by success:** Timeout classification passed in automated tests, but successful end-to-end delivery after an actual CRM timeout has not yet been verified.
- **Successful crash recovery:** An end-to-end worker-crash test ending with the order in `SYNCED` has not yet been verified.

The worker interruption attempt is not reported as a successful recovery. The failed test order indicates that the interaction between CRM delays, retry timing, and recovery requires further investigation.

### PostgreSQL Worker Concurrency

The PostgreSQL concurrency test previously passed (`1 passed`). It checks that two concurrent attempts to claim a test order result in only one successful claim.

This validates the tested order-claiming path, but does not by itself prove that duplicate CRM side effects are impossible in every failure scenario. CRM-side idempotency requires separate verification.

## Continuous Integration

GitHub Actions runs the automated test workflow when configured repository events trigger it.

The workflow was observed with a successful green status during development.

[View ClientBridge GitHub Actions](https://github.com/ekinalkan1334-engineering/ClientBridge/actions)

## Live Deployment

The deployed API readiness endpoint is:

https://clientbridge-api-6qn6.onrender.com/health/ready

The endpoint returned `200 OK` during the latest manual check, with database, CRM, and worker checks reporting `true`. This confirms health at the time of the check, not guaranteed continuous availability.

## Known Limitations and Future Improvements

- Complete an end-to-end worker-crash recovery test that finishes with the order in `SYNCED`.
- Verify a real CRM timeout followed by successful delivery.
- Investigate the interaction between mock CRM delay and client timeout/retry timing.
- Expand duplicate detection to compare the full order payload, including items and currency.
- Test CRM-side idempotency under concurrent requests.
- Add more automated integration tests for crash recovery, timeouts, and retries.
- Integrate with a real CRM provider.
- Add authentication, role-based authorization, metrics, and alerting.
- Review production deployment and operational requirements.

## Project Goal

ClientBridge was developed to gain practical experience with backend engineering, asynchronous processing, database transactions, API integration, retry and recovery strategies, container orchestration, automated testing, and continuous integration.

---

**Author:** Ekin Alkan

**GitHub:** [ekinalkan1334-engineering](https://github.com/ekinalkan1334-engineering)

**Repository:** [ClientBridge](https://github.com/ekinalkan1334-engineering/ClientBridge)
