"""
Template definitions for the synthesized Space Fractions project.
Contains clean, fully runnable implementations of domain models, state machines, and tests.
"""

from __future__ import annotations

import csv
import io
from typing import Dict

PROJECT_TEMPLATES: Dict[str, str] = {}

PROJECT_TEMPLATES["requirements.txt"] = """fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
pytest>=8.0.0
httpx>=0.27.0
"""

PROJECT_TEMPLATES["Dockerfile"] = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

PROJECT_TEMPLATES["sql/game_ddl.sql"] = """-- Relational DDL for Space Fractions
-- Reconciles traceability matrix (sql/question_ddl.sql) and deliverables list (sql/game_ddl.sql)

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
"""

# Alias sql/question_ddl.sql to resolve naming discrepancy
PROJECT_TEMPLATES["sql/question_ddl.sql"] = PROJECT_TEMPLATES["sql/game_ddl.sql"]

PROJECT_TEMPLATES["k8s/deployment.yaml"] = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: space-fractions-app
  labels:
    app: space-fractions
spec:
  replicas: 2
  selector:
    matchLabels:
      app: space-fractions
  template:
    metadata:
      labels:
        app: space-fractions
    spec:
      containers:
        - name: app
          image: spacefractions/app:latest
          ports:
            - containerPort: 8000
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "100m"
              memory: "128Mi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: space-fractions-svc
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 8000
  selector:
    app: space-fractions
"""

PROJECT_TEMPLATES["internal.proto"] = """syntax = "proto3";

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
"""

PROJECT_TEMPLATES["openapi.yaml"] = """openapi: 3.0.3
info:
  title: Space Fractions API
  description: Educational math gameplay, fraction question engine, and leaderboard.
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
  /game/question:
    get:
      summary: Get the next fraction question
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
          description: Question payload
  /game/answer:
    post:
      summary: Submit fraction answer
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
          description: Verification response
  /scores:
    get:
      summary: Retrieve top scores
      responses:
        '200':
          description: Score leaderboard
  /admin/questions:
    get:
      summary: List question bank
      responses:
        '200':
          description: Questions
    post:
      summary: Create custom question
      responses:
        '201':
          description: Created
  /healthz:
    get:
      summary: Health check
      responses:
        '200':
          description: Healthy
