# Conventional Commits

This repository follows [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#specification); please add your conventional commit message to this PR's description in the form:

```text
type[!]: description

[body]

[footer(s)]
```

- Type may be one of (feat, fix, refactory, test, chore, docs)
- Breaking changes must be indicated with an exclamation point after the type, as well as a mention of the change in the footer in the following format:

```text
BREAKING CHANGE: description
```

Additionally, references to a Jira ticket or GitHub issue should be placed in the footer.

## Example

```text
feat!: reorganize commands into new structure, remove debug command

- use subcommands to group similar commands together
- removed "debug" command

BREAKING CHANGE: the "debug" command no longer exists. All other commands have a new format.
Resolves: Jira:5231
```
