# Purpose

Building modern AI applications with FastAPI and LangGraph often requires the same foundational setup. This template eliminates repetitive initial configuration by providing an almost ready to use project structure with common dependencies already configured.

## Why use this template?

- **Save time**: Skip the repetitive setup process and focus on building your application
- **Best practices**: Get a well structured project following industry standards
- **Consistency**: Maintain the same project structure across all your AI applications
- **Production-ready**: Includes essential components like database integration, API routing, and code quality tools

# Features

- API built with FastAPI
    - SSE streaming support already configured
- Environment variables management using `pydantic-settings` (remember to set your environment variables in `.env` file)
- AI framework uses LangGraph with a default ReAct workflow that lets LLMs use tools you define
    - The graph uses thread and user scoped memory through `langgraph-checkpoint-postgres`
    - Database integration for conversation state management using PostgreSQL
- Uses uv for project management
- Docker with uv and multistage build for lightweight and fast images
- Pre-commit hooks for code quality and consistency
- CI/CD templates for Github Actions
  - CI ready to use
  - CD configured for Cloud Run (GCP) deployment - requires secrets and authentication setup


# Usage

To use this template, you need [Copier](https://copier.readthedocs.io/en/stable/#installation).
The easiest way to use Copier is through `uvx`:

```shell
uvx copier copy gh:jjovalle99/fastapi-langgraph-template my_project/ --trust
```

This command copies the template (gh:jjovalle99/fastapi-langgraph-template) into your project directory (my_project/).

## Why the `--trust` flag?

The template includes automated tasks to initialize the repository and optionally create the first commit. You can see these tasks in the `copier.yml` file:

```yaml
_tasks:
  - command: [git, init]
  - command: [git, add, .]
    when: "{{ git_auto_commit }}"
  - command: [git, commit, -m, "Initial commit from {{ project_name }} template"]
    when: "{{ git_auto_commit }}"
```

However, if you prefer not to trust the template and skip the automated tasks, you can run:

```shell
uvx copier copy gh:jjovalle99/fastapi-langgraph-template my_project/ --skip-tasks
```

# Final Notes

This template uses specific dependencies and database configurations, but you can modify them to fit your needs. For example, if you want to use MongoDB instead of PostgreSQL, you can update the queries and code accordingly. 

The template is designed to be a starting point, not a rigid structure. Feel free to adapt (add/remove/modify files) it to your specific requirements and preferences.
