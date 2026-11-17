# Space Fractions: Architecture Documentation

## Section A: Executive Summary
Space Fractions is an interactive educational math application designed for 6th-grade students to master fractions (addition, subtraction, comparison, and simplification) through a gamified space exploration theme. Players pilot a starship through asteroid fields and alien encounters where solving fraction problems fuels the ship's engines and shields. The user journey features an intro movie setting up the mission, a main menu for level selection, dynamic interactive questions, and a victory ending scene with rank evaluation.

The system aims to provide engaging, pedagogically sound arithmetic drills with immediate feedback, progress tracking, and administrative capabilities for educators to curate question banks and monitor class performance.

## Section B: Risks & Mitigations
| Risk ID | Description | Severity | Probability | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| RSK-01 | Student disengagement due to repetitive questions | High | Medium | Dynamic algorithmic question generation and adaptive difficulty scaling |
| RSK-02 | Network latency during classroom-wide simultaneous play | Medium | High | Local state caching, optimistic UI updates, and lightweight API payloads |
| RSK-03 | Math rendering and fraction input parsing ambiguity | High | Low | Structured fraction representations (numerator/denominator pairs) and strict input validation |
| RSK-04 | Overly complex deployment infrastructure causing classroom outage | Medium | Medium | Self-contained modular architecture with fallback single-node execution |

## Section C: Quality Attribute Mapping
| Attribute | Goal | Measure | Contradiction / Note |
| :--- | :--- | :--- | :--- |
| Availability | 99.99% uptime | Annual downtime < 52.6 minutes | Contradicts the specified 1% monthly error budget allowance below |
| Reliability | 1% error budget | Max 1% failed requests per calendar month | Note: 1% error budget corresponds to 99.0% availability, not 99.99% |
| Latency | Sub-200ms response | 95th percentile response time for question verification | Target under standard school network conditions |
| Usability | 6th-grade accessibility | 90% task success rate without adult intervention | Simplified UI controls, clear fraction visualizers |

## Section D: Traceability Matrix
| Req ID | Requirement Description | Category | Architectural Component | Verification Method | Deliverable Artifact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| FR-01 | Play fraction game with intro movie, menu, questions, and victory ending | Functional | GameComponent | Automated E2E Test | src/game/ |
| FR-02 | Generate and check fraction arithmetic (add, sub, compare, simplify) | Functional | QuestionComponent | Unit & Property Tests | src/question/ |
| FR-03 | Record, aggregate, and view player high scores and session history | Functional | ScoreComponent | Integration Test | src/score/ |
| FR-04 | Provide help screens explaining fraction rules and game controls | Functional | GameComponent | Manual Inspection | src/game/help.py |
| FR-05 | Educator administration portal to create, update, and delete questions | Functional | AdminComponent | API Integration Test | src/admin/ |
| FR-06 | User authentication and classroom profile management | Functional | UserComponent | Unit & API Tests | src/user/ |
| FR-07 | Multi-student live multiplayer fleet race mode | Functional |  |  |  |
| NFR-01 | API responses must return in under 200ms | Non-Functional | GameGateway | Performance Benchmark | tests/perf/ |
| NFR-02 | RESTful API conforming to OpenAPI 3.0 specifications | Non-Functional | API Layer | Schema Validation | openapi.yaml |
| NFR-03 | Zero-data loss with automated failover and geo-redundancy | Non-Functional |  |  |  |
| ASR-01 | Persist question bank and game progress in relational schema | Architectural | Database Layer | Migration Test | sql/question_ddl.sql |
| ASR-02 | High-throughput low-latency inter-service communication | Architectural | RPC Layer | Contract Test | internal.proto |

## Section E: Components
### Component 1: GameComponent
- **Name**: `GameComponent`
- **Responsibilities**: Orchestrates game session lifecycle, state machine transitions (Idle, Playing, Paused, GameOver), scoring calculations, and student feedback dialogues.
- **Tech Options Considered**: FastAPI, Django, Flask, Express.js.
- **Recommended Stack**: FastAPI (Python 3.11+) with Pydantic v2 for high performance, async capabilities, and automatic OpenAPI documentation.
- **API Contracts**: REST API over HTTP/JSON exposed at `/api/v1/game/*`.
- **Data Schema**: Manages in-memory active game sessions and persists completed sessions to `game_sessions` table.

