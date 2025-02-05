# Conventional Commits

This repository follows [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#specification); please add your conventional commit message to this PR's **title** in the form:

```text
type[!]: description
```

- Type may be one of (feat, fix, refactory, test, chore, docs)
- Breaking changes must be indicated with an exclamation point after the type

You may additionally put a commit message body and footer(s) in the PR description of the form:

```
[body]

[footer(s)]
```

Any breaking changes must indicate the change in the footer as such:

```text
BREAKING CHANGE: description
```

Finally, references to a Jira ticket or GitHub issue should be placed in the footer.

## Example

### PR title
```text
feat!: reorganize commands into new structure, remove debug command
```

### PR description

```text
- use subcommands to group similar commands together
- removed "debug" command

BREAKING CHANGE: the "debug" command no longer exists. All other commands have a new format.
Resolves: Jira:5231
```
