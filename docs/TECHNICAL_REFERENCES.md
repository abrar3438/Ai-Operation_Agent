# Official Technical References

Use current official documentation to verify package APIs and recommended configurations at implementation time. Do not blindly copy examples for a different language or package version.

## Antigravity project rules

- [Google Antigravity — Rules](https://www.antigravity.google/docs/rules/): workspace rules can be placed in `AGENTS.md` or `GEMINI.md`; use a root `AGENTS.md` for persistent project instructions.
- [Google Antigravity — Workflows](https://www.antigravity.google/docs/ide/workflows/): workflows are reusable prompt sequences; project rules and task-by-task prompts serve different purposes.

## Agent orchestration and human approval

- [LangGraph Python documentation](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph concepts and guides](https://docs.langchain.com/oss/python/learn)

During implementation, verify the selected LangGraph version's current APIs for `interrupt`, checkpointing, persistence, retry policies, state typing, and resumption. Approval safety must be covered by executable tests; documentation alone is not enough.

## API and containerization

- [FastAPI — First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [FastAPI — Docker Containers](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker Compose — Service startup order and health checks](https://docs.docker.com/compose/how-tos/startup-order)

Use health checks to coordinate service readiness rather than assuming a started container means its database is ready. Keep runtime images and local development tools appropriately separated.

## Implementation reminders

- Choose supported versions at implementation time and lock dependencies.
- Ensure LangGraph checkpoint behavior matches the actual persistence adapter and package versions in the repository.
- Verify any third-party model platform's API format, base URL, authentication headers, structured output/tool-calling support, timeout handling, and rate-limit semantics before calling it “compatible.”
- Do not treat this reference list as evidence that the planned stack has been installed, run, or verified in this project.