*(Note: While AdminComponent and UserComponent are referenced across diagrams and traceability, detailed implementation specifications for AdminComponent and UserComponent are deferred in this document section to GameComponent's integrated modular scope).*

## Section F: API Contracts
```yaml
openapi: 3.0.3
info:
  title: Space Fractions API
  description: Educational fractions gameplay, question management, and scoring engine.
  version: 1.0.0
servers:
  - url: http://localhost:8000/api/v1
paths:
  /game/start:
    post:
      summary: Start a new game session
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [player_name]
              properties:
                player_name:
                  type: string
                  example: "CosmoPilot"
      responses:
        '200':
          description: Session created
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                  player_name:
                    type: string
                  status:
                    type: string
  /game/question:
    get:
      summary: Get the next fraction question for an active session
      parameters:
        - name: session_id
          in: query
          required: true
          schema:
            type: string
        - name: operation
          in: query
          required: false
          schema:
            type: string
            enum: [add, subtract, compare, simplify]
      responses:
        '200':
          description: Next question generated
  /game/answer:
    post:
      summary: Submit player answer for verification
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [session_id, question_id, answer]
              properties:
                session_id:
                  type: string
                question_id:
                  type: string
                answer:
                  type: string
      responses:
        '200':
          description: Answer verification result
  /scores:
    get:
      summary: Retrieve leaderboard and high scores
      responses:
        '200':
          description: List of top scores
  /admin/questions:
    get:
      summary: List custom questions (Admin)
      responses:
        '200':
          description: Question list
    post:
      summary: Create custom fraction question (Admin)
      responses:
        '201':
          description: Question created
```

## Section G: Data Schemas & Contracts
### gRPC Protocol Buffers
```proto
syntax = "proto3";

package spacefractions;

service GameService {
  rpc StartGame (StartGameRequest) returns (StartGameResponse);
  rpc SubmitAnswer (SubmitAnswerRequest) returns (SubmitAnswerResponse);
  rpc EndGame (EndGameRequest) returns (EndGameResponse);
}

service QuestionService {
  rpc GenerateQuestion (GenerateQuestionRequest) returns (QuestionResponse);
  rpc ValidateAnswer (ValidateAnswerRequest) returns (ValidateAnswerResponse);
}

message StartGameRequest {
  string player_name = 1;
}

message StartGameResponse {
  string session_id = 1;
  string status = 2;
  int64 start_time = 3;
}

message SubmitAnswerRequest {
  string session_id = 1;
  string question_id = 2;
  string answer = 3;
}

message SubmitAnswerResponse {
  bool correct = 1;
  int32 score_delta = 2;
  string explanation = 3;
}

message EndGameRequest {
  string session_id = 1;
}

message EndGameResponse {
  int32 final_score = 1;
  int32 questions_answered = 2;
  int32 correct_count = 3;
}

message GenerateQuestionRequest {
  string operation_type = 1;
  int32 difficulty_level = 2;
}

message QuestionResponse {
  string question_id = 1;
  string prompt = 2;
  string fraction_a = 3;
  string fraction_b = 4;
  string operation = 5;
  string expected_answer = 6;
}

message ValidateAnswerRequest {
  string question_id = 1;
  string submitted_answer = 2;
  string expected_answer = 3;
}

message ValidateAnswerResponse {
  bool is_valid = 1;
}
```

### SQL DDL
```sql
-- DDL for Space Fractions Persistence Layer

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(36) PRIMARY KEY,
    operation VARCHAR(20) NOT NULL,
    fraction_a VARCHAR(20) NOT NULL,
    fraction_b VARCHAR(20),
    correct_answer VARCHAR(20) NOT NULL,
    explanation TEXT,
    difficulty INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    player_name VARCHAR(50) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'Playing',
    score INT NOT NULL DEFAULT 0,
    questions_attempted INT NOT NULL DEFAULT 0,
    questions_correct INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS scores (
    id VARCHAR(36) PRIMARY KEY,
    player_name VARCHAR(50) NOT NULL,
    score INT NOT NULL,
    accuracy FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Section H: Infrastructure & Deployment
The document originally proposed a high-complexity distributed architecture:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: space-fractions-cluster
  labels:
    app: space-fractions
spec:
  replicas: 10
  selector:
    matchLabels:
      app: space-fractions
  template:
    metadata:
      labels:
        app: space-fractions
    spec:
      containers:
        - name: game-service
          image: spacefractions/game-service:latest
          ports:
            - containerPort: 8000
          env:
            - name: RABBITMQ_HOST
              value: "rabbitmq-cluster.infrastructure.svc.cluster.local"
            - name: ELASTICSEARCH_URL
              value: "http://elasticsearch-cluster.infrastructure.svc.cluster.local:9200"
            - name: JENKINS_WEBHOOK
              value: "http://jenkins-ci.infrastructure.svc.cluster.local"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq-broker
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: rabbitmq
          image: rabbitmq:3.12-management
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch-node
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: elasticsearch
          image: elasticsearch:8.10.0
```

## Section I: Security Architecture
- Role-based Access Control (RBAC): Differentiates between `student` (gameplay and read-only scoreboards) and `educator`/`admin` (question creation, editing, student diagnostics).
- Input Validation: Strict fraction syntax verification (e.g., regex `^-?[0-9]+/[1-9][0-9]*$` or whole integers) to eliminate injection vulnerabilities.
- Data Protection: Classroom student data anonymization by default.

## Section J: Observability & Reliability
- Service Level Objectives (SLOs): 95% of gameplay requests answered under 200ms.
- Disaster Recovery: Recovery Time Objective (RTO) ≤ 1 hour, Recovery Point Objective (RPO) ≤ 15 minutes.
- Health Monitoring: Standard `/healthz` and `/metrics` endpoints.

## Section K: Testing Matrix
| Component / Module | Unit Test | Integration Test | E2E Test | Performance Test |
| :--- | :--- | :--- | :--- | :--- |
| Question Calculation Engine | Automated pytest | Verified |  | Skipped |
| Game State Machine | Verified | Verified | Manual |  |
| Admin Question CRUD | Verified |  |  |  |
| Score Leaderboard API | Verified | Verified |  | Skipped |
| User Authentication |  |  |  |  |

*(Note: Multiple cells in this matrix were left empty during initial architecture drafting).*

## Section L: Deliverables, Tradeoffs, Assumptions & Open Questions
### Deliverables List
1. Runnable project source code structure (`src/` with Game, Question, Score, Admin modules).
2. Dependency manifest (`requirements.txt`).
3. OpenAPI Specification (`openapi.yaml`).
4. Protocol Buffer definition (`internal.proto`).
5. Database Schemas (`sql/game_ddl.sql`). *(Note mismatch: Traceability Matrix specifies `sql/question_ddl.sql`)*.
6. Deployment manifest (`k8s/deployment.yaml`).
7. Complete Traceability Matrix (`traceability_matrix.csv`).
8. Architecture Documentation (`architecture.md`).
9. Automated Test Suite (`tests/` with pytest).
10. System README (`README.md`).

### Architecture Trade-offs & Rationalization
- **Microservices vs. Modular Monolith**: The draft deployment specifies RabbitMQ, Elasticsearch clusters, and distributed microservices for a 6th-grade fractions game. This constitutes extreme over-engineering that introduces unnecessary points of failure and prohibitive operational overhead for school environments. A cohesive modular monolith (FastAPI service with discrete internal modules for Game, Question, Score, and Admin) preserves clean boundaries while allowing zero-dependency local execution.

### Assumptions & Open Questions
- Question format accepts both simplified fractions and equivalent fractions (with pedagogical feedback).
- Database defaults to lightweight SQLite for self-contained out-of-the-box execution, with schema compatible with PostgreSQL.
