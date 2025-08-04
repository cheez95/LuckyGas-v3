# Lucky Gas Training System Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the Lucky Gas Training System based on the architecture document. The system includes a training portal, API services, video delivery infrastructure, and integration with Moodle LMS.

## Prerequisites

- Node.js 20.11+ and npm
- Python 3.11+
- Docker and Docker Compose
- AWS Account with appropriate permissions
- PostgreSQL 15+
- Redis 7+
- Terraform 1.6+

## Quick Start

### 1. Clone Repository and Setup

```bash
# Clone the repository
git clone https://github.com/luckygas/luckygas-v3.git
cd luckygas-v3

# Install dependencies
cd packages/training-portal
npm install

cd ../training-api
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` files for both frontend and backend:

**packages/training-portal/.env.local**:
```env
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
NEXT_PUBLIC_MOODLE_URL=http://localhost:8080
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8001
```

**packages/training-api/.env**:
```env
DATABASE_URL=postgresql+asyncpg://training_user:training_pass@localhost:5433/luckygas_training
REDIS_URL=redis://:training_redis_pass@localhost:6380/0
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=true
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_BUCKET_NAME=luckygas-training-content-dev
```

### 3. Start Development Environment

```bash
# Start backend services
cd packages/training-api
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:socket_app --reload --port 8001

# In another terminal, start frontend
cd packages/training-portal
npm run dev
```

Access the applications:
- Training Portal: http://localhost:3000
- Training API: http://localhost:8001/api/docs
- Moodle LMS: http://localhost:8080 (admin/Admin123!)

## Detailed Implementation Steps

### Phase 1: Infrastructure Setup

#### 1.1 AWS Infrastructure

```bash
cd infrastructure/terraform/training

# Initialize Terraform
terraform init

# Create development environment
terraform workspace new development
terraform plan -var="environment=development"
terraform apply -var="environment=development"
```

#### 1.2 Database Setup

```sql
-- Create training database and initial schema
CREATE DATABASE luckygas_training;

-- Connect to the database
\c luckygas_training;

-- Run the schema creation (handled by Alembic migrations)
```

#### 1.3 Moodle Configuration

1. Access Moodle at http://localhost:8080
2. Complete initial setup wizard
3. Install Lucky Gas custom plugins:

```bash
# Copy plugins to Moodle
docker cp packages/moodle-plugins/lucky_gas_auth training-moodle:/bitnami/moodle/auth/
docker cp packages/moodle-plugins/lucky_gas_integration training-moodle:/bitnami/moodle/local/

# Restart Moodle
docker restart training-moodle
```

### Phase 2: API Development

#### 2.1 Create API Endpoints

The training API is already scaffolded. Key endpoints to implement:

```python
# app/api/v1/endpoints/training.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.training_service import TrainingService

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get user training dashboard data."""
    service = TrainingService(db)
    return await service.get_user_dashboard(current_user.id)

@router.get("/paths/{role}")
async def get_learning_paths(
    role: str,
    db: AsyncSession = Depends(get_db)
):
    """Get learning paths for a specific role."""
    service = TrainingService(db)
    return await service.get_learning_paths_by_role(role)
```

#### 2.2 Implement Services

```python
# app/services/training_service.py
from sqlalchemy import select, func
from app.models.training import TrainingProfile, Enrollment, Course

class TrainingService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_dashboard(self, user_id: UUID):
        # Get user profile
        profile = await self.db.get(TrainingProfile, user_id)
        
        # Get enrollments
        enrollments = await self.db.execute(
            select(Enrollment)
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.last_accessed.desc())
        )
        
        # Get recommendations
        recommendations = await self._get_recommendations(user_id)
        
        return {
            "profile": profile,
            "enrollments": enrollments.scalars().all(),
            "recommendations": recommendations
        }
```

### Phase 3: Frontend Implementation

#### 3.1 Setup Component Library

```bash
cd packages/training-portal

# Install additional UI components
npm install @radix-ui/react-avatar @radix-ui/react-select
npm install recharts react-player
```

#### 3.2 Create Core Components

```typescript
// src/components/course/CourseCard.tsx
import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { Clock, Users, Star } from 'lucide-react';

interface CourseCardProps {
  course?: Course;
  enrollment?: Enrollment;
  showProgress?: boolean;
  compact?: boolean;
}

export const CourseCard: React.FC<CourseCardProps> = ({
  course,
  enrollment,
  showProgress,
  compact
}) => {
  const displayCourse = course || enrollment?.course;
  
  if (!displayCourse) return null;
  
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <Link href={`/courses/${displayCourse.courseId}`}>
        <div className="p-4">
          <h3 className="font-semibold mb-2">
            {displayCourse.title['zh-TW']}
          </h3>
          
          {!compact && (
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">
              {displayCourse.description['zh-TW']}
            </p>
          )}
          
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center">
              <Clock size={14} className="mr-1" />
              {displayCourse.durationMinutes} 分鐘
            </span>
            <span className="flex items-center">
              <Users size={14} className="mr-1" />
              {displayCourse.enrollmentCount}
            </span>
            <span className="flex items-center">
              <Star size={14} className="mr-1" />
              {displayCourse.rating.toFixed(1)}
            </span>
          </div>
          
          {showProgress && enrollment && (
            <div className="mt-3">
              <Progress value={enrollment.progressPercentage} />
              <span className="text-xs text-gray-500 mt-1">
                {enrollment.progressPercentage}% 完成
              </span>
            </div>
          )}
        </div>
      </Link>
    </Card>
  );
};
```

