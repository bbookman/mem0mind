# Lifeboard Development Specification

## 1. Project Overview

### 1.1 System Description
Lifeboard is a local-first life data aggregation and reflection platform that transforms personal digital data into an interactive "daily newspaper" format. The system automatically ingests data from multiple sources (Limitless, Bee.computer, weather, mood) and presents it through a calendar-centric interface with AI-powered exploration capabilities.

### 1.2 Core Architecture
- **Frontend**: React-based web interface with calendar and chat components
- **Backend**: Node.js/Express API server with modular data processing
- **Database**: PostgreSQL with specialized tables for each data source
- **AI Layer**: Pluggable AI backends (mem0 for MVP) for semantic search and chat
- **Deployment**: Docker containerized for local-first installation

### 1.3 Key Technical Principles
- **Modular Plugin Architecture**: All components swappable via configuration
- **Local-First Processing**: No cloud dependencies for core functionality
- **Date-Optimized Performance**: Database design prioritizes calendar view queries
- **Native Format Preservation**: Rich data maintained with lightweight tagging overlay

## 2. System Architecture

### 2.1 High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web    │    │   Node.js API   │    │   PostgreSQL    │
│   Interface     │◄──►│     Server      │◄──►│    Database     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Vector Store  │
                       │   (mem0/other)  │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ External APIs   │
                       │ (Limitless,Bee, │
                       │  Weather, etc)  │
                       └─────────────────┘
```

### 2.2 Component Architecture

#### 2.2.1 Frontend Components
```
src/frontend/
├── components/
│   ├── CalendarView/
│   │   ├── MonthlyCalendar.jsx
│   │   ├── DailyNewspaper.jsx
│   │   └── DataIndicators.jsx
│   ├── ChatInterface/
│   │   ├── FloatingChat.jsx
│   │   ├── MessageHistory.jsx
│   │   └── AIResponse.jsx
│   ├── DataModules/
│   │   ├── LimitlessModule.jsx
│   │   ├── BeeModule.jsx
│   │   ├── MoodModule.jsx
│   │   └── WeatherModule.jsx
│   └── Common/
│       ├── Layout.jsx
│       ├── Navigation.jsx
│       └── ErrorBoundary.jsx
├── hooks/
│   ├── useCalendarData.js
│   ├── useChat.js
│   └── useDataSources.js
├── services/
│   ├── api.js
│   ├── dateUtils.js
│   └── formatters.js
└── styles/
    ├── calendar.css
    ├── modules.css
    └── chat.css
```

#### 2.2.2 Backend Components
```
src/backend/
├── api/
│   ├── routes/
│   │   ├── calendar.js
│   │   ├── chat.js
│   │   ├── data.js
│   │   └── config.js
│   └── middleware/
│       ├── auth.js
│       ├── validation.js
│       └── errorHandler.js
├── services/
│   ├── dataIngestion/
│   │   ├── LimitlessConnector.js
│   │   ├── BeeConnector.js
│   │   ├── WeatherConnector.js
│   │   └── BaseConnector.js
│   ├── processing/
│   │   ├── DataProcessor.js
│   │   ├── DateNormalizer.js
│   │   └── ContentExtractor.js
│   ├── ai/
│   │   ├── AIProvider.js
│   │   ├── Mem0Provider.js
│   │   └── ChatHandler.js
│   └── storage/
│       ├── DatabaseManager.js
│       ├── VectorStore.js
│       └── ConfigManager.js
├── models/
│   ├── LifelogEntry.js
│   ├── BeeConversation.js
│   ├── MoodEntry.js
│   └── WeatherData.js
└── utils/
    ├── logger.js
    ├── scheduler.js
    └── validators.js
