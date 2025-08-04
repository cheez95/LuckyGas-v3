# Lucky Gas Training System

Comprehensive employee training system for Lucky Gas (幸福氣) with microlearning, gamification, and real-time progress tracking.

## System Overview

The Lucky Gas Training System is a modern, cloud-native learning management platform designed specifically for gas delivery companies. It provides:

- 🎯 **Microlearning**: Bite-sized training modules optimized for mobile
- 🎮 **Gamification**: Points, achievements, and leaderboards
- 📱 **Mobile-First**: Responsive design for drivers on the go
- 🌐 **Bilingual**: Traditional Chinese and English support
- 🔄 **Real-time**: WebSocket-based progress tracking
- 🎥 **Video Streaming**: HLS adaptive streaming for training videos
- 🧪 **Practice Environment**: Safe sandbox for hands-on training
- 📊 **Analytics**: Comprehensive training metrics and reporting

## Architecture

```
training-system/
├── training-portal/        # Next.js 14 frontend
├── training-api/          # FastAPI backend
├── video-processor/       # AWS Lambda for video processing
├── moodle-plugins/        # Moodle LMS integration
└── practice-environment/  # Docker-based training sandbox
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- AWS Account (for video processing)
- Google Maps API Key

### 1. Training Portal (Frontend)

```bash
cd packages/training-portal
npm install
npm run dev
```

Access at: http://localhost:3000

### 2. Training API (Backend)

```bash
cd packages/training-api
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload
```

API docs at: http://localhost:8000/docs

### 3. Practice Environment

```bash
cd packages/practice-environment
./scripts/deploy.sh
```

Practice portal at: http://localhost:8888

Test accounts:
- Office: office@practice.local / practice123
- Driver: driver@practice.local / practice123
- Manager: manager@practice.local / practice123

## Features

### For Learners

#### Course Discovery
- Browse courses by department and difficulty
- Search and filter capabilities
- Personalized recommendations
- Progress tracking across devices

#### Learning Experience
- Video lessons with adaptive streaming
- Interactive quizzes and assessments
- Downloadable resources
- Offline mode for mobile users
- Progress synchronization

#### Gamification
- Points for completing modules
- Achievement badges and milestones
- Department and company-wide leaderboards
- Learning streaks and challenges
- Social features (coming soon)

### For Administrators

#### Content Management
- Course and module creation
- Video upload with automatic processing
- Quiz and assessment builder
- Resource management
- Multi-language support

#### User Management
- Role-based access control
- Department-based assignments
- Bulk user import/export
- Progress monitoring
- Certificate generation

#### Analytics Dashboard
- Course completion rates
- User engagement metrics
- Department performance
- Video analytics
- Custom reports

### For Managers

#### Team Overview
- Department training progress
- Individual performance tracking
- Compliance monitoring
- Skills gap analysis
- Training recommendations

## Technical Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React Query + Zustand
- **Components**: Custom UI library
- **Charts**: Recharts
- **Video**: React Player with HLS.js

### Backend
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with PostGIS
- **Cache**: Redis
- **ORM**: SQLAlchemy 2.0
- **Auth**: JWT with refresh tokens
- **Validation**: Pydantic
- **Testing**: Pytest with async support

### Infrastructure
- **Video**: AWS S3 + CloudFront + MediaConvert
- **Compute**: AWS Lambda for processing
- **Monitoring**: CloudWatch + Sentry
- **CI/CD**: GitHub Actions
- **Containers**: Docker + Kubernetes

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - User logout

### Courses
- `GET /courses` - List courses
- `GET /courses/{id}` - Course details
- `POST /courses/{id}/enroll` - Enroll in course
- `PUT /courses/{id}/modules/{module_id}/progress` - Update progress

### Achievements
- `GET /achievements` - List all achievements
- `GET /achievements/my-achievements` - User's achievements
- `GET /achievements/leaderboard` - Leaderboard

### Admin
- `POST /admin/courses` - Create course
- `PUT /admin/courses/{id}` - Update course
- `POST /admin/videos/upload` - Upload video
- `GET /admin/analytics` - Analytics data

## Video Processing

The system automatically processes uploaded videos:

1. **Upload** to S3 via presigned URL
2. **Lambda trigger** on S3 upload event
3. **MediaConvert** creates multiple qualities:
   - 360p (800 Kbps)
   - 720p (2.5 Mbps)
   - 1080p (5 Mbps)
4. **HLS packaging** for adaptive streaming
5. **CloudFront** distribution
6. **Thumbnail generation**

## Practice Environment

The practice environment provides a safe sandbox for training:

### Office Training Scenarios
- Customer data management
- Order creation and assignment
- Route optimization
- Report generation
- Complaint handling

### Driver Training Scenarios
- Mobile app navigation
- GPS and route following
- Customer interaction
- Electronic signatures
- Inventory management

## Deployment

### Production Deployment

1. **Build Docker images**:
```bash
docker build -t luckygas-training-portal:latest packages/training-portal
docker build -t luckygas-training-api:latest packages/training-api
```

2. **Push to registry**:
```bash
docker push your-registry/luckygas-training-portal:latest
docker push your-registry/luckygas-training-api:latest
```

3. **Deploy to Kubernetes**:
```bash
kubectl apply -f k8s/training-system/
```

### Environment Variables

See `.env.example` files in each package for required configuration.

## Monitoring

### Application Metrics
- Request latency and error rates
- Video streaming performance
- WebSocket connection health
- Database query performance

### Business Metrics
- Course completion rates
- User engagement scores
- Video watch time
- Achievement unlock rates

## Security

- JWT authentication with refresh tokens
- Role-based access control (RBAC)
- Content Security Policy (CSP)
- Rate limiting and DDoS protection
- Encrypted video delivery
- OWASP compliance

## Contributing

1. Fork the repository
2. Create feature branch
3. Follow code style guidelines
4. Write tests for new features
5. Submit pull request

## License

Copyright © 2025 Lucky Gas Company. All rights reserved.