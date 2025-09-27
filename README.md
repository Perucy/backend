# FitPro Backend API

A FastAPI-based backend service that powers the FitPro fitness app, providing secure user authentication and seamless integrations with Whoop and Spotify APIs for personalized fitness and music experiences.

> **⚠️ Project Status**: This project is currently on hold while I focus on other priorities. The codebase is functional but may not receive regular updates. Feel free to fork and continue development!

## 🛠️ Built With

**Core Framework:**
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) **Python 3.13+** - Programming language
- ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) **FastAPI** - Modern web framework for APIs
- ![Uvicorn](https://img.shields.io/badge/Uvicorn-2C5AA0?style=flat&logo=gunicorn&logoColor=white) **Uvicorn** - ASGI server

**Database & Storage:**
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white) **PostgreSQL** - Primary database
- ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat&logo=sqlalchemy&logoColor=white) **SQLAlchemy (Async)** - ORM with async support
- ![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white) **Redis** - Session storage and caching

**Authentication & Security:**
- ![JWT](https://img.shields.io/badge/JWT-000000?style=flat&logo=jsonwebtokens&logoColor=white) **PyJWT** - JSON Web Tokens
- ![OAuth](https://img.shields.io/badge/OAuth_2.0-4285F4?style=flat&logo=oauth&logoColor=white) **OAuth 2.0 + PKCE** - Secure third-party authentication
- ![Cryptography](https://img.shields.io/badge/Cryptography-663399?style=flat&logo=letsencrypt&logoColor=white) **Fernet Encryption** - Token encryption

**Third-Party APIs:**
- ![Whoop](https://img.shields.io/badge/Whoop_API-FF6B35?style=flat&logo=fitbit&logoColor=white) **Whoop API v2** - Fitness and recovery data
- ![Spotify](https://img.shields.io/badge/Spotify_API-1DB954?style=flat&logo=spotify&logoColor=white) **Spotify Web API** - Music data and recommendations

**Development Tools:**
- ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) **Docker Compose** - Containerized development
- ![pgAdmin](https://img.shields.io/badge/pgAdmin-4169E1?style=flat&logo=postgresql&logoColor=white) **pgAdmin** - Database administration
- ![Redis Commander](https://img.shields.io/badge/Redis_Commander-DC382D?style=flat&logo=redis&logoColor=white) **Redis Commander** - Redis GUI

## 🌟 Features

- **🔐 Secure Authentication**: JWT-based auth with refresh tokens
- **🏃 Whoop Integration**: Complete OAuth flow with fitness data access
- **🎵 Spotify Integration**: Music recommendations based on recovery status
- **🗄️ Async Database**: High-performance PostgreSQL with async SQLAlchemy
- **🔒 Data Encryption**: OAuth tokens encrypted at rest using Fernet
- **🐳 Docker Ready**: Complete containerized development environment
- **📊 State Management**: OAuth state tracking for secure flows
- **🔄 Token Refresh**: Automatic token refresh for both APIs
- **🚀 Auto-Scaling**: Connection pooling and async request handling

## 🏗️ Architecture

### Project Structure

```
backend/
├── auth/                     # Authentication system
│   ├── auth.py              # JWT functions, password hashing
│   └── dependencies.py      # Database user operations
├── databases/               # Database layer
│   ├── database.py          # Models, engine, session setup
│   ├── db_service.py        # OAuth token storage
│   └── oauth_state_service.py # OAuth state management
├── integrations/            # Third-party API integrations
│   ├── whoop.py            # Whoop API client
│   └── spotify.py          # Spotify API client
├── routers/                # API route handlers
│   ├── app_routes.py       # User auth endpoints
│   ├── whoop_routes.py     # Whoop integration endpoints
│   └── spotify_routes.py   # Spotify integration endpoints
├── init-db/                # Database initialization
│   └── 01-create-database.sql
├── docker-compose.yml      # Development environment
├── main.py                 # FastAPI application
└── .env.example           # Environment template
```

### Database Schema

**Core Tables:**
- `users` - FitPro user accounts and linked service IDs
- `oauth_tokens` - Encrypted third-party API tokens
- `oauth_states` - Temporary OAuth flow state management

## 🚀 Getting Started

### Prerequisites

- **Python 3.13+** with `pip`
- **Docker & Docker Compose** (for databases)
- **Git** for version control

### Quick Start

1. **Clone and setup**
   ```bash
   git clone <your-repo-url>
   cd fitpro-backend
   pip install -r requirements.txt
   ```

2. **Environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Generate security keys**
   ```bash
   python encryption.py
   # Copy output to your .env file
   ```

4. **Start databases**
   ```bash
   docker-compose up -d
   ```

5. **Run the API**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

6. **Test the setup**
   ```bash
   chmod +x server.sh
   ./server.sh
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Security Keys (generate with encryption.py)
JWT_SECRET_KEY="your-jwt-secret"
ENCRYPTION_KEY="your-fernet-key"

# Database Configuration
DATABASE_URL="postgresql+asyncpg://fitpro_user:password@localhost:5432/fitpro_db"
POSTGRES_DB="fitpro_db"
POSTGRES_USER="fitpro_user"
POSTGRES_PASSWORD="your-db-password"

# Redis Configuration
REDIS_URL="redis://:your-redis-password@localhost:6379"
REDIS_PASSWORD="your-redis-password"

# Whoop API Credentials
WHOOP_CLIENT_ID="your-whoop-client-id"
WHOOP_CLIENT_SECRET="your-whoop-client-secret"
WHOOP_REDIRECT_URI="https://your-domain.com/whoop/auth/callback"

# Spotify API Credentials
SPOTIFY_CLIENT_ID="your-spotify-client-id"
SPOTIFY_CLIENT_SECRET="your-spotify-client-secret"
SPOTIFY_REDIRECT_URI="https://your-domain.com/spotify/auth/callback"

# Port Configuration
POSTGRES_PORT=5432
REDIS_PORT=6379
PGADMIN_PORT=5050
REDIS_COMMANDER_PORT=8081
```

### OAuth App Setup

**Whoop Developer Console:**
1. Create app at [Whoop Developer Portal](https://developer.whoop.com/)
2. Set redirect URI: `https://your-domain.com/whoop/auth/callback`
3. Required scopes: `read:profile read:recovery read:cycles read:sleep read:workout`

**Spotify Developer Console:**
1. Create app at [Spotify for Developers](https://developer.spotify.com/)
2. Set redirect URI: `https://your-domain.com/spotify/auth/callback`
3. Required scopes: `user-read-private user-read-email playlist-read-private user-read-recently-played`

## 📋 API Documentation

### Authentication Endpoints

```http
POST /app/register         # Create new user account
POST /app/login           # User login
POST /app/refresh         # Refresh access token
GET  /app/me             # Get current user profile
```

### Whoop Integration

```http
GET  /whoop/auth/login     # Start Whoop OAuth flow
GET  /whoop/auth/callback  # Handle OAuth callback
GET  /whoop/status         # Check connection status
GET  /whoop/profile        # Get user profile
GET  /whoop/recovery       # Get recovery data
GET  /whoop/workouts       # Get workout data
GET  /whoop/sleep          # Get sleep data
```

### Spotify Integration

```http
GET  /spotify/auth/login      # Start Spotify OAuth flow
GET  /spotify/auth/callback   # Handle OAuth callback
GET  /spotify/status          # Check connection status
GET  /spotify/profile         # Get user profile
GET  /spotify/recently-played # Get recently played tracks
GET  /spotify/currently-playing # Get current track
```

### Example Usage

```bash
# Register new user
curl -X POST "http://localhost:8000/app/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Login and get JWT token
curl -X POST "http://localhost:8000/app/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Use JWT token for protected endpoints
curl -X GET "http://localhost:8000/whoop/status" \
  -H "Authorization: Bearer your-jwt-token"
```

## 🔧 Development

### Database Operations

```bash
# Connect to PostgreSQL
psql -h 127.0.0.1 -p 5432 -U fitpro_user -d fitpro_db

# Test database connection
python test_connection.py

# Initialize database schema
psql -h 127.0.0.1 -p 5432 -U fitpro_user -d fitpro_db -f init-db/01-create-database.sql
```

### Development Tools

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **pgAdmin**: http://localhost:5050 (Database GUI)
- **Redis Commander**: http://localhost:8081 (Redis GUI)

### Running Tests

```bash
# Test all endpoints
./server.sh

# Manual endpoint testing
python test_connection.py
```

## 🔐 Security Features

### Authentication Flow
1. **Registration/Login**: JWT tokens with refresh capability
2. **OAuth Integration**: PKCE-secured OAuth 2.0 flows
3. **Token Storage**: Fernet-encrypted tokens in PostgreSQL
4. **State Management**: Secure OAuth state tracking

### Data Protection
- **Encryption at Rest**: OAuth tokens encrypted using Fernet
- **Secure Sessions**: Redis-backed session management  
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

## 🐳 Docker Development

The included `docker-compose.yml` provides:

- **PostgreSQL 15** with persistent data
- **Redis 7** with password protection
- **pgAdmin 4** for database management
- **Redis Commander** for Redis inspection

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Data Flow

### OAuth Integration Flow

1. **Frontend** → `GET /whoop/auth/login` (with JWT)
2. **Backend** → Stores OAuth state, returns auth URL
3. **User** → Completes OAuth on provider site
4. **Provider** → Redirects to `/whoop/auth/callback`
5. **Backend** → Exchanges code for tokens, stores encrypted
6. **Backend** → Redirects to mobile app with success/error

### API Request Flow

1. **Frontend** → Makes API request with JWT
2. **Backend** → Validates JWT, extracts user ID
3. **Backend** → Retrieves encrypted OAuth tokens
4. **Backend** → Makes authenticated request to provider
5. **Backend** → Returns data to frontend

## 🚀 Deployment

### Production Setup

1. **Environment Variables**
   ```bash
   # Update .env for production
   DATABASE_URL="postgresql+asyncpg://user:pass@prod-db:5432/fitpro"
   REDIS_URL="redis://:pass@prod-redis:6379"
   ```

2. **SSL Configuration**
   ```bash
   # Update OAuth redirect URIs to HTTPS
   WHOOP_REDIRECT_URI="https://api.yourapp.com/whoop/auth/callback"
   SPOTIFY_REDIRECT_URI="https://api.yourapp.com/spotify/auth/callback"
   ```

3. **Run Production Server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Health Monitoring

```bash
# Health check endpoint
curl http://localhost:8000/health

# Basic connectivity
curl http://localhost:8000/
```

## 🐛 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check if PostgreSQL is running
docker-compose ps
# Verify connection settings
python test_connection.py
```

**OAuth Redirect Mismatch**
- Ensure redirect URIs match exactly in OAuth provider settings
- Check HTTPS vs HTTP in production vs development

**Token Encryption Errors**
- Regenerate encryption key: `python encryption.py`
- Verify `ENCRYPTION_KEY` is set in `.env`

**API Rate Limits**
- Whoop: 100 requests per hour per user
- Spotify: Varies by endpoint (usually 100-1000/hour)

### Debug Mode

```bash
# Run with debug logging
uvicorn main:app --reload --log-level debug

# Database query logging (set in database.py)
engine = create_async_engine(DATABASE_URL, echo=True)
```

## 📈 Performance

### Optimization Features
- **Async Database**: Non-blocking PostgreSQL operations
- **Connection Pooling**: Configurable pool size (default: 20)
- **Token Caching**: Redis-based session storage
- **Automatic Retry**: OAuth token refresh on expiration

### Monitoring Metrics
- Database connection pool utilization
- API response times
- OAuth token refresh frequency
- Third-party API error rates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper tests
4. Ensure all endpoints work: `./server.sh`
5. Submit a pull request

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints for all functions
- Document complex OAuth flows
- Add error handling for external APIs

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

For questions or issues:
- Check the troubleshooting section above
- Review API documentation at `/docs`
- Verify OAuth provider settings
- Test with the included `server.sh` script

---

Built with ❤️ using FastAPI and modern Python async patterns