### Phase 4: Video Infrastructure

#### 4.1 Setup Video Processing

```python
# packages/video-processor/lambda_function.py
import json
import boto3
import os
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
mediaconvert = boto3.client('mediaconvert', endpoint_url=os.environ['MEDIACONVERT_ENDPOINT'])

def lambda_handler(event, context):
    # Get the uploaded video details
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    # Create MediaConvert job
    job_settings = {
        "Role": os.environ['MEDIACONVERT_ROLE_ARN'],
        "Settings": {
            "Inputs": [{
                "FileInput": f"s3://{bucket}/{key}",
                "VideoSelector": {},
                "AudioSelectors": {
                    "Audio Selector 1": {
                        "DefaultSelection": "DEFAULT"
                    }
                }
            }],
            "OutputGroups": [
                create_hls_output_group(bucket, key),
                create_mp4_output_group(bucket, key)
            ]
        }
    }
    
    response = mediaconvert.create_job(**job_settings)
    
    return {
        'statusCode': 200,
        'body': json.dumps(f"Job created: {response['Job']['Id']}")
    }

def create_hls_output_group(bucket, key):
    """Create HLS output group for adaptive streaming."""
    output_key = key.replace('uploads/', 'processed/').replace('.mp4', '')
    
    return {
        "Name": "HLS",
        "OutputGroupSettings": {
            "Type": "HLS_GROUP_SETTINGS",
            "HlsGroupSettings": {
                "Destination": f"s3://{bucket}/{output_key}/hls/",
                "SegmentLength": 10,
                "MinSegmentLength": 0
            }
        },
        "Outputs": [
            create_hls_output("_360p", 640, 360, 800000),
            create_hls_output("_720p", 1280, 720, 2500000),
            create_hls_output("_1080p", 1920, 1080, 5000000)
        ]
    }
```

#### 4.2 Implement Video Player

```typescript
// src/components/video/VideoPlayer.tsx
import React, { useRef, useEffect } from 'react';
import ReactPlayer from 'react-player';
import { api } from '@/services/api';

interface VideoPlayerProps {
  url: string;
  courseId: string;
  moduleId: string;
  onProgress?: (progress: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  url,
  courseId,
  moduleId,
  onProgress
}) => {
  const playerRef = useRef<ReactPlayer>(null);
  const lastUpdateRef = useRef(0);
  
  const handleProgress = (state: { played: number; playedSeconds: number }) => {
    const currentTime = Math.floor(state.playedSeconds);
    
    // Update every 10 seconds
    if (currentTime - lastUpdateRef.current >= 10) {
      lastUpdateRef.current = currentTime;
      
      api.updateVideoProgress(
        courseId,
        moduleId,
        currentTime,
        playerRef.current?.getDuration() || 0
      );
      
      onProgress?.(state.played * 100);
    }
  };
  
  return (
    <div className="video-player-wrapper">
      <ReactPlayer
        ref={playerRef}
        url={url}
        controls
        width="100%"
        height="100%"
        progressInterval={1000}
        onProgress={handleProgress}
        config={{
          file: {
            attributes: {
              controlsList: 'nodownload'
            }
          }
        }}
      />
    </div>
  );
};
```

### Phase 5: Assessment System

#### 5.1 Create Assessment Components

```typescript
// src/components/assessment/QuizQuestion.tsx
import React from 'react';
import { Question } from '@/types/training';
import { RadioGroup, RadioGroupItem } from '@/components/ui/RadioGroup';
import { Checkbox } from '@/components/ui/Checkbox';

interface QuizQuestionProps {
  question: Question;
  value: string | string[];
  onChange: (value: string | string[]) => void;
  showResult?: boolean;
}

export const QuizQuestion: React.FC<QuizQuestionProps> = ({
  question,
  value,
  onChange,
  showResult
}) => {
  const renderQuestionContent = () => {
    switch (question.type) {
      case 'multiple_choice':
        return (
          <RadioGroup
            value={value as string}
            onValueChange={onChange}
            disabled={showResult}
          >
            {question.options?.map((option, index) => (
              <div key={index} className="flex items-center space-x-2 mb-2">
                <RadioGroupItem value={option} id={`q${question.questionId}-${index}`} />
                <label
                  htmlFor={`q${question.questionId}-${index}`}
                  className={`cursor-pointer ${
                    showResult && option === question.correctAnswer
                      ? 'text-green-600 font-semibold'
                      : ''
                  }`}
                >
                  {option}
                </label>
              </div>
            ))}
          </RadioGroup>
        );
        
      case 'true_false':
        return (
          <RadioGroup
            value={value as string}
            onValueChange={onChange}
            disabled={showResult}
          >
            <div className="flex items-center space-x-2 mb-2">
              <RadioGroupItem value="true" id={`q${question.questionId}-true`} />
              <label htmlFor={`q${question.questionId}-true`}>正確</label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="false" id={`q${question.questionId}-false`} />
              <label htmlFor={`q${question.questionId}-false`}>錯誤</label>
            </div>
          </RadioGroup>
        );
        
      default:
        return <div>Unsupported question type</div>;
    }
  };
  
  return (
    <div className="mb-6 p-4 border rounded-lg">
      <h3 className="font-medium mb-3">
        {question.questionText['zh-TW']}
      </h3>
      {renderQuestionContent()}
      {showResult && question.explanation && (
        <div className="mt-3 p-3 bg-blue-50 rounded text-sm">
          <strong>解釋：</strong> {question.explanation['zh-TW']}
        </div>
      )}
    </div>
  );
};
```