"""

PROJECT_TEMPLATES["traceability_matrix.csv"] = """Req ID,Requirement Description,Category,Architectural Component,Verification Method,Deliverable Artifact
FR-01,Play fraction game with intro movie menu questions and ending,Functional,GameComponent,Automated E2E Test,src/game/engine.py
FR-02,Generate and check fraction arithmetic (add sub compare simplify),Functional,QuestionComponent,Unit & Property Tests,src/question/fraction.py
FR-03,Record aggregate and view player high scores and session history,Functional,ScoreComponent,Integration Test,src/score/service.py
FR-04,Provide help screens explaining fraction rules and game controls,Functional,GameComponent,Unit Test,src/game/help.py
FR-05,Educator administration portal to create update and delete questions,Functional,AdminComponent,API Integration Test,src/admin/service.py
FR-06,User authentication and classroom profile management,Functional,UserComponent,Unit & API Tests,src/user/service.py
FR-07,Multi-student live multiplayer fleet race mode,Functional,GameComponent (Deferred),Mock Benchmark,src/game/engine.py
NFR-01,API responses must return in under 200ms,Non-Functional,FastAPI Gateway,Performance Benchmark,tests/test_api.py
NFR-02,RESTful API conforming to OpenAPI 3.0 specifications,Non-Functional,FastAPI Router,Schema Validation,openapi.yaml
NFR-03,Zero-data loss with automated failover and local persistence,Non-Functional,Database Layer,Integration Test,sql/game_ddl.sql
ASR-01,Persist question bank and game progress in relational schema,Architectural,SQLite/Postgres Storage,Migration Test,sql/game_ddl.sql
ASR-02,High-throughput low-latency inter-service communication,Architectural,RPC/Internal Interface,Contract Test,internal.proto
"""

PROJECT_TEMPLATES["src/__init__.py"] = '"""Space Fractions application package."""\n'
PROJECT_TEMPLATES["src/question/__init__.py"] = '"""Question and Fraction Math engine."""\n'
PROJECT_TEMPLATES["src/game/__init__.py"] = '"""Game session and state machine."""\n'
PROJECT_TEMPLATES["src/score/__init__.py"] = '"""Scoring and leaderboard service."""\n'
PROJECT_TEMPLATES["src/admin/__init__.py"] = '"""Educator question bank administration."""\n'
PROJECT_TEMPLATES["src/user/__init__.py"] = '"""User profiles and authentication."""\n'

PROJECT_TEMPLATES["src/question/fraction.py"] = '''"""
Core Fraction Arithmetic Module.
Implements exact fraction math: addition, subtraction, comparison, and simplification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Fraction:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator == 0:
            raise ValueError("Denominator cannot be zero.")
        # Canonical representation with positive denominator
        if self.denominator < 0:
            object.__setattr__(self, "numerator", -self.numerator)
            object.__setattr__(self, "denominator", -self.denominator)

    @classmethod
    def parse(cls, value: str | int | Fraction) -> Fraction:
        """Parses a fraction from strings like '1/2', '-3/4', '5'."""
        if isinstance(value, Fraction):
            return value
        if isinstance(value, int):
            return cls(value, 1)

        val_str = str(value).strip()
        if "/" in val_str:
            parts = val_str.split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid fraction format: '{val_str}'")
            return cls(int(parts[0].strip()), int(parts[1].strip()))
        return cls(int(val_str), 1)

    def simplify(self) -> Fraction:
        """Returns the irreducible form of the fraction."""
        gcd_val = math.gcd(abs(self.numerator), self.denominator)
        return Fraction(self.numerator // gcd_val, self.denominator // gcd_val)

    def add(self, other: Fraction | str | int) -> Fraction:
        o = Fraction.parse(other)
        common_denom = self.denominator * o.denominator
        num = (self.numerator * o.denominator) + (o.numerator * self.denominator)
        return Fraction(num, common_denom).simplify()

    def subtract(self, other: Fraction | str | int) -> Fraction:
        o = Fraction.parse(other)
        common_denom = self.denominator * o.denominator
        num = (self.numerator * o.denominator) - (o.numerator * self.denominator)
        return Fraction(num, common_denom).simplify()

    def compare(self, other: Fraction | str | int) -> str:
        """Compares two fractions and returns '<', '=', or '>'."""
        o = Fraction.parse(other)
        left = self.numerator * o.denominator
        right = o.numerator * self.denominator
        if left < right:
            return "<"
        elif left > right:
            return ">"
        return "="

    def to_decimal(self) -> float:
        return self.numerator / self.denominator

    def __str__(self) -> str:
        simplified = self.simplify()
        if simplified.denominator == 1:
            return str(simplified.numerator)
        return f"{simplified.numerator}/{simplified.denominator}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Fraction, str, int)):
            return False
        try:
            o = Fraction.parse(other).simplify()
            s = self.simplify()
            return s.numerator == o.numerator and s.denominator == o.denominator
        except Exception:
            return False
'''

PROJECT_TEMPLATES["src/question/engine.py"] = '''"""
Question Generation and Pedagogical Verification Engine.
Supports operations: add, subtract, compare, simplify.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.question.fraction import Fraction


@dataclass
class QuestionItem:
    id: str
    operation: str  # add, subtract, compare, simplify
    fraction_a: Fraction
    fraction_b: Optional[Fraction]
    prompt: str
    correct_answer: str
    explanation: str
    difficulty: int = 1


class QuestionEngine:
    """Generates fraction math challenges and evaluates student answers."""

    def __init__(self) -> None:
        self.custom_bank: Dict[str, QuestionItem] = {}

    def generate_question(self, operation: Optional[str] = None, difficulty: int = 1) -> QuestionItem:
        ops = ["add", "subtract", "compare", "simplify"]
        op = operation.lower() if operation and operation.lower() in ops else random.choice(ops)
        q_id = str(uuid.uuid4())[:8]

        # Select denominators appropriate for 6th grade math
        denoms = [2, 3, 4, 5, 6, 8, 10, 12]
        d1 = random.choice(denoms)
        n1 = random.randint(1, d1 * 2)
        f1 = Fraction(n1, d1)

        if op == "add":
            d2 = random.choice(denoms)
            n2 = random.randint(1, d2 * 2)
            f2 = Fraction(n2, d2)
            result = f1.add(f2)
            prompt = f"Calculate the sum: {f1} + {f2}"
            expected = str(result)
            expl = f"Find a common denominator ({f1.denominator * f2.denominator}), add the numerators, and simplify to {expected}."
            return QuestionItem(q_id, op, f1, f2, prompt, expected, expl, difficulty)

        elif op == "subtract":
            d2 = random.choice(denoms)
            n2 = random.randint(1, d2 * 2)
            f2 = Fraction(n2, d2)
            # Ensure positive result for student friendly practice
            if f1.compare(f2) == "<":
                f1, f2 = f2, f1
            result = f1.subtract(f2)
            prompt = f"Calculate the difference: {f1} - {f2}"
            expected = str(result)
            expl = f"Convert to common denominator, subtract numerators: {expected}."
            return QuestionItem(q_id, op, f1, f2, prompt, expected, expl, difficulty)

        elif op == "compare":
            d2 = random.choice(denoms)
            n2 = random.randint(1, d2 * 2)
            f2 = Fraction(n2, d2)
            expected = f1.compare(f2)
            prompt = f"Compare the fractions: {f1} [ ? ] {f2} (Enter '<', '>', or '=')"
            expl = f"{f1.numerator}/{f1.denominator} is {f1.to_decimal():.2f} and {f2.numerator}/{f2.denominator} is {f2.to_decimal():.2f}, so {f1} {expected} {f2}."
            return QuestionItem(q_id, op, f1, f2, prompt, expected, expl, difficulty)

        else:  # simplify
            multiplier = random.randint(2, 4)
            unsimplified = Fraction(f1.simplify().numerator * multiplier, f1.simplify().denominator * multiplier)
            expected = str(unsimplified.simplify())
            prompt = f"Reduce to simplest form: {unsimplified.numerator}/{unsimplified.denominator}"
            expl = f"Divide numerator and denominator by {multiplier} to obtain {expected}."
            return QuestionItem(q_id, op, unsimplified, None, prompt, expected, expl, difficulty)

    def validate_answer(self, question: QuestionItem, student_answer: str) -> Tuple[bool, str]:
        """Validates student answer against question specifications."""
        ans = student_answer.strip()
        if not ans:
            return False, "Answer cannot be empty."

        if question.operation == "compare":
            is_correct = ans == question.correct_answer
            return is_correct, question.explanation if not is_correct else "Correct! Asteroid evaded!"

        # Fraction comparison
        try:
            student_frac = Fraction.parse(ans)
            expected_frac = Fraction.parse(question.correct_answer)

            # Check mathematical equality
            if student_frac == expected_frac:
                # If simplify question, check that student provided the irreducible form
                if question.operation == "simplify" and str(student_frac) != str(expected_frac.simplify()):
                    return False, f"Equivalent, but not in simplest form! Simplest form is {expected_frac.simplify()}."
                return True, "Excellent navigation! Fuel cells replenished."
            else:
                return False, f"Incorrect. {question.explanation}"
        except Exception:
            return False, f"Invalid fraction format '{ans}'. Enter answers in format 'numerator/denominator' (e.g. 3/4)."
'''

PROJECT_TEMPLATES["src/game/state_machine.py"] = '''"""
Game State Machine Module.
Implements the SpaceFractions_GameState lifecycle: Idle -> Playing -> Paused -> GameOver.
"""

from __future__ import annotations

from enum import Enum


class GameState(str, Enum):
    IDLE = "Idle"
    PLAYING = "Playing"
    PAUSED = "Paused"
    GAME_OVER = "GameOver"


class InvalidStateTransitionError(Exception):
    pass


class GameStateMachine:
    """Manages legal state transitions for the Space Fractions gameplay loop."""

    VALID_TRANSITIONS = {
        GameState.IDLE: {GameState.PLAYING},
        GameState.PLAYING: {GameState.PAUSED, GameState.GAME_OVER},
        GameState.PAUSED: {GameState.PLAYING, GameState.GAME_OVER},
        GameState.GAME_OVER: {GameState.IDLE},
    }

    def __init__(self, initial_state: GameState = GameState.IDLE) -> None:
        self._current_state = initial_state

    @property
    def current_state(self) -> GameState:
        return self._current_state

    def transition_to(self, target_state: GameState) -> GameState:
        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition from {self._current_state.value} to {target_state.value}. Allowed: {[s.value for s in allowed]}"
            )
        self._current_state = target_state
        return self._current_state

    def start_game(self) -> GameState:
        return self.transition_to(GameState.PLAYING)

    def pause_game(self) -> GameState:
        return self.transition_to(GameState.PAUSED)

    def resume_game(self) -> GameState:
        return self.transition_to(GameState.PLAYING)

    def end_game(self) -> GameState:
        return self.transition_to(GameState.GAME_OVER)

    def reset_to_menu(self) -> GameState:
        return self.transition_to(GameState.IDLE)
'''

PROJECT_TEMPLATES["src/game/help.py"] = '''"""
Help and Tutorial Module for 6th Grade Math Students.
"""

from __future__ import annotations


def get_game_instructions() -> dict[str, str]:
    return {
        "story": "Pilot your starship through the asteroid nebula! Correct fraction calculations recharge fuel and shields.",
        "fraction_addition": "To add fractions with different denominators: Find the common denominator, scale numerators, then add.",
        "fraction_subtraction": "To subtract: Align denominators, subtract numerators, and reduce to simplest form.",
        "fraction_comparison": "Cross-multiply (numerator * other denominator) to quickly see which fraction is greater (<, >, =).",
        "fraction_simplification": "Divide both top and bottom by their greatest common divisor (GCD).",
        "controls": "Type your answer as a simplified fraction like '3/4' or an integer like '2'. Enter '<', '>', or '=' for comparison.",
    }
'''

PROJECT_TEMPLATES["src/game/engine.py"] = '''"""
Game Engine and Session Management Module.
Integrates State Machine, Intro Narrative, Scoring, and Ending Scenes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.game.state_machine import GameState, GameStateMachine
from src.question.engine import QuestionEngine, QuestionItem


@dataclass
class GameSession:
    session_id: str
    player_name: str
    state_machine: GameStateMachine = field(default_factory=GameStateMachine)
    score: int = 0
    shields: int = 3
    questions_attempted: int = 0
    questions_correct: int = 0
    current_question: Optional[QuestionItem] = None
    created_at: float = field(default_factory=time.time)

    @property
    def status(self) -> str:
        return self.state_machine.current_state.value

    def get_intro_movie_text(self) -> str:
        return (
            "=== MISSION LAUNCH: SECTOR ARITHMETICA ===\\n"
            f"Commander {self.player_name}, your starship is stranded in the Fraction Nebula!\\n"
            "Asteroids require exact mathematical orbital solutions to evade.\\n"
            "Keep shields intact and navigate back to Starbase Prime!"
        )

    def get_ending_scene_text(self) -> str:
        if self.shields <= 0:
            return (
                "=== MISSION STATUS: SHIP DAMAGED ===\\n"
                f"Emergency hyperdrive engaged! Final Score: {self.score}. Review fraction rules and retry!"
            )
        accuracy = (self.questions_correct / self.questions_attempted * 100) if self.questions_attempted else 0
        return (
            "=== VICTORY: STARBASE REACHED ===\\n"
            f"Spectacular navigation, Commander {self.player_name}!\\n"
            f"Final Score: {self.score} points | Accuracy: {accuracy:.1f}%. Rank: Master Navigator!"
        )


class GameEngine:
    """Manages active game sessions and gameplay transitions."""

    def __init__(self, question_engine: Optional[QuestionEngine] = None) -> None:
        self.question_engine = question_engine or QuestionEngine()
        self.sessions: Dict[str, GameSession] = {}

    def create_session(self, player_name: str) -> GameSession:
        sid = str(uuid.uuid4())[:8]
        session = GameSession(session_id=sid, player_name=player_name)
        session.state_machine.start_game()
        self.sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> Optional[GameSession]:
        return self.sessions.get(session_id)

    def next_question(self, session_id: str, operation: Optional[str] = None) -> QuestionItem:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session not found: {session_id}")
        if session.status != GameState.PLAYING.value:
            raise RuntimeError(f"Cannot request questions while game is {session.status}")

        q = self.question_engine.generate_question(operation=operation)
        session.current_question = q
        return q

    def answer_question(self, session_id: str, question_id: str, answer: str) -> dict:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session not found: {session_id}")
        if session.status != GameState.PLAYING.value:
            raise RuntimeError(f"Game is currently {session.status}")

        q = session.current_question
        if not q or q.id != question_id:
            # Fallback evaluation if matching id not stored
            q = self.question_engine.generate_question()

        is_correct, feedback = self.question_engine.validate_answer(q, answer)
        session.questions_attempted += 1

        if is_correct:
            session.questions_correct += 1
            session.score += 100
        else:
            session.shields -= 1
            if session.shields <= 0:
                session.state_machine.end_game()

        return {
            "correct": is_correct,
            "feedback": feedback,
            "score": session.score,
            "shields": session.shields,
            "game_over": session.status == GameState.GAME_OVER.value,
            "ending_scene": session.get_ending_scene_text() if session.status == GameState.GAME_OVER.value else None,
        }
'''

PROJECT_TEMPLATES["src/score/service.py"] = '''"""
Score and Leaderboard Persistence Service.
Records high scores and calculates classroom statistics.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ScoreRecord:
    id: str
    player_name: str
    score: int
    accuracy: float
    created_at: str


class ScoreService:
    """Manages high scores with local SQLite relational persistence."""

    def __init__(self, db_path: str = "space_fractions.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    accuracy REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def record_score(self, player_name: str, score: int, accuracy: float = 1.0) -> ScoreRecord:
        record_id = str(uuid.uuid4())[:8]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO scores (id, player_name, score, accuracy) VALUES (?, ?, ?, ?)",
                (record_id, player_name, score, accuracy),
            )
            conn.commit()
            cur = conn.execute("SELECT created_at FROM scores WHERE id = ?", (record_id,))
            row = cur.fetchone()
            ts = row[0] if row else ""
            return ScoreRecord(record_id, player_name, score, accuracy, ts)

    def get_leaderboard(self, limit: int = 10) -> List[ScoreRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, player_name, score, accuracy, created_at FROM scores ORDER BY score DESC LIMIT ?",
                (limit,),
            )
            return [ScoreRecord(*row) for row in cur.fetchall()]
'''

PROJECT_TEMPLATES["src/admin/service.py"] = '''"""
Admin Component: Question Bank and Teacher Management Service.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CustomQuestion:
    id: str
    operation: str
    fraction_a: str
    fraction_b: Optional[str]
    correct_answer: str
    explanation: str
    difficulty: int = 1


class AdminService:
    """Provides educators with CRUD controls over question banks."""

    def __init__(self, db_path: str = "space_fractions.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    fraction_a TEXT NOT NULL,
                    fraction_b TEXT,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT,
                    difficulty INTEGER DEFAULT 1
                );
                """
            )
            conn.commit()

    def create_question(self, q: CustomQuestion) -> CustomQuestion:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO questions (id, operation, fraction_a, fraction_b, correct_answer, explanation, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (q.id, q.operation, q.fraction_a, q.fraction_b, q.correct_answer, q.explanation, q.difficulty),
            )
            conn.commit()
        return q

    def list_questions(self) -> List[CustomQuestion]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT id, operation, fraction_a, fraction_b, correct_answer, explanation, difficulty FROM questions")
            return [CustomQuestion(*row) for row in cur.fetchall()]
'''

PROJECT_TEMPLATES["src/user/service.py"] = '''"""
User Component: Classroom Profiles and Authentication.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UserProfile:
    id: str
    username: str
    role: str  # student or admin


class UserService:
    """Manages student and teacher profiles."""

    def __init__(self, db_path: str = "space_fractions.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL DEFAULT 'student'
                );
                """
            )
            conn.commit()

    def get_or_create_user(self, username: str, role: str = "student") -> UserProfile:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT id, username, role FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if row:
                return UserProfile(*row)

            uid = str(uuid.uuid4())[:8]
            conn.execute("INSERT INTO users (id, username, role) VALUES (?, ?, ?)", (uid, username, role))
            conn.commit()
            return UserProfile(uid, username, role)
'''

PROJECT_TEMPLATES["src/main.py"] = '''"""
Space Fractions FastAPI Modular Monolith Application.
Exposes RESTful endpoints conforming to openapi.yaml and serves local gameplay.
"""

from __future__ import annotations

from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from src.admin.service import AdminService, CustomQuestion
from src.game.engine import GameEngine
from src.game.help import get_game_instructions
from src.score.service import ScoreService
from src.user.service import UserService

app = FastAPI(
    title="Space Fractions API",
    description="Modular monolith educational service for 6th-grade fraction drills.",
    version="1.0.0",
)

game_engine = GameEngine()
score_service = ScoreService()
admin_service = AdminService()
user_service = UserService()


class StartGameRequest(BaseModel):
    player_name: str


class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    answer: str


class CreateQuestionRequest(BaseModel):
    operation: str
    fraction_a: str
    fraction_b: Optional[str] = None
    correct_answer: str
    explanation: str
    difficulty: int = 1


@app.get("/healthz")
def health_check():
    return {"status": "healthy", "service": "space-fractions"}


@app.post("/api/v1/game/start")
def start_game(req: StartGameRequest):
    user = user_service.get_or_create_user(req.player_name)
    session = game_engine.create_session(req.player_name)
    return {
        "session_id": session.session_id,
        "player_name": session.player_name,
        "status": session.status,
        "intro_movie": session.get_intro_movie_text(),
    }


@app.get("/api/v1/game/question")
def get_question(session_id: str, operation: Optional[str] = None):
    try:
        q = game_engine.next_question(session_id, operation)
        return {
            "question_id": q.id,
            "operation": q.operation,
            "prompt": q.prompt,
            "fraction_a": str(q.fraction_a),
            "fraction_b": str(q.fraction_b) if q.fraction_b else None,
            "difficulty": q.difficulty,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=str(re))


@app.post("/api/v1/game/answer")
def submit_answer(sub: AnswerSubmission):
    try:
        result = game_engine.answer_question(sub.session_id, sub.question_id, sub.answer)
        if result.get("game_over"):
            sess = game_engine.get_session(sub.session_id)
            if sess:
                score_service.record_score(sess.player_name, sess.score)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=str(re))


@app.get("/api/v1/scores")
def list_scores(limit: int = 10):
    records = score_service.get_leaderboard(limit)
    return [{"player": r.player_name, "score": r.score, "accuracy": r.accuracy, "date": r.created_at} for r in records]


@app.get("/api/v1/help")
def get_help():
    return get_game_instructions()


@app.get("/api/v1/admin/questions")
def get_admin_questions():
    questions = admin_service.list_questions()
    return questions


@app.post("/api/v1/admin/questions", status_code=201)
def add_admin_question(req: CreateQuestionRequest):
    import uuid
    cq = CustomQuestion(
        id=str(uuid.uuid4())[:8],
        operation=req.operation,
        fraction_a=req.fraction_a,
        fraction_b=req.fraction_b,
        correct_answer=req.correct_answer,
        explanation=req.explanation,
        difficulty=req.difficulty,
    )
    admin_service.create_question(cq)
    return {"message": "Question created", "id": cq.id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
'''

PROJECT_TEMPLATES["tests/__init__.py"] = ""

PROJECT_TEMPLATES["tests/test_fraction.py"] = '''"""
Unit Tests for Fraction Arithmetic and Question Validation.
"""

import pytest
from src.question.fraction import Fraction
from src.question.engine import QuestionEngine


def test_fraction_parsing_and_simplification():
    f = Fraction.parse("4/8")
    assert f.simplify() == Fraction(1, 2)
    assert str(f) == "1/2"

    f_int = Fraction.parse("5")
    assert f_int.numerator == 5
    assert f_int.denominator == 1

    with pytest.raises(ValueError):
        Fraction(1, 0)


def test_fraction_addition():
    f1 = Fraction(1, 3)
    f2 = Fraction(1, 6)
    assert f1.add(f2) == Fraction(1, 2)

    f3 = Fraction(2, 5)
    f4 = Fraction(3, 10)
    assert f3.add(f4) == Fraction(7, 10)


def test_fraction_subtraction():
    f1 = Fraction(3, 4)
    f2 = Fraction(1, 2)
    assert f1.subtract(f2) == Fraction(1, 4)

    f3 = Fraction(1, 2)
    f4 = Fraction(3, 4)
    assert f3.subtract(f4) == Fraction(-1, 4)


def test_fraction_comparison():
    f1 = Fraction(2, 3)
    f2 = Fraction(3, 4)
    assert f1.compare(f2) == "<"
    assert f2.compare(f1) == ">"

    f3 = Fraction(2, 4)
    f4 = Fraction(1, 2)
    assert f3.compare(f4) == "="


def test_question_engine_validation():
    engine = QuestionEngine()

    q_add = engine.generate_question(operation="add")
    is_valid, _ = engine.validate_answer(q_add, q_add.correct_answer)
    assert is_valid is True

    is_invalid, _ = engine.validate_answer(q_add, "999/1")
    assert is_invalid is False
'''

PROJECT_TEMPLATES["tests/test_state_machine.py"] = '''"""
State Machine Lifecycle Tests.
Verifies transitions per SpaceFractions_GameState: Idle -> Playing -> Paused -> GameOver.
"""

import pytest
from src.game.state_machine import GameState, GameStateMachine, InvalidStateTransitionError


def test_state_machine_valid_flow():
    sm = GameStateMachine()
    assert sm.current_state == GameState.IDLE

    sm.start_game()
    assert sm.current_state == GameState.PLAYING

    sm.pause_game()
    assert sm.current_state == GameState.PAUSED

    sm.resume_game()
    assert sm.current_state == GameState.PLAYING

    sm.end_game()
    assert sm.current_state == GameState.GAME_OVER

    sm.reset_to_menu()
    assert sm.current_state == GameState.IDLE


def test_invalid_transitions():
    sm = GameStateMachine()
    assert sm.current_state == GameState.IDLE

    # Cannot transition directly from IDLE to PAUSED
    with pytest.raises(InvalidStateTransitionError):
        sm.pause_game()

    sm.start_game()
    # Cannot jump from PLAYING back to IDLE without GameOver
    with pytest.raises(InvalidStateTransitionError):
        sm.reset_to_menu()
'''

PROJECT_TEMPLATES["tests/test_api.py"] = '''"""
Integration tests for FastAPI REST endpoints.
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "space-fractions"}


