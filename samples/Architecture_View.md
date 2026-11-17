# Space Fractions: Architecture Views

## 1. Scenario View (Use Cases)

```plantuml
@startuml SpaceFractions_UseCase
left to right direction
actor "Student Player" as student
actor "Math Educator / Admin" as admin

rectangle "Space Fractions System" {
  usecase "Play Game" as UC_Play
  usecase "View Score" as UC_Score
  usecase "View Help" as UC_Help
  usecase "Update Questions" as UC_AdminQuestions
  usecase "Manage Student Profiles" as UC_UserMgmt
}

student --> UC_Play
student --> UC_Score
student --> UC_Help

admin --> UC_AdminQuestions
admin --> UC_Score
admin --> UC_UserMgmt
@enduml
```

## 2. Logic View (Class & Object Diagrams)

### Class Diagram
```plantuml
@startuml SpaceFractions_Classes
class GameSession {
  +String sessionId
  +String playerName
  +String state
  +int currentScore
  +int questionsAnswered
  +startGame()
  +submitAnswer(questionId, answer)
  +pauseGame()
  +resumeGame()
  +endGame()
}

class Question {
  +String id
  +String operation
  +Fraction fractionA
  +Fraction fractionB
  +String correctAnswer
  +String explanation
  +validate(answer: String): Boolean
}

class Fraction {
  +int numerator
  +int denominator
  +simplify(): Fraction
  +toDecimal(): Float
  +toString(): String
}

class Score {
  +String id
  +String playerName
  +int points
  +float accuracy
  +DateTime timestamp
}

class User {
  +String id
  +String username
  +String role
}

' Deliberate architectural quirk: odd composition arrows
Score --* GameSession : belongs to
Question --* GameSession : contains
User --* GameSession : plays
Fraction --* Question : operands
@enduml
```

### Object Diagram
```plantuml
@startuml SpaceFractions_Objects
' Deliberate syntax anomaly: legacy/nonstandard plantuml syntax
object session_1 {
  sessionId = "sess-101"
  playerName = "AstroCadet"
  state = "Playing"
  currentScore = 150
}

object question_42 {
  id = "q-42"
  operation = "add"
  fractionA = "1/2"
  fractionB = "1/4"
  correctAnswer = "3/4"
}

session_1 : contains -> question_42
@enduml
```

## 3. Process View (State, Activity, Sequence & Collaboration)

### State Diagram
```plantuml
@startuml SpaceFractions_GameState
[*] --> Idle

Idle --> Playing : Start Game / Intro Complete
Playing --> Paused : Pause Triggered
Paused --> Playing : Resume Game
Playing --> GameOver : Questions Exhausted / Lives Zero
Paused --> GameOver : Quit Session

GameOver --> Idle : Return to Menu
GameOver --> [*]
@enduml
```

### Activity Diagram
```plantuml
@startuml SpaceFractions_Activity
start
:Display Intro & Main Menu;
:Select Game Mode;
repeat
  :Fetch Fraction Question;
  :Display Question & Asteroid Challenge;
  :Player Submits Fraction Answer;
  if (Answer is Correct?) then (yes)
    :Award Score & Fuel Starship;
    :Display Positive Feedback;
  else (no)
    :Deduct Shield & Show Step-by-Step Explanation;
  endif
repeat while (More questions and ship operational?) is (yes)
->no;
:Display Victory / Defeat Ending Scene;
:Record Final Score;
stop
@enduml
```

### Sequence Diagram
```plantuml
@startuml SpaceFractions_Sequence
autonumber
actor Player
participant GameComponent
participant QuestionComponent
participant ScoreComponent
database Database

Player -> GameComponent: start_game("CosmoPilot")
activate GameComponent
GameComponent -> QuestionComponent: generate_question("add", difficulty=1)
activate QuestionComponent
QuestionComponent --> GameComponent: Question(id="q1", "1/3 + 1/6", expected="1/2")
deactivate QuestionComponent
GameComponent --> Player: display_question("1/3 + 1/6")

Player -> GameComponent: submit_answer("q1", "1/2")
GameComponent -> QuestionComponent: validate_answer("q1", "1/2")
activate QuestionComponent
QuestionComponent --> GameComponent: Valid(true, delta=+100)
deactivate QuestionComponent

GameComponent -> ScoreComponent: record_score("CosmoPilot", 100)
activate ScoreComponent
ScoreComponent -> Database: INSERT INTO scores
ScoreComponent --> GameComponent: score_confirmed
deactivate ScoreComponent

GameComponent --> Player: result(correct=True, score=100)
deactivate GameComponent
@enduml
```

### Collaboration Diagram
```plantuml
@startuml SpaceFractions_Collaboration
component [Player UI] as UI
component [GameController] as GC
component [QuestionEngine] as QE
component [ScoreKeeper] as SK

UI -> GC : 1: start_game()
GC -> QE : 2: get_question()
UI -> GC : 3: submit_answer()
GC -> QE : 4: check_answer()
GC -> SK : 5: update_score()
@enduml
```

## 4. Development View (Package & Component Diagrams)

### Package Diagram
```plantuml
@startuml SpaceFractions_Packages
package "spacefractions" {
  package "game" {
    [game_session]
    [engine]
    [state_machine]
  }
  package "question" {
    [fraction_math]
    [generator]
    [validator]
  }
  package "score" {
    [leaderboard]
    [persistence]
  }
  package "admin" {
    [question_crud]
  }
  package "user" {
    [auth]
    [profile]
  }
}
game ..> question : depends
game ..> score : depends
admin ..> question : manages
@enduml
```

### Component Diagram
```plantuml
@startuml SpaceFractions_Components
[Player Interface] as PlayerUI
[Educator Interface] as AdminUI

package "Backend Services" {
  [GameComponent] as GameComp
  [QuestionComponent] as QuestionComp
  [ScoreComponent] as ScoreComp
  [UserComponent] as UserComp
  [AdminComponent] as AdminComp
}

database "SQLite / Postgres" as DB

PlayerUI --> GameComp : REST /api/v1/game
PlayerUI --> ScoreComp : REST /api/v1/scores
AdminUI --> AdminComp : REST /api/v1/admin
AdminUI --> UserComp : REST /api/v1/users

GameComp --> QuestionComp : internal call
GameComp --> ScoreComp : internal call
AdminComp --> QuestionComp : manage questions
ScoreComp --> DB : SQL
UserComp --> DB : SQL
AdminComp --> DB : SQL
@enduml
```

## 5. Physical View (Deployment & Container Diagrams)

### Deployment Diagram
```plantuml
@startuml SpaceFractions_Deployment
node "Client Machine" {
  artifact "Web Browser / Desktop GUI" as ClientUI
}

node "Application Server" {
  node "FastAPI Runtime" {
    artifact "SpaceFractions App" as App
  }
}

node "Database Host" {
  database "Relational Storage (SQLite/PostgreSQL)" as DBServer
}

ClientUI -- App : HTTP/JSON :8000
App -- DBServer : SQL Connection
@enduml
```

### Container Diagram (C4 Style)
```plantuml
@startuml SpaceFractions_Container
skinparam componentStyle uml2

actor "Student / Educator" as User

package "Space Fractions System" {
  [Single Page / GUI Client] as WebApp
  [FastAPI Modular Monolith API] as APIApp
  database "SQLite Database" as AppDB
}

User --> WebApp : Uses
WebApp --> APIApp : JSON / HTTPS API
APIApp --> AppDB : SQL Queries
@enduml
```