### Phase 6: Deployment

#### 6.1 Build and Deploy Frontend

```bash
# Build frontend
cd packages/training-portal
npm run build

# Deploy to AWS S3 + CloudFront
aws s3 sync out/ s3://luckygas-training-portal-production/
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
```

#### 6.2 Deploy Backend to EKS

```yaml
# k8s/training/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: training-api
  namespace: training
spec:
  replicas: 3
  selector:
    matchLabels:
      app: training-api
  template:
    metadata:
      labels:
        app: training-api
    spec:
      containers:
      - name: api
        image: luckygas/training-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: training-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: training-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: training-api
  namespace: training
spec:
  selector:
    app: training-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply deployment:
```bash
kubectl apply -f k8s/training/
```

## Testing

### Unit Tests

```bash
# Frontend tests
cd packages/training-portal
npm test

# Backend tests
cd packages/training-api
pytest tests/unit/ -v
```

### Integration Tests

```bash
# Run integration tests
cd packages/training-api
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
pytest tests/integration/ -v
```

### E2E Tests

```typescript
// tests/e2e/training-flow.spec.ts
import { test, expect } from '@playwright/test';

test('complete training course flow', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[name=email]', 'test@luckygas.com.tw');
  await page.fill('[name=password]', 'password123');
  await page.click('button[type=submit]');
  
  // Navigate to courses
  await page.click('text=我的課程');
  await expect(page).toHaveURL('/courses');
  
  // Start a course
  await page.click('.course-card:first-child');
  await expect(page.locator('h1')).toContainText('課程');
  
  // Watch video
  await page.click('text=開始學習');
  await page.waitForSelector('.video-player-wrapper');
  
  // Complete quiz
  await page.click('text=進行測驗');
  await page.click('input[type=radio]:first-child');
  await page.click('text=提交答案');
  
  // Check certificate
  await expect(page.locator('.certificate-badge')).toBeVisible();
});
```

## Monitoring and Maintenance

### Setup Monitoring

```yaml
# k8s/monitoring/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: training-dashboard
  namespace: monitoring
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Training System Metrics",
        "panels": [
          {
            "title": "Active Learners",
            "targets": [
              {
                "expr": "sum(training_active_users)"
              }
            ]
          },
          {
            "title": "Course Completion Rate",
            "targets": [
              {
                "expr": "avg(training_course_completion_rate)"
              }
            ]
          }
        ]
      }
    }
```

### Regular Maintenance Tasks

1. **Weekly**:
   - Review video processing queue
   - Check assessment completion rates
   - Monitor user feedback

2. **Monthly**:
   - Update course content
   - Review analytics reports
   - Backup Moodle data

3. **Quarterly**:
   - Security patches
   - Performance optimization
   - User satisfaction survey

## Troubleshooting

### Common Issues

#### Video Upload Fails
```bash
# Check S3 permissions
aws s3 cp test.mp4 s3://luckygas-training-content/uploads/

# Check Lambda logs
aws logs tail /aws/lambda/luckygas-video-processor --follow
```

#### Moodle Integration Issues
```bash
# Check Moodle web services
curl -X POST http://localhost:8080/webservice/rest/server.php \
  -d "wstoken=$MOODLE_TOKEN" \
  -d "wsfunction=core_webservice_get_site_info" \
  -d "moodlewsrestformat=json"
```

#### Database Connection Errors
```bash
# Test database connection
psql -h localhost -p 5433 -U training_user -d luckygas_training

# Check connection pool
SELECT count(*) FROM pg_stat_activity WHERE datname = 'luckygas_training';
```

## Next Steps

1. **Configure Production Environment**
   - SSL certificates
   - Domain setup
   - Security hardening

2. **Create Initial Content**
   - Upload training videos
   - Create assessment questions
   - Define learning paths

3. **User Acceptance Testing**
   - Pilot with small group
   - Gather feedback
   - Iterate on UX

4. **Launch Preparation**
   - Train administrators
   - Create user guides
   - Plan rollout schedule

## Support

For issues or questions:
- Technical Support: tech-support@luckygas.com.tw
- Training Team: training@luckygas.com.tw
- Documentation: https://docs.luckygas.com.tw/training