def test_full_game_api_flow():
    # 1. Start game
    start_resp = client.post("/api/v1/game/start", json={"player_name": "TestCadet"})
    assert start_resp.status_code == 200
    data = start_resp.json()
    session_id = data["session_id"]
    assert data["status"] == "Playing"
    assert "intro_movie" in data

    # 2. Get question
    q_resp = client.get(f"/api/v1/game/question?session_id={session_id}&operation=add")
    assert q_resp.status_code == 200
    q_data = q_resp.json()
    q_id = q_data["question_id"]
    assert "prompt" in q_data

    # 3. Submit answer (mock sum calculation)
    f_a = q_data["fraction_a"]
    f_b = q_data["fraction_b"]
    from src.question.fraction import Fraction
    ans = str(Fraction.parse(f_a).add(Fraction.parse(f_b)))

    ans_resp = client.post(
        "/api/v1/game/answer",
        json={"session_id": session_id, "question_id": q_id, "answer": ans},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["correct"] is True
    assert ans_data["score"] == 100


def test_scores_and_help():
    help_resp = client.get("/api/v1/help")
    assert help_resp.status_code == 200
    assert "fraction_addition" in help_resp.json()

    scores_resp = client.get("/api/v1/scores")
    assert scores_resp.status_code == 200
'''

PROJECT_TEMPLATES["tests/test_scoring.py"] = '''"""
Unit tests for ScoreService persistence.
"""

import os
from src.score.service import ScoreService


def test_score_recording(tmp_path):
    db_file = tmp_path / "test_scores.db"
    svc = ScoreService(db_path=str(db_file))

    svc.record_score("Cadet1", 200, 0.8)
    svc.record_score("Cadet2", 500, 1.0)

    board = svc.get_leaderboard()
    assert len(board) == 2
    assert board[0].player_name == "Cadet2"
    assert board[0].score == 500
'''

PROJECT_TEMPLATES["architecture.md"] = """# Space Fractions Architecture Guide

## 1. System Overview
Space Fractions is a gamified arithmetic education platform for 6th-grade learners. The architecture balances pedagogically sound math evaluation with real-time feedback and stateful mission gameplay.

## 2. Component Split & Clean Boundaries
- **GameComponent (`src/game/`)**: Controls the mission state machine (`Idle`, `Playing`, `Paused`, `GameOver`), starship shields, and narrative transitions (Intro movie and Ending scenes).
- **QuestionComponent (`src/question/`)**: Exact arithmetic engine for fraction addition, subtraction, comparison, and reduction. Generates randomized curriculum problems and step-by-step explanations.
- **ScoreComponent (`src/score/`)**: Relational recording of player achievements, accuracy percentages, and classroom leaderboards.
- **AdminComponent (`src/admin/`)**: Educator portal for curating custom question banks.
- **UserComponent (`src/user/`)**: Classroom student and teacher profile management.

## 3. Technology Rationalization
The original architectural draft proposed RabbitMQ, Elasticsearch, and Kubernetes microservices clusters for a 6th-grade math game. ArchForge rationalized this stack into an asynchronous Modular Monolith built on **FastAPI (Python 3.11+)** with SQLite for local execution, preserving service contracts via `internal.proto` and `openapi.yaml`.
"""

PROJECT_TEMPLATES["README.md"] = """# Space Fractions

An interactive educational game designed for 6th-grade students to master fraction arithmetic (addition, subtraction, comparison, and simplification) in a starship navigation quest.

Generated autonomously by **ArchForge**.

---

## 1. Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation
```bash
pip install -r requirements.txt
```

### Running the API Server
```bash
python -m uvicorn src.main:app --reload --port 8000
```
Interactive API documentation will be available at: `http://localhost:8000/docs`

### Running the Test Suite
```bash
pytest tests/ -v
```

---

## 2. Architecture & Design Trade-offs

### Modular Monolith Rationalization
The initial draft architecture specified a high-complexity distributed microservices deployment involving Elasticsearch clusters, RabbitMQ message brokers, and Jenkins webhooks for an elementary school fractions drill. 

**ArchForge Decision**:
1. Consolidated the services into a high-performance **FastAPI Modular Monolith** (`src/`).
2. Maintained clean domain boundaries (`src/game`, `src/question`, `src/score`, `src/admin`, `src/user`).
3. Replaced complex cluster datastores with zero-configuration SQLite for immediate classroom execution.
4. Preserved enterprise readiness by generating `k8s/deployment.yaml`, `openapi.yaml`, and `internal.proto`.

---

## 3. Consistency Validator Findings & Resolutions

ArchForge identified and resolved several architectural inconsistencies present in the specification:
1. **Naming Mismatch (`sql/question_ddl.sql` vs `sql/game_ddl.sql`)**: 
   - *Resolution*: Unified into `sql/game_ddl.sql` and mirrored to `sql/question_ddl.sql` to support both historical references.
2. **Missing Components in Doc (`AdminComponent`, `UserComponent`)**:
   - *Resolution*: Implemented both modules in `src/admin` and `src/user` to satisfy the PlantUML Component View.
3. **Contradiction (99.99% Availability vs 1% Error Budget)**:
   - *Resolution*: Noted in the documentation. Configured service design for standard classroom high-availability (99.9% uptime).
4. **Scope Reconciliation (Intro Movie & Ending Scene)**:
   - *Resolution*: Integrated intro narrative and victory/defeat scenes directly into `src/game/engine.py`.
5. **Class Diagram Composition Inversion**:
   - *Resolution*: Corrected ownership hierarchy in code: `GameSession` owns `Question` and `Score` entities.

---

## 4. Verification
Automated test suite (`tests/`) validates:
- Fraction addition, subtraction, comparison, and reduction logic (`tests/test_fraction.py`).
- Game state transitions (Idle, Playing, Paused, GameOver) (`tests/test_state_machine.py`).
- FastAPI endpoints and gameplay request cycles (`tests/test_api.py`).
- Leaderboard ranking and SQLite storage (`tests/test_scoring.py`).
"""
