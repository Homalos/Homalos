# Git Standards

## Commit Standards

Sample Git commit record: [type]: [description]. A specific example is docs: updating the README file.
The following are the enumeration values for type:

- feat: New features
- fix: Bug fixes
- docs: Documentation comments
- style: Code formatting (changes that do not affect code execution)
- refactor: Refactoring and optimization (neither adding new features nor fixing bugs)
- perf: Performance optimization
- test: Adding tests
- chore: Changes to the build process or auxiliary tools
- revert: Reverting a change
- build: Packaging

## Branch Management

- main/master: Main branch, maintaining a stable and releasable state
- develop: Development branch, containing the latest development features
- feature/*: Feature branches, used for developing new features
- bugfix/*: Bugfix branches, used for fixing bugs
- release/*: Release branches, used to prepare for releases

## Important Principles

- **Important**: Do not automatically commit Git code unless explicitly prompted to do so
- Ensure that all tests pass before committing
- Keep commit messages concise and clearly describe the changes
- Avoid large commits and try to break down changes into small, relevant commits.
- Submit descriptions in English by default, unless explicitly requested in Simplified Chinese.