```

## 3. Database Design

### 3.1 Core Tables Structure

#### 3.1.1 Limitless Data Tables
```sql
-- Main lifelog entries
CREATE TABLE limitless_entries (
    id UUID PRIMARY KEY,
    limitless_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    markdown_content TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_starred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content nodes for structured data
CREATE TABLE limitless_content_nodes (
    id UUID PRIMARY KEY,
    entry_id UUID REFERENCES limitless_entries(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES limitless_content_nodes(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL,
    content TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    start_offset_ms INTEGER,
    end_offset_ms INTEGER,
    speaker_name VARCHAR(255),
    speaker_identifier VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 3.1.2 Bee Data Tables
```sql
-- Bee conversations
CREATE TABLE bee_conversations (
    id UUID PRIMARY KEY,
    bee_id BIGINT UNIQUE NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    device_type VARCHAR(50),
    summary TEXT,
    short_summary TEXT,
    state VARCHAR(50),
    primary_location JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation utterances
CREATE TABLE bee_utterances (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES bee_conversations(id) ON DELETE CASCADE,
    bee_utterance_id BIGINT NOT NULL,
    speaker VARCHAR(10) NOT NULL,
    text TEXT NOT NULL,
    start_seconds DECIMAL(10,2),
    end_seconds DECIMAL(10,2),
    spoken_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_realtime BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bee facts
CREATE TABLE bee_facts (
    id UUID PRIMARY KEY,
    bee_id BIGINT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    is_confirmed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bee todos
CREATE TABLE bee_todos (
    id UUID PRIMARY KEY,
    bee_id BIGINT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    alarm_at TIMESTAMP WITH TIME ZONE,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bee locations
CREATE TABLE bee_locations (
    id UUID PRIMARY KEY,
    bee_id BIGINT UNIQUE NOT NULL,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 3.1.3 Supporting Tables
```sql
-- Weather data
CREATE TABLE weather_entries (
    id UUID PRIMARY KEY,
    date DATE NOT NULL,
    location VARCHAR(255),
    temperature_high INTEGER,
    temperature_low INTEGER,
    condition VARCHAR(100),
    description TEXT,
    humidity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mood tracking
CREATE TABLE mood_entries (
    id UUID PRIMARY KEY,
    date DATE NOT NULL,
    mood_score INTEGER CHECK (mood_score >= 1 AND mood_score <= 10),
    mood_text VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily aggregations for performance
CREATE TABLE daily_aggregations (
    id UUID PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    has_limitless_data BOOLEAN DEFAULT FALSE,
    has_bee_data BOOLEAN DEFAULT FALSE,
    has_weather_data BOOLEAN DEFAULT FALSE,
    has_mood_data BOOLEAN DEFAULT FALSE,
    entry_count INTEGER DEFAULT 0,
    ai_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.2 Performance Indexes
```sql
-- Date-based indexes for calendar performance
CREATE INDEX idx_limitless_entries_start_time ON limitless_entries(start_time);
CREATE INDEX idx_limitless_entries_date ON limitless_entries(DATE(start_time));
CREATE INDEX idx_bee_conversations_start_time ON bee_conversations(start_time);
CREATE INDEX idx_bee_conversations_date ON bee_conversations(DATE(start_time));
CREATE INDEX idx_weather_entries_date ON weather_entries(date);
CREATE INDEX idx_mood_entries_date ON mood_entries(date);
CREATE INDEX idx_daily_aggregations_date ON daily_aggregations(date);

-- Content searching indexes
CREATE INDEX idx_limitless_content_search ON limitless_entries USING gin(to_tsvector('english', title || ' ' || COALESCE(markdown_content, '')));
CREATE INDEX idx_bee_conversation_search ON bee_conversations USING gin(to_tsvector('english', summary || ' ' || short_summary));
```

## 4. API Specification

### 4.1 Calendar API Endpoints

#### 4.1.1 Monthly Calendar Data
```
GET /api/calendar/month/{year}/{month}
```
**Response:**
```json
{
  "year": 2025,
  "month": 6,
  "days": [
    {
      "date": "2025-06-01",
      "hasData": true,
      "dataTypes": ["limitless", "bee", "weather"],
      "entryCount": 15
    }
  ]
}
```

#### 4.1.2 Daily Data
```
GET /api/calendar/day/{date}
```
**Response:**
```json
{
  "date": "2025-06-01",
  "aiSummary": "Today brought meaningful conversations...",
  "modules": {
    "limitless": {
      "entries": [...],
      "count": 8
    },
    "bee": {
      "conversations": [...],
      "facts": [...],
      "todos": [...]
    },
    "weather": {
      "condition": "sunny",
      "temperature": {"high": 75, "low": 62}
    },
    "mood": {
      "score": 7,
      "notes": "Productive day"
    }
  }
}
```

### 4.2 Chat API Endpoints

#### 4.2.1 Send Message
```
POST /api/chat/message
```
**Request:**
```json
{
  "message": "What did I talk about yesterday?",
  "context": {
    "currentDate": "2025-06-01",
    "viewType": "daily"
  }
}
```

**Response:**
```json
{
  "response": "Yesterday you had several conversations about...",
  "sources": [
    {
      "type": "bee_conversation",
      "id": "uuid",
      "relevance": 0.95
    }
  ],
  "timestamp": "2025-06-01T10:30:00Z"
}
```

### 4.3 Data Ingestion API Endpoints

#### 4.3.1 Trigger Data Sync
```
POST /api/sync/{source}
```
**Parameters:**
- `source`: limitless | bee | weather | mood

**Response:**
```json
{
  "success": true,
  "source": "limitless",
  "entriesProcessed": 25,
  "newEntries": 3,
  "errors": []
}
```

## 5. Data Processing Specifications

### 5.1 Data Ingestion Pipeline

#### 5.1.1 Limitless Data Processing
```javascript
class LimitlessConnector extends BaseConnector {
  async fetchData(options = {}) {
    // API parameters: timezone, date, start, end, cursor, direction, limit
    const params = this.buildParams(options);
    const response = await this.apiClient.get('/v1/lifelogs', { params });
    
    return this.processLifelogs(response.data.lifelogs);
  }

  async processLifelogs(lifelogs) {
    for (const lifelog of lifelogs) {
      await this.storeLifelogEntry(lifelog);
      await this.processContentNodes(lifelog.contents, lifelog.id);
    }
  }

  async storeLifelogEntry(lifelog) {
    // Store in limitless_entries table
    // Handle duplicate detection via limitless_id
  }
}
```

#### 5.1.2 Bee Data Processing
```javascript
class BeeConnector extends BaseConnector {
  async fetchConversations(options = {}) {
    const conversations = await this.apiClient.get('/v1/me/conversations', {
      params: { limit: options.limit || 10, page: options.page || 1 }
    });
    
    for (const conversation of conversations.conversations) {
      await this.storeConversation(conversation);
      
      // Fetch detailed transcription
      const details = await this.apiClient.get(`/v1/me/conversations/${conversation.id}`);
      await this.processTranscriptions(details.conversation.transcriptions, conversation.id);
    }
  }

  async fetchFacts(options = {}) {
    // Process facts, todos, locations similarly
  }
}
```

### 5.2 AI Processing Pipeline

#### 5.2.1 Daily Summary Generation
```javascript
class AIProvider {
  async generateDailySummary(date) {
    const dayData = await this.dataService.getDayData(date);
    
    const prompt = this.buildSummaryPrompt(dayData);
    const summary = await this.aiClient.complete(prompt);
    
    await this.storeDailySummary(date, summary);
    return summary;
  }

  buildSummaryPrompt(dayData) {
    return `
    Generate a warm, reflective daily summary for this day's activities:
    
    Conversations: ${dayData.bee.conversations.length} conversations
    Key topics: ${this.extractTopics(dayData)}
    Mood: ${dayData.mood.score}/10
    Weather: ${dayData.weather.condition}
    
    Style: Warm and reflective, focusing on meaningful moments and connections.
    `;
  }
}
```

### 5.3 Data Synchronization Strategy

#### 5.3.1 Incremental Sync Logic
```javascript
class DataSyncManager {
  async syncSource(sourceName, options = {}) {
    const lastSyncTime = await this.getLastSyncTime(sourceName);
    const connector = this.getConnector(sourceName);
    
    const syncOptions = {
      ...options,
      since: lastSyncTime,
      batchSize: 50
    };
    
    let hasMore = true;
    let cursor = null;
    
    while (hasMore) {
      const result = await connector.fetchData({ ...syncOptions, cursor });
      await this.processBatch(result.data, sourceName);
      
      cursor = result.nextCursor;
      hasMore = !!cursor;
    }
    
    await this.updateLastSyncTime(sourceName);
  }
}
```

## 6. Configuration Management

### 6.1 Configuration File Structure
```yaml
# lifeboard.config.yml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "lifeboard"
  username: "${DB_USERNAME}"
  password: "${DB_PASSWORD}"

dataSources:
  limitless:
    enabled: true
    apiKey: "${LIMITLESS_API_KEY}"
    baseUrl: "https://api.limitless.ai"
    syncInterval: "1h"
    timezone: "America/New_York"
  
  bee:
    enabled: true
    apiKey: "${BEE_API_KEY}"
    baseUrl: "https://api.bee.computer/v1/me"
    syncInterval: "30m"
    subSources:
      conversations: true
      facts: true
      todos: true
      locations: true
  
  weather:
    enabled: true
    provider: "openweathermap"
    apiKey: "${WEATHER_API_KEY}"
    location: "New York, NY"
    syncInterval: "6h"
  
  mood:
    enabled: true
    reminderTime: "21:00"

ai:
  provider: "mem0"
  config:
    apiKey: "${MEM0_API_KEY}"
    model: "gpt-4"
  
  prompts:
    dailySummary: |
      Generate a warm, reflective summary of this day's activities.
      Focus on meaningful moments and connections.
      Tone: Conversational and insightful.

server:
  port: 3000
  cors:
    origin: ["http://localhost:3001"]
  
logging:
  level: "info"
  file: "./logs/lifeboard.log"
```

### 6.2 Environment Variables
```bash
# .env
DB_USERNAME=lifeboard_user
DB_PASSWORD=secure_password
LIMITLESS_API_KEY=your_limitless_api_key
BEE_API_KEY=your_bee_api_key
WEATHER_API_KEY=your_weather_api_key
MEM0_API_KEY=your_mem0_api_key
```

## 7. Deployment Specification

### 7.1 Docker Configuration

#### 7.1.1 Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

CMD ["npm", "start"]
```

#### 7.1.2 Docker Compose
```yaml
version: '3.8'

services:
  lifeboard:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    env_file:
      - .env
    volumes:
      - ./lifeboard.config.yml:/app/lifeboard.config.yml:ro
      - ./logs:/app/logs
    depends_on:
      - database
    restart: unless-stopped

  database:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: lifeboard
      POSTGRES_USER: ${DB_USERNAME}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

### 7.2 Installation Script
```bash
#!/bin/bash
# install.sh

set -e

echo "Installing Lifeboard..."

# Check requirements
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

# Create directory structure
mkdir -p lifeboard/{config,logs,data}
cd lifeboard

# Download configuration templates
curl -L -o lifeboard.config.yml https://raw.githubusercontent.com/lifeboard/lifeboard/main/config/lifeboard.config.yml.template
curl -L -o .env.template https://raw.githubusercontent.com/lifeboard/lifeboard/main/config/.env.template
curl -L -o docker-compose.yml https://raw.githubusercontent.com/lifeboard/lifeboard/main/docker-compose.yml

# Copy environment template
cp .env.template .env

echo "Installation complete!"
echo "Please edit .env and lifeboard.config.yml with your API keys and preferences."
echo "Then run: docker-compose up -d"
```

## 8. Error Handling and Logging

### 8.1 Error Handling Strategy
```javascript
class ErrorHandler {
  static handle(error, context = {}) {
    const errorInfo = {
      message: error.message,
      stack: error.stack,
      context,
      timestamp: new Date().toISOString(),
      severity: this.determineSeverity(error)
    };
    
    // Log error
    logger.error('Application Error', errorInfo);
    
    // For API errors, continue operation but log
    if (error.type === 'API_ERROR') {
      this.notifyUser(`Data sync failed for ${context.source}. Will retry automatically.`);
      return { success: false, retry: true };
    }
    
    // For critical errors, fail gracefully
    if (error.type === 'DATABASE_ERROR') {
      this.notifyUser('Database connection lost. Please check your configuration.');
      return { success: false, critical: true };
    }
    
    return { success: false };
  }
}
```

### 8.2 Logging Configuration
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'lifeboard' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});
```

## 9. Testing Specifications

### 9.1 Unit Testing
```javascript
// Example test structure
describe('LimitlessConnector', () => {
  describe('fetchData', () => {
    it('should fetch and process lifelog entries', async () => {
      const connector = new LimitlessConnector(mockConfig);
      const mockResponse = { data: { lifelogs: [mockLifelog] } };
      
      jest.spyOn(connector.apiClient, 'get').mockResolvedValue(mockResponse);
      
      const result = await connector.fetchData();
      
      expect(result).toHaveLength(1);
      expect(result[0].title).toBe(mockLifelog.title);
    });
  });
});
```

### 9.2 Integration Testing
```javascript
describe('Data Ingestion Pipeline', () => {
  it('should sync data from all sources without conflicts', async () => {
    const syncManager = new DataSyncManager();
    
    await Promise.all([
      syncManager.syncSource('limitless'),
      syncManager.syncSource('bee'),
      syncManager.syncSource('weather')
    ]);
    
    const dayData = await dataService.getDayData('2025-06-01');
    expect(dayData.modules).toHaveProperty('limitless');
    expect(dayData.modules).toHaveProperty('bee');
    expect(dayData.modules).toHaveProperty('weather');
  });
});
```

## 10. Performance Requirements

### 10.1 Response Time Targets
- **Calendar Month View**: < 200ms
- **Daily Newspaper View**: < 500ms
- **Chat Response**: < 2000ms
- **Data Sync**: Background process, non-blocking

### 10.2 Optimization Strategies
- **Database Indexes**: Date-based indexes for calendar queries
- **Caching**: Daily summaries cached for 24 hours
- **Lazy Loading**: Module data loaded on demand
- **Pagination**: Large datasets paginated for performance

## 11. Security Considerations

### 11.1 MVP Security Measures
- **Local-only deployment** - no network exposure by default
- **Configuration file security** - API keys in environment variables
- **Input validation** - all API inputs validated and sanitized
- **SQL injection prevention** - parameterized queries only

### 11.2 Future Security Enhancements
- **Encryption at rest** for sensitive data
- **API key rotation** mechanisms
- **Access logging** for audit trails
- **Rate limiting** for API endpoints

This development specification provides a comprehensive technical foundation for building Lifeboard MVP while maintaining the flexibility for future enhancements and community contributions.