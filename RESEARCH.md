# MUD Games for Autonomous AI Agents: Complete Research Report

> **Research Date:** January 2026  
> **Purpose:** Explore creating an old-school MUD-like game as a learning tool for stress-testing AI agent development practices and using agents for gameplay.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background: What is a MUD?](#background-what-is-a-mud)
3. [Why MUDs for AI Agent Testing](#why-muds-for-ai-agent-testing)
4. [Open Source MUD Engines](#open-source-mud-engines)
5. [AI Agent Game-Playing Research](#ai-agent-game-playing-research)
6. [MUD Protocols and Communication](#mud-protocols-and-communication)
7. [Application Ideas](#application-ideas)
8. [Technical Architecture Options](#technical-architecture-options)
9. [Implementation Recommendations](#implementation-recommendations)
10. [Resources and References](#resources-and-references)

---

## Executive Summary

This research explores the intersection of classic Multi-User Dungeon (MUD) games and autonomous AI agents. MUDs represent an ideal testing ground for AI agents because they:

- Require **natural language understanding** without visual processing overhead
- Demand **long-term planning** and **memory management**
- Test **trial-and-error exploration** and **state tracking**
- Can be **procedurally generated** for controlled experiments
- Support **multiple concurrent agents** for complex interaction testing

**Key Finding:** Microsoft's TextWorld provides the fastest path to agent testing, while building a custom MUD offers more control for specific development practice stress tests.

---

## Background: What is a MUD?

### History

MUDs (Multi-User Dungeons) evolved from the original game created in 1978 at the University of Essex by Roy Trubshaw and Richard Bartle. They represent one of the earliest forms of online multiplayer gaming.

### Key MUD Families

| Family | Origin | Key Features |
|--------|--------|--------------|
| **MUD1** | 1978, Essex | Original, inspired all others |
| **AberMUD** | 1987 | First popular open-source MUD |
| **TinyMUD** | 1989 | Focused on social interaction, led to MOO/MUSH |
| **LPMud** | 1989 | Introduced LPC scripting language, driver/mudlib separation |
| **DikuMUD** | 1990 | Combat-focused, most commercially influential |

### Core MUD Components

```
┌─────────────────────────────────────────────────────────────┐
│                        MUD ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │    WORLD     │   │    PARSER    │   │   ACTIONS    │     │
│  │              │   │              │   │              │     │
│  │ • Rooms      │   │ • Tokenizer  │   │ • Movement   │     │
│  │ • Objects    │   │ • Commands   │   │ • Combat     │     │
│  │ • NPCs       │   │ • NL→Action  │   │ • Inventory  │     │
│  │ • Players    │   │              │   │ • Quests     │     │
│  └──────────────┘   └──────────────┘   └──────────────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
│                   ┌────────┴────────┐                       │
│                   │   GAME LOOP     │                       │
│                   │                 │                       │
│                   │ • State Updates │                       │
│                   │ • Event Queue   │                       │
│                   │ • Tick System   │                       │
│                   └────────┬────────┘                       │
│                            │                                 │
│                   ┌────────┴────────┐                       │
│                   │   NETWORK       │                       │
│                   │                 │                       │
│                   │ • Telnet/TCP    │                       │
│                   │ • WebSocket     │                       │
│                   │ • GMCP/MSDP     │                       │
│                   └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Why MUDs for AI Agent Testing

### Challenges That Make MUDs Ideal for AI

| Challenge | Description | Agent Skill Tested |
|-----------|-------------|-------------------|
| **Partial Observability** | Agent only sees current room description | Memory, state tracking |
| **Sparse Rewards** | May need 100+ actions before any reward | Long-term planning |
| **Large Action Space** | Free-form text input, infinite possibilities | Language understanding |
| **Stateful Environment** | Objects change, NPCs move, world evolves | Temporal reasoning |
| **Ambiguity** | Same words can mean different things | Context understanding |
| **Exploration Required** | Must discover mechanics through trial | Hypothesis formation |

### Academic Validation

Recent research confirms MUDs/text games as valuable AI benchmarks:

1. **"Can Large Language Models Play Text Games Well?"** (arXiv:2304.02868)
   - Finding: ChatGPT/GPT-4 struggle with world model construction
   - Even with game manuals, LLMs fail to leverage knowledge properly
   - Cannot infer step-by-step goals as games progress

2. **"TextQuests: How Good are LLMs at Text-Based Video Games?"** (arXiv:2507.23701)
   - Benchmark of 25 Infocom games (Zork, Hitchhiker's Guide, etc.)
   - Games require 30+ hours and hundreds of precise actions
   - Tests long-context reasoning without external tools
   - Available at: https://textquests.ai

### Why This Matters for Agent Development

Testing AI agents on MUDs can reveal:

- **Memory limitations**: How well agents track state over long sessions
- **Planning failures**: Where agents fail to form coherent strategies
- **Language understanding gaps**: Misinterpretation of descriptions
- **Generalization ability**: Can agents transfer learning between games?
- **Collaboration patterns**: How multiple agents interact and coordinate

---

## Open Source MUD Engines

### Tier 1: Purpose-Built for AI (Recommended)

#### Microsoft TextWorld
- **GitHub:** https://github.com/microsoft/TextWorld
- **Stars:** 1,400+
- **Language:** Python
- **License:** MIT

**Features:**
- Procedural game generation with controllable difficulty
- OpenAI Gym-compatible API
- Built-in reward systems
- State tracking and game tree visualization
- Includes Jericho for playing classic Z-machine games

**API Example:**
```python
import textworld

# Generate a game
options = textworld.GameOptions()
options.nb_rooms = 5
options.nb_objects = 10
options.quest_length = 5
game = textworld.generator.make_game(options)
game_file = textworld.generator.compile_game(game)

# Play with an agent
env = textworld.start(game_file)
obs, infos = env.reset()

while not done:
    action = agent.act(obs, infos)  # Your agent here
    obs, score, done, infos = env.step(action)
```

**Best For:** Quick prototyping, RL research, controlled experiments

---

#### Jericho (Microsoft)
- **GitHub:** https://github.com/microsoft/jericho
- **Language:** Python
- **License:** GPL v2

**Features:**
- Play classic Infocom Z-machine games
- Provides valid action detection
- World state diffing
- Object tree extraction

**Best For:** Benchmarking on classic games, research reproducibility

---

### Tier 2: Full-Featured MUD Engines

#### Evennia
- **GitHub:** https://github.com/evennia/evennia
- **Stars:** 1,800+
- **Language:** Python (Django/Twisted)
- **License:** BSD

**Features:**
- Modern Python codebase with web admin
- Built-in web client with WebSocket support
- Extensive documentation and tutorials
- Database-backed persistence (SQLite, PostgreSQL)
- Plugin architecture for extensions

**Architecture:**
```
┌─────────────────────────────────────────────────────┐
│                    EVENNIA                           │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Portal    │  │   Server    │  │   Webclient │  │
│  │  (Twisted)  │←→│  (Django)   │←→│   (React)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│         │                │                │          │
│         ↓                ↓                ↓          │
│  ┌─────────────────────────────────────────────────┐│
│  │              Database (PostgreSQL)              ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

**Best For:** Building production MUDs, web integration, complex worlds

---

#### Ranvier
- **GitHub:** https://github.com/shawncplus/ranviermud
- **Stars:** 1,000+
- **Language:** Node.js/TypeScript
- **License:** MIT

**Features:**
- Modern JavaScript/TypeScript codebase
- Bundle-based modular architecture
- YAML-based content definition
- WebSocket and Telnet support
- Event-driven design

**Content Example (YAML):**
```yaml
- id: "1"
  title: "Town Square"
  description: "You stand in the center of a bustling town square."
  exits:
    north: "2"
    east: "3"
  items:
    - "sword:1"
  npcs:
    - "merchant:1"
```

**Best For:** Rapid prototyping, JavaScript developers, modular content

---

#### DikuMUD III
- **GitHub:** https://github.com/Seifert69/DikuMUD3
- **Language:** C++
- **License:** LGPL

**Features:**
- Latest evolution of classic DikuMUD
- HTML and WebSocket support
- Discord integration
- Proven combat system from 30+ years of development

**Best For:** Classic MUD feel, combat-heavy games

---

### Tier 3: Lightweight Engines

| Engine | Language | GitHub | Notes |
|--------|----------|--------|-------|
| **text-engine** | JavaScript | okaybenji/text-engine | Browser-based, simple JSON game definition |
| **Tale** | Python | irmen/Tale | IF framework, good for single-player |
| **Kalevala** | Elixir | oestrich/kalevala | Modern toolkit for text games |
| **ExVenture** | Elixir | oestrich/ex_venture | Full MUD engine in Elixir |
| **RockMUD** | Node.js | MoreOutput/RockMUD | WebSocket-first design |
| **room.js** | Node.js | doughsay/room.js | MOO-style engine |

---

### Comparison Matrix

| Feature | TextWorld | Evennia | Ranvier | DikuMUD3 |
|---------|-----------|---------|---------|----------|
| **Language** | Python | Python | Node.js | C++ |
| **AI-Ready API** | ✅ Native | ⚠️ Needs work | ⚠️ Needs work | ❌ Telnet only |
| **Procedural Gen** | ✅ Built-in | ❌ | ❌ | ❌ |
| **Multiplayer** | ❌ | ✅ | ✅ | ✅ |
| **Web Client** | ⚠️ Basic | ✅ | ✅ | ✅ |
| **Persistence** | ❌ | ✅ SQLite/PG | ✅ JSON/DB | ✅ Files |
| **Documentation** | ✅ Excellent | ✅ Excellent | ⚠️ Good | ⚠️ Moderate |
| **Active Development** | ⚠️ Slow | ✅ Active | ⚠️ Slow | ✅ Active |
| **Learning Curve** | Low | Medium | Medium | High |

---

## AI Agent Game-Playing Research

### Existing Frameworks for Agent Evaluation

#### TextQuests Benchmark
- **Website:** https://textquests.ai
- **Paper:** arXiv:2507.23701
- **Games:** 25 classic Infocom titles

**Evaluation Approach:**
- No external tools allowed
- Pure long-context reasoning
- Trial-and-error within single session
- Measures intrinsic agent capability

**Included Games:**
- Zork I, II, III
- Hitchhiker's Guide to the Galaxy
- Planetfall
- Enchanter series
- And 19 more classic titles

---

#### TextWorld Research Platform

**Key Research Uses:**
1. **Curriculum Learning:** Generate progressively harder games
2. **Transfer Learning:** Train on simple games, test on complex
3. **Reward Shaping:** Control reward density and signals
4. **Ablation Studies:** Isolate specific challenges

**Game Generation Parameters:**
```python
options = textworld.GameOptions()
options.nb_rooms = 1-20      # World size
options.nb_objects = 1-50    # Object count
options.quest_length = 1-30  # Minimum actions to win
options.grammar = {...}       # Language complexity
```

---

### Agent Architectures That Have Been Tested

| Architecture | Approach | Limitations Found |
|--------------|----------|-------------------|
| **LSTM + RL** | Encode text, predict actions | Poor generalization |
| **Transformer + RL** | Better text encoding | High sample complexity |
| **GPT-4 Zero-shot** | Prompt with game state | Fails world modeling |
| **GPT-4 + Memory** | External state tracking | Still misses causality |
| **ReAct Pattern** | Reason + Act alternation | Better but inconsistent |

---

## MUD Protocols and Communication

### Standard Protocols

#### GMCP (Generic MUD Communication Protocol)
- **Telnet Option:** 201
- **Format:** JSON over telnet subnegotiation
- **Purpose:** Out-of-band structured data

**Example Messages:**
```
# Server → Client: Room info
Char.Vitals {"hp": 100, "maxhp": 100, "mp": 50, "maxmp": 50}

# Server → Client: Room data
Room.Info {"id": 1234, "name": "Town Square", "exits": ["north", "east"]}

# Client → Server: Enable module
Core.Supports.Set ["Char 1", "Room 1", "Comm 1"]
```

**Use for AI:** Perfect for providing structured state to agents without parsing prose.

---

#### MSDP (MUD Server Data Protocol)
- **Telnet Option:** 69
- **Format:** Custom binary protocol
- **Purpose:** Variable reporting and subscription

**Key Variables:**
- `CHARACTER_NAME`, `HEALTH`, `MANA`
- `ROOM_NAME`, `ROOM_EXITS`, `ROOM_VNUM`
- `SERVER_ID`, `SERVER_TIME`

---

#### MSSP (MUD Server Status Protocol)
- **Purpose:** Server discovery and status
- **Used by:** MUD listing sites

---

### Communication Options for AI Agents

| Method | Latency | Complexity | Best For |
|--------|---------|------------|----------|
| **Direct Function Calls** | Lowest | Lowest | Same-process agent |
| **WebSocket + JSON** | Low | Low | Web-based agents |
| **REST API** | Medium | Low | Stateless agents |
| **Telnet + GMCP** | Medium | Medium | Standard MUD clients |
| **gRPC** | Low | Medium | High-performance agents |

---

## Application Ideas

### Application 1: Agent Development Stress Tester

**Purpose:** Test AI coding agents on tasks that require long-term coherence and state management.

**Concept:** 
Create a MUD where the "quests" are actually software development tasks. Rooms represent code modules, objects represent APIs/functions, and NPCs represent external services.

**Example Scenario:**
```
You are in the Authentication Module. 
A UserService daemon lurks here, awaiting requests.
Exits: [database-room] [api-gateway] [logging-chamber]

You see:
- A dusty JWT token generator
- An OAuth2 configuration scroll

> use token-generator on user-request
The token generator whirs to life, but ERROR: 
The signing key is missing! Perhaps the Key Vault in the 
database-room has what you need.
```

**Stress Tests:**
- Context management across many "rooms" (modules)
- Correct sequencing of operations
- Error recovery and debugging
- Integration between components

**Unique Value:**
- Maps directly to real development scenarios
- Reveals agent memory/planning limitations
- Can import real codebase structures

---

### Application 2: Multi-Agent Collaboration Arena

**Purpose:** Test how multiple AI agents collaborate, compete, or coordinate.

**Concept:**
A shared MUD world where multiple agents must work together (or against each other) to accomplish goals.

**Game Modes:**

| Mode | Description | Tests |
|------|-------------|-------|
| **Cooperative Quest** | Agents must share info to solve puzzle | Communication, trust |
| **Resource Competition** | Limited resources, agents compete | Strategy, efficiency |
| **Role-Based Team** | Each agent has unique abilities | Specialization, coordination |
| **Adversarial** | Some agents help, some hinder | Deception detection |

**Example: Cooperative Dungeon**
```
AGENT-1 is in: Dark Library
"You see ancient tomes. One mentions 'The key lies where 
the sun first touches the mountain.'"

AGENT-2 is in: Mountain Peak
"The sunrise illuminates a small crevice in the eastern rock.
There appears to be something shiny inside."

COMMUNICATION CHANNEL:
AGENT-1 → AGENT-2: "Check the east side of the mountain at 
sunrise for a key!"
```

**Unique Value:**
- Tests agent-to-agent communication
- Reveals coordination failures
- Benchmarks emergent behaviors

---

### Application 3: LLM Reasoning Benchmark Suite

**Purpose:** Systematic evaluation of LLM capabilities through controlled game scenarios.

**Concept:**
Procedurally generated games that isolate specific reasoning abilities.

**Test Categories:**

| Category | Game Type | Example |
|----------|-----------|---------|
| **Spatial Reasoning** | Navigation maze | "Go north, east, south. Where are you relative to start?" |
| **Temporal Reasoning** | Time-limited quests | "The door opens at midnight, the key disappears at dawn" |
| **Causal Reasoning** | Rube Goldberg puzzles | "Push lever → opens door → releases water → grows plant" |
| **Social Reasoning** | NPC manipulation | "The guard likes flattery but hates bribes" |
| **Numerical Reasoning** | Resource management | "You have 10 gold, sword costs 15, you can sell the gem for 8" |

**Implementation:**
```python
# Generate test suite
tests = []
for category in REASONING_CATEGORIES:
    for difficulty in [EASY, MEDIUM, HARD]:
        game = generate_game(category, difficulty)
        tests.append(game)

# Run agent evaluation
results = []
for test in tests:
    score = evaluate_agent(agent, test)
    results.append({
        "category": test.category,
        "difficulty": test.difficulty,
        "score": score,
        "transcript": test.transcript
    })

# Analyze weaknesses
weaknesses = identify_failure_patterns(results)
```

**Unique Value:**
- Reproducible benchmarks
- Fine-grained capability assessment
- Direct comparison between models

---

### Application 4: Emergent Narrative Sandbox

**Purpose:** Study how AI agents create and respond to emergent stories.

**Concept:**
A persistent world where AI agents live as characters, with an AI "Dungeon Master" creating dynamic content.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    NARRATIVE SANDBOX                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 DUNGEON MASTER (LLM)                  │   │
│  │                                                       │   │
│  │  • Generates quests based on agent actions            │   │
│  │  • Creates NPCs with personalities                    │   │
│  │  • Evolves world state based on outcomes              │   │
│  │  • Introduces conflicts and opportunities             │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↕                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    WORLD STATE                        │   │
│  │                                                       │   │
│  │  • Persistent object database                         │   │
│  │  • NPC relationship graphs                            │   │
│  │  • Event history and consequences                     │   │
│  │  • Economic simulation                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↕                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  AGENT 1   │  │  AGENT 2   │  │  AGENT N   │            │
│  │  "Warrior" │  │  "Mage"    │  │  "Thief"   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Research Questions:**
- Do agents develop consistent personalities?
- Can agents form meaningful relationships?
- What narratives emerge without human guidance?
- How do agents handle moral dilemmas?

**Unique Value:**
- Tests creative and social reasoning
- Generates interesting content for study
- Could produce entertainment value

---

### Application 5: Development Practice Simulator

**Purpose:** Directly stress-test agent coding practices through game mechanics.

**Concept:**
A MUD where game actions directly mirror software development practices.

**Game Mechanics Mapping:**

| Game Action | Development Practice | Success Metric |
|-------------|---------------------|----------------|
| "write code" | Generate code | Passes tests |
| "review artifact" | Code review | Finds bugs |
| "deploy to zone" | CI/CD | No regressions |
| "talk to npc" | Requirement gathering | Correct interpretation |
| "use debugging-tool" | Debugging | Identifies root cause |
| "explore dungeon" | Codebase exploration | Finds relevant code |
| "combine items" | Integration | Components work together |

**Example Session:**
```
You are in the Feature Branch Cavern.
Your TASK SCROLL reads: "Add user authentication to the API"

Obvious exits: [main-branch] [test-suite] [documentation-tower]

You see:
- A rusty AuthController class
- An untested middleware function
- A stack of requirement scrolls

> read requirement scrolls
The scrolls describe: "Users should log in with email and password.
Sessions should expire after 24 hours. Failed attempts should be 
rate-limited."

> examine AuthController
The AuthController is incomplete. It has methods for:
- login() - EMPTY
- logout() - EMPTY  
- validateSession() - BUGGY (never checks expiration)

What do you do?
```

**Evaluation Metrics:**
- Time to completion
- Test pass rate
- Bug introduction rate
- Requirement coverage
- Code quality scores

**Unique Value:**
- Directly measures development capability
- Controlled, reproducible scenarios
- Reveals specific failure modes

---

### Application Comparison Matrix

| Application | Complexity | Research Value | Entertainment Value | Development Effort |
|-------------|------------|----------------|--------------------|--------------------|
| **1: Stress Tester** | Medium | High | Low | Medium |
| **2: Multi-Agent Arena** | High | Very High | Medium | High |
| **3: Benchmark Suite** | Low-Medium | Very High | Low | Medium |
| **4: Narrative Sandbox** | Very High | High | High | Very High |
| **5: Dev Practice Sim** | Medium | Very High | Low | Medium |

### Recommended Starting Point

**For Research Focus:** Start with **Application 3** (Benchmark Suite) using TextWorld as the base. This provides immediate value with minimal custom development.

**For Development Testing:** Start with **Application 5** (Dev Practice Sim) built on Evennia. This directly addresses the stated goal of stress-testing agent development practices.

**For Maximum Learning:** Start with **Application 1** (Stress Tester) as it combines reasonable complexity with practical insights.

---

## Technical Architecture Options

### Option A: TextWorld Extension (Simplest)

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Custom Game Generator                   │   │
│  │                                                       │   │
│  │  • Define your game grammar                           │   │
│  │  • Create custom quest types                          │   │
│  │  • Design evaluation metrics                          │   │
│  └─────────────────────────┬────────────────────────────┘   │
│                            │                                 │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  TextWorld Core                       │   │
│  │                                                       │   │
│  │  • Game execution engine                              │   │
│  │  • State tracking                                     │   │
│  │  • Gym-compatible API                                 │   │
│  └─────────────────────────┬────────────────────────────┘   │
│                            │                                 │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Agent Interface                     │   │
│  │                                                       │   │
│  │  • LLM integration (OpenAI, Anthropic, local)         │   │
│  │  • Action selection logic                             │   │
│  │  • Memory management                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Fastest to implement
- Proven game engine
- Good documentation

**Cons:**
- Single-player only
- Limited customization
- No persistence

---

### Option B: Custom MUD on Evennia (Most Flexible)

```
┌─────────────────────────────────────────────────────────────┐
│                      EVENNIA CORE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │ Portal Server  │  │  Game Server   │  │   Web Admin   │  │
│  │   (Twisted)    │  │   (Django)     │  │   Interface   │  │
│  └───────┬────────┘  └───────┬────────┘  └───────────────┘  │
│          │                   │                               │
│          ↓                   ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    YOUR EXTENSIONS                       ││
│  ├─────────────────────────────────────────────────────────┤│
│  │                                                          ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ││
│  │  │ Agent API    │  │ Custom       │  │ Evaluation   │   ││
│  │  │ Endpoints    │  │ Commands     │  │ Framework    │   ││
│  │  │              │  │              │  │              │   ││
│  │  │ • REST API   │  │ • code       │  │ • Metrics    │   ││
│  │  │ • WebSocket  │  │ • review     │  │ • Logging    │   ││
│  │  │ • Batch mode │  │ • deploy     │  │ • Analysis   │   ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘   ││
│  │                                                          ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│                            ↓                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                     DATABASE                             ││
│  │           (PostgreSQL / SQLite)                          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘

                            ↕

┌─────────────────────────────────────────────────────────────┐
│                    AGENT FRAMEWORK                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Agent 1    │  │   Agent 2    │  │   Agent N    │       │
│  │              │  │              │  │              │       │
│  │  • LLM       │  │  • LLM       │  │  • RL Model  │       │
│  │  • Memory    │  │  • Memory    │  │  • Policy    │       │
│  │  • Strategy  │  │  • Strategy  │  │  • Value     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Full multiplayer support
- Persistence and state management
- Web admin for monitoring
- Highly extensible

**Cons:**
- More development effort
- Steeper learning curve
- Heavier infrastructure

---

### Option C: Lightweight Custom Build (Middle Ground)

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOM MUD SERVER                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    FastAPI Server                     │   │
│  │                                                       │   │
│  │  POST /game/{id}/action   - Submit action             │   │
│  │  GET  /game/{id}/state    - Get current state         │   │
│  │  POST /game/new           - Create new game           │   │
│  │  GET  /game/{id}/history  - Get action history        │   │
│  │  WS   /game/{id}/stream   - Real-time updates         │   │
│  └─────────────────────────────┬────────────────────────┘   │
│                                │                             │
│                                ↓                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                     Game Engine                       │   │
│  │                                                       │   │
│  │  class GameWorld:                                     │   │
│  │      rooms: dict[str, Room]                           │   │
│  │      objects: dict[str, Object]                       │   │
│  │      players: dict[str, Player]                       │   │
│  │                                                       │   │
│  │  class CommandParser:                                 │   │
│  │      def parse(text: str) -> Action                   │   │
│  │                                                       │   │
│  │  class ActionExecutor:                                │   │
│  │      def execute(action: Action, world: World)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 World Definition (YAML)               │   │
│  │                                                       │   │
│  │  rooms:                                               │   │
│  │    - id: town_square                                  │   │
│  │      name: Town Square                                │   │
│  │      description: A bustling plaza...                 │   │
│  │      exits: {north: castle_gate, east: market}        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pros:**
- Full control over design
- Simple, understandable codebase
- Easy to modify for specific needs
- Lightweight deployment

**Cons:**
- Build everything from scratch
- No existing content
- More testing needed

---

### Technology Stack Recommendations

#### For Python Developers
```
Backend:      FastAPI or Flask
Database:     SQLite (dev) / PostgreSQL (prod)
WebSocket:    python-socketio or websockets
Base Engine:  Extend TextWorld or Evennia
Agent:        LangChain or custom LLM integration
```

#### For Node.js Developers
```
Backend:      Express or Fastify
Database:     SQLite (dev) / PostgreSQL (prod)  
WebSocket:    ws or Socket.io
Base Engine:  Extend Ranvier
Agent:        LangChain.js or custom
```

#### For Maximum Research Value
```
Backend:      Python (best ML ecosystem)
Game Engine:  TextWorld (proven for research)
Database:     PostgreSQL (complex queries)
Agent:        Direct API calls to Claude/GPT-4
Analysis:     Pandas, Jupyter notebooks
```

---

## Implementation Recommendations

### Phase 1: Proof of Concept (1-2 weeks)

**Goal:** Validate the concept with minimal investment.

**Steps:**
1. Install TextWorld: `pip install textworld`
2. Generate a simple game with known solution
3. Build a basic LLM agent that plays the game
4. Measure success rate and failure modes

**Deliverables:**
- Working agent that can play generated games
- Initial metrics on agent performance
- List of interesting failure cases

---

### Phase 2: Custom Game Content (2-4 weeks)

**Goal:** Create games that test specific capabilities.

**Steps:**
1. Define target capabilities to test (memory, planning, etc.)
2. Design game scenarios for each capability
3. Implement custom TextWorld grammar/content
4. Build evaluation framework

**Deliverables:**
- Suite of test games
- Automated evaluation pipeline
- Baseline results for different LLMs

---

### Phase 3: Multi-Agent Support (4-8 weeks)

**Goal:** Enable multiple agents in shared world.

**Options:**
1. **Extend Evennia:** Add agent API endpoints
2. **Build Custom:** Lightweight Python server with WebSocket
3. **Modify TextWorld:** Fork and add multiplayer

**Deliverables:**
- Server supporting multiple concurrent agents
- Communication protocol between agents
- Metrics for collaboration/competition

---

### Phase 4: Development Practice Integration (4-8 weeks)

**Goal:** Map game mechanics to real development tasks.

**Steps:**
1. Define development scenarios (debugging, code review, etc.)
2. Create game representations of code artifacts
3. Integrate with real codebases (read-only at first)
4. Build scoring based on code quality metrics

**Deliverables:**
- Development-themed MUD
- Integration with code analysis tools
- Benchmarks for coding agents

---

## Resources and References

### Primary Resources

#### MUD Engine Documentation
- **Evennia:** https://www.evennia.com/docs/
- **TextWorld:** https://textworld.readthedocs.io/
- **Ranvier:** https://ranviermud.com/docs/

#### Research Papers
- TextWorld Paper: arXiv:1806.11532
- TextQuests Benchmark: arXiv:2507.23701
- LLMs Playing Text Games: arXiv:2304.02868

#### Curated Lists
- **awesome-mud:** https://github.com/mudcoders/awesome-mud
- **awesome-muds:** https://github.com/maldorne/awesome-muds
- **awesome-ai-agents:** https://github.com/e2b-dev/awesome-ai-agents

### Protocol References
- **GMCP Specification:** https://tintin.mudhalla.net/protocols/gmcp/
- **MSDP Specification:** https://tintin.mudhalla.net/protocols/msdp/
- **MSSP Specification:** https://tintin.mudhalla.net/protocols/mssp/

### Community
- **MUD Coders Guild (Slack):** https://mudcoders.com
- **r/MUD (Reddit):** https://www.reddit.com/r/MUD
- **MUDhalla Discord:** https://discord.gg/m3wZeSq

### Tools
- **TextWorld GitHub:** https://github.com/microsoft/TextWorld
- **Jericho (Z-machine):** https://github.com/microsoft/jericho
- **TextQuests Benchmark:** https://github.com/centerforaisafety/textquests

---

## Appendix: Quick Start Code Examples

### Example 1: Basic TextWorld Agent

```python
"""
Basic agent that plays TextWorld games using an LLM.
"""
import textworld
import textworld.gym
from anthropic import Anthropic

client = Anthropic()

def create_agent_prompt(observation: str, valid_actions: list[str]) -> str:
    return f"""You are playing a text adventure game. 

Current observation:
{observation}

Valid actions you can take:
{', '.join(valid_actions)}

What action do you take? Respond with ONLY the action, nothing else."""

def get_agent_action(observation: str, valid_actions: list[str]) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": create_agent_prompt(observation, valid_actions)
        }]
    )
    return response.content[0].text.strip()

def play_game(game_file: str, max_steps: int = 100):
    request_infos = textworld.EnvInfos(
        admissible_commands=True,
        description=True,
        inventory=True
    )
    
    env = textworld.start(game_file, request_infos)
    obs, infos = env.reset()
    
    total_score = 0
    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")
        print(f"Observation: {obs}")
        
        valid_actions = infos.get("admissible_commands", ["look", "inventory"])
        action = get_agent_action(obs, valid_actions)
        print(f"Agent action: {action}")
        
        obs, score, done, infos = env.step(action)
        total_score += score
        
        if done:
            print(f"\nGame finished! Final score: {total_score}")
            break
    
    env.close()
    return total_score

if __name__ == "__main__":
    # Generate a simple game
    options = textworld.GameOptions()
    options.nb_rooms = 3
    options.nb_objects = 5
    options.quest_length = 3
    
    game = textworld.generator.make_game(options)
    game_file = textworld.generator.compile_game(game)
    
    play_game(game_file)
```

### Example 2: Simple Custom MUD Server

```python
"""
Minimal MUD server with API for agent integration.
"""
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI()

# Game state
class Room:
    def __init__(self, id: str, name: str, description: str, exits: dict):
        self.id = id
        self.name = name
        self.description = description
        self.exits = exits
        self.objects = []

class Player:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.current_room = "start"
        self.inventory = []
        self.history = []

class GameWorld:
    def __init__(self):
        self.rooms = {
            "start": Room("start", "Town Square", 
                "You stand in a bustling town square. A fountain gurgles nearby.",
                {"north": "castle", "east": "market"}),
            "castle": Room("castle", "Castle Gate",
                "Massive iron gates loom before you. Guards eye you suspiciously.",
                {"south": "start"}),
            "market": Room("market", "Market District",
                "Vendors hawk their wares. The smell of spices fills the air.",
                {"west": "start"})
        }
        self.players = {}
    
    def add_player(self, name: str) -> str:
        player_id = str(uuid.uuid4())
        self.players[player_id] = Player(player_id, name)
        return player_id
    
    def get_observation(self, player_id: str) -> dict:
        player = self.players[player_id]
        room = self.rooms[player.current_room]
        return {
            "room_name": room.name,
            "description": room.description,
            "exits": list(room.exits.keys()),
            "objects": room.objects,
            "inventory": player.inventory
        }
    
    def execute_action(self, player_id: str, action: str) -> dict:
        player = self.players[player_id]
        room = self.rooms[player.current_room]
        
        player.history.append(action)
        parts = action.lower().split()
        
        if not parts:
            return {"success": False, "message": "What would you like to do?"}
        
        verb = parts[0]
        
        if verb == "look":
            return {"success": True, "message": room.description}
        
        elif verb == "go" and len(parts) > 1:
            direction = parts[1]
            if direction in room.exits:
                player.current_room = room.exits[direction]
                new_room = self.rooms[player.current_room]
                return {"success": True, "message": f"You go {direction}.\n\n{new_room.description}"}
            return {"success": False, "message": "You can't go that way."}
        
        elif verb in room.exits:  # Allow "north" instead of "go north"
            player.current_room = room.exits[verb]
            new_room = self.rooms[player.current_room]
            return {"success": True, "message": f"You go {verb}.\n\n{new_room.description}"}
        
        elif verb == "inventory":
            if player.inventory:
                return {"success": True, "message": f"You are carrying: {', '.join(player.inventory)}"}
            return {"success": True, "message": "You aren't carrying anything."}
        
        return {"success": False, "message": "I don't understand that command."}

# Initialize world
world = GameWorld()

# API Models
class NewGameRequest(BaseModel):
    player_name: str

class ActionRequest(BaseModel):
    action: str

# API Endpoints
@app.post("/game/new")
def new_game(request: NewGameRequest):
    player_id = world.add_player(request.player_name)
    observation = world.get_observation(player_id)
    return {
        "player_id": player_id,
        "observation": observation
    }

@app.get("/game/{player_id}/state")
def get_state(player_id: str):
    return world.get_observation(player_id)

@app.post("/game/{player_id}/action")
def take_action(player_id: str, request: ActionRequest):
    result = world.execute_action(player_id, request.action)
    observation = world.get_observation(player_id)
    return {
        "result": result,
        "observation": observation
    }

@app.get("/game/{player_id}/history")
def get_history(player_id: str):
    player = world.players[player_id]
    return {"history": player.history}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Conclusion

Building a MUD for AI agent testing is a viable and valuable project that can:

1. **Reveal agent limitations** in long-term planning and state management
2. **Provide controlled benchmarks** for comparing different agent architectures
3. **Enable multi-agent research** on collaboration and competition
4. **Map directly to development practices** for practical stress testing

**Recommended Next Step:** Start with Microsoft TextWorld to validate the concept quickly, then expand to a custom Evennia-based solution for multiplayer and development practice simulation.

---

*Document generated from research conducted January 2026*
