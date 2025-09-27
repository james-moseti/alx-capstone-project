# 🛍️ E-Commerce Backend API

A production-ready, scalable REST API for e-commerce platforms built with Django REST Framework. Features comprehensive user management, product catalog, order processing, and payment handling with robust admin controls.

## Key Features

### User Management

- **JWT Authentication** - Secure token-based auth with refresh tokens
- **User Profiles** - Complete profile management with `/users/me/` endpoint
- **Password Reset** - Email-based password recovery (console/SMTP)
- **Soft Delete** - Users can deactivate accounts instead of permanent deletion

### Product Catalog

- **Full CRUD Operations** - Complete product and category management
- **Advanced Filtering** - Search, filter, sort, and paginate products
- **Public Access** - Browse products without authentication
- **Admin Controls** - Restricted write access for administrators

### Order Management

- **Customer Orders** - Users create and track their own orders
- **Multi-Product Support** - Add multiple products with quantities
- **Auto-Calculation** - Automatic order totals and tax computation
- **Order History** - Complete order tracking and status updates

### Payment Processing

- **Dual Endpoints** - Separate customer and admin payment interfaces
- **Status Management** - PENDING → PAID → REFUNDED workflow
- **Business Rules** - Refunds only allowed for paid orders
- **Payment Gateway Ready** - Designed for PayPal, Stripe, M-Pesa integration

### API Documentation

- **Interactive Swagger UI** - Test endpoints directly in browser
- **Detailed Redoc** - Comprehensive API reference
- **OpenAPI Schema** - Standard JSON schema for tooling integration

## Architecture

Built with modern Django patterns and best practices:

- **Clean Architecture** - Separation of concerns across apps
- **RESTful Design** - Consistent API patterns and HTTP methods
- **Permission System** - Granular access control (IsOwner, IsAdmin)
- **Serializer Validation** - Robust data validation and sanitization
- **Pagination & Filtering** - Scalable data retrieval with `django-filter`

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL (recommended) or SQLite
- Virtual environment tool

### Installation

1. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/ecommerce-backend.git
   cd ecommerce-backend 
   conda create -n ecom-env python=3.10 
   conda activate ecom-env 
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   
   Create `.env` file:
   ```bash
   DB_NAME=enter your db name
   DB_USERNAME=enter your username
   DB_PASSWORD=enter your password
   DB_HOST=localhost
   DB_PORT=5432
   DATABASE_URL=postgres://username:password@localhost:5432/ecommerce_db
   ```

4. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Launch Server**
   ```bash
   python manage.py runserver
   ```

   **API Available at:** `http://localhost:8000/api/`

## API Documentation

| Documentation | URL |
|--------------|-----|
| **Swagger UI** | http://localhost:8000/api/docs/swagger/ |
| **Redoc** | http://localhost:8000/api/docs/redoc/ |
| **OpenAPI Schema** | http://localhost:8000/api/schema/ |

## Authentication Flow

### 1. Obtain JWT Tokens
```bash
POST /api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. Use Access Token
```bash
Authorization: Bearer <access_token>
```

### 3. Refresh Token (when expired)
```bash
POST /api/token/refresh/
{
  "refresh": "<refresh_token>"
}
```

## API Examples

### Products

**Browse Products**
```bash
GET /api/products/?search=smartphone&category=electronics&ordering=-created_at&page=1
```

**Create Product** (Admin Only)
```bash
POST /api/products/
Authorization: Bearer <admin_token>

{
  "name": "iPhone 15 Pro",
  "slug": "iphone-15-pro",
  "description": "Latest iPhone with titanium design",
  "price": "1199.00",
  "stock": 50,
  "category": 1,
  "is_active": true
}
```

### Orders

**Place Order**
```bash
POST /api/orders/
Authorization: Bearer <customer_token>

{
  "items": [
    {
      "product": 1,
      "quantity": 2
    },
    {
      "product": 5,
      "quantity": 1
    }
  ],
  "shipping_address": "123 Main St, City, State 12345"
}
```

**Order Response**
```json
{
  "id": 42,
  "items": [...],
  "subtotal": "2398.00",
  "tax": "191.84",
  "grand_total": "2589.84",
  "status": "PENDING",
  "created_at": "2025-09-27T10:30:00Z"
}
```

### Payments

**Customer Creates Payment**
```bash
POST /api/payments/
Authorization: Bearer <customer_token>

{
  "order": 42
}
```

**Admin Confirms Payment**
```bash
PUT /api/admin/payments/15/
Authorization: Bearer <admin_token>

{
  "order_id": 42,
  "status": "PAID"
}
```

**Admin Processes Refund**
```bash
PUT /api/admin/payments/15/
Authorization: Bearer <admin_token>

{
  "order_id": 42,
  "status": "REFUNDED"
}
```

## Testing

**Run Full Test Suite**

```bash
pytest
```

**Run Specific App Tests**

```bash
pytest users/tests/
pytest products/tests/
pytest orders/tests/
pytest payments/tests/
```

**Coverage Report**
```bash
pytest --cov=. --cov-report=html
```


### Docker Deployment

```dockerfile
# Dockerfile included for containerized deployment
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application"]
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend Framework** | Django 5.0+ | Web framework & ORM |
| **API Framework** | Django REST Framework | RESTful API development |
| **Authentication** | JWT (SimpleJWT) | Stateless authentication |
| **Database** | PostgreSQL | Primary data storage |
| **Documentation** | drf-spectacular | Auto-generated API docs |
| **Filtering** | django-filter | Advanced query capabilities |
| **Email** | Django Email | Password reset functionality |

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/amazing-feature`
3. **Make your changes** with tests
4. **Commit:** `git commit -m 'feat: add amazing feature'`
5. **Push:** `git push origin feature/amazing-feature`
6. **Open Pull Request**
