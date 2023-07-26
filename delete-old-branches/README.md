# Delete Old Branches Action

This action is meant to cleanup old lingering branches in a
repository. There are a number of dials that you can play with to only
select the branches that you want gone.

This action is originally based off of:
 - https://github.com/icyak/delete-old-branches-action/tree/master

but was translated to Python and tweaked to work better with how
branches are used at Delphix.

## Inputs

| Input                    | Description                                                  |
|--------------------------|--------------------------------------------------------------|
| repo_token               | *Required*: The GITHUB_TOKEN secret                          |
| date                     | *Required*: A git-log compatible date format. (3 months ago) |
| dry_run                  | *Required*: Run in dry-run mode so no branches are deleted   |
| branch_regex             | A regex for branches to include                              |
| excluded_branches        | A comma seperated list of branch(es) to exclude              |
| excluded_branch_regex    | A regex for branches to exclude.                             |
| exclude_open_pr_branches | Exclude branches that have an open pull request              |

## Examples

There are two ways to use the action. You can use the action in your
own workflow directly, or you can use the reusable workflow defined in
this repository.
 - The reusable workflow that consumes this action: [../.github/workflows/delete-old-branches-workflows.yaml](../.github/workflows/delete-old-branches-workflows.yaml)
 - Post push automation that consumes the reusable workflow [../.github/workflows/delete-old-branches.yaml](../.github/workflows/delete-old-branches.yaml)

### Using the action directly

1. Only run against certain branches via include:
   ```yaml
   jobs:
     housekeeping:
       name: Cleanup old branches
       runs-on: ubuntu-latest
       permissions:
         contents: write
         pull-requests: read
       steps:
         - name: Checkout repository
           uses: actions/checkout@v2
         - name: Run delete-old-branches-action
           uses: ./delete-old-branches
           with:
             repo_token: ${{ github.token }}
             date: '3 months ago'
             dry_run: true
             branch_regex: 'dlpx/.*|projects/.*|dependabot/.*|gh-readonly-queue/.*'
   ```
2. Only run against certain branches via exclude:
   ```yaml
   jobs:
     housekeeping:
       name: Cleanup old branches
       runs-on: ubuntu-latest
       permissions:
         contents: write
         pull-requests: read
       steps:
         - name: Checkout repository
           uses: actions/checkout@v2
         - name: Run delete-old-branches-action
           uses: ./delete-old-branches
           with:
             repo_token: ${{ github.token }}
             date: '3 months ago'
             dry_run: true
             excluded_branches: 'develop,patch,release,main'
             excluded_branch_regex: 'projects/.*'
   ```

### Using the reusable workflow instead of the action

1. Use the default settings
   [../.github/workflows/delete-old-branches.yaml](../.github/workflows/delete-old-branches.yaml)
2. Only run against certain branches via include:
   ```yaml
   jobs:
     delete-old-branches:
       uses: ./.github/workflows/delete-old-branches-workflow.yml
       permissions:
         contents: write
         pull-requests: read
       with:
         branch_regex: 'dlpx/.*|projects/.*|dependabot/.*|gh-readonly-queue/.*'
   ```
3. Only run against certain branches via exclude:
   ```yaml
   jobs:
     delete-old-branches:
       uses: ./.github/workflows/delete-old-branches-workflow.yml
       permissions:
         contents: write
         pull-requests: read
       with:
         excluded_branches: 'develop,patch,release,main'
         excluded_branch_regex: 'projects/.*'
   ```

## Testing

It is possible to test this action using [act](https://github.com/nektos/act).

## Testing by running the workflow

To test it as part of the workflow  you can run:
```console
$ act -W .github/workflows/delete-old-branches-workflow.yaml -s GITHUB_TOKEN="$GITHUB_TOKEN"
```
You can also use `--input` to change some values like:
```console
$ act -W .github/workflows/delete-old-branches-workflow.yaml -s GITHUB_TOKEN="$GITHUB_TOKEN" --input branch_regex='dlpx/.*|projects/.*|dependabot/.*|gh-readonly-queue/.*'
```

## Testing by running the post push action that consumes the workflow

N.B. When testing the post-push action you cannot specify any inputs.

```console
$ act -j delete-old-branches -s GITHUB_TOKEN="$GITHUB_TOKEN"
```
