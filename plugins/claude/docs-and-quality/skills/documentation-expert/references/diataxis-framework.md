# Diátaxis Documentation Framework Reference

Diátaxis is a systematic framework for technical writing, categorizing documentation into four distinct typologies based on the user's intent.

---

## The Four Pillars

```
                     ┌───────────────────┬───────────────────┐
                     │    PRACTICAL      │    THEORETICAL    │
 ┌───────────────────┼───────────────────┼───────────────────┤
 │    ACQUISITION    │    Tutorials      │    Explanation    │
 ├───────────────────┼───────────────────┼───────────────────┤
 │    APPLICATION    │    How-to Guides  │    Reference      │
 └───────────────────┴───────────────────┴───────────────────┘
```

### 1. Tutorials (Learning-oriented)
- **Goal**: Help the reader get started and build confidence.
- **Form**: A series of step-by-step instructions that leads a beginner to a completed, working prototype.
- **Rule**: Avoid choices, explanations, or reference material. Provide a single, linear path that works 100% of the time.

### 2. How-To Guides (Task-oriented)
- **Goal**: Show the reader how to solve a specific, real-world problem.
- **Form**: A recipe of steps to achieve a result (e.g. "How to set up SSO with FastAPI").
- **Rule**: Assumes basic competence. Explain the context briefly, list prerequisites, and outline the steps. Avoid generic tutorials.

### 3. Reference Material (Information-oriented)
- **Goal**: Describe the machinery and provide lookup details.
- **Form**: API catalogs, class definitions, configuration flags, and CLI arguments.
- **Rule**: Keep it neutral, objective, and dense. Do not include explanation of concepts or tutorials here.

### 4. Explanation (Understanding-oriented)
- **Goal**: Clarify background concepts, architecture choices, and design rationale.
- **Form**: Conceptual explanations, sitemaps, database relations, and trade-offs.
- **Rule**: Exclude instructions and reference details. Focus on *why* things are structured the way they are.
