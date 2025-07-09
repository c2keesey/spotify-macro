# Feature Development Workflow

## Overview
Simple markdown-based system for tracking feature development across Claude Code sessions.

## Workflow Steps

### 1. Select Feature
- Review `docs/backlog/todos.md` 
- User will specify feature to work on. it may be in progress

### 2. Create Feature Branch
```bash
git checkout -b feature/[feature-name]
```

### 3. Setup Feature Tracking
```bash
cp -r docs/features/template docs/features/[feature-name]
```
- Update `docs/features/[feature-name]/README.md` with feature context
- Use `docs/features/[feature-name]/todos.md` for feature-specific tasks

### 4. Development
- Work on feature using todos for tracking
- Keep context in README for session continuity
- Update todos as progress is made

### 5. Completion
- Clean up feature folder
- Remove from backlog if applicable
- Delete feature branch after merge

## Files Structure
```
docs/
├── features/
│   ├── template/           # Template for new features
│   └── [feature-name]/     # Active feature folder
├── backlog/
│   └── todos.md           # General todos/feature ideas
└── workflow.md            # This file
```

## Session Continuity
- Each feature README contains context and related files
- Todos track specific implementation steps
- No code in markdown files - only task descriptions and file references
