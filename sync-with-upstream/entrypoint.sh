#!/bin/bash -eux

#
# This variable must be passed into this script.
#
UPSTREAM_REPOSITORY="$1"
UPSTREAM_BRANCH="$2"
DOWNSTREAM_BRANCH="$3"

[[ -n "${UPSTREAM_REPOSITORY}" ]] || exit 1
[[ -n "${UPSTREAM_BRANCH}" ]] || exit 1
[[ -n "${DOWNSTREAM_BRANCH}" ]] || exit 1

#
# We need these config parameters set in order to do the git-merge.
#
git config user.name "${GITHUB_ACTOR}"
git config user.email "${GITHUB_ACTOR}@users.noreply.github.com"

#
# We need the full git repository history in order to do the git-merge.
#
git fetch --unshallow

git remote add upstream "$UPSTREAM_REPOSITORY"
git fetch upstream

if git show-ref --verify --quiet "refs/heads/${DOWNSTREAM_BRANCH}"; then
	git checkout "${DOWNSTREAM_BRANCH}"
else
	git checkout -b "${DOWNSTREAM_BRANCH}"
fi

git branch --set-upstream-to "origin/${DOWNSTREAM_BRANCH}"
git reset --hard "origin/${DOWNSTREAM_BRANCH}"

git merge "upstream/${UPSTREAM_BRANCH}"

#
# In order for the "hub" command to properly detect which remote branch
# is the "tracking" branch, we must use "-u" here such that the local
# branch tracks the remote branch we're pushing to.
#
git push -f -u origin "HEAD:projects/sync-with-upstream/${DOWNSTREAM_BRANCH}"

#
# We remove this remote that we added before so the "hub" command can
# properly infer the repository to open the pull request against; i.e.
# so it'll open the pull request against the "origin" repository.
#
git remote remove upstream

#
# In order for the "hub" command to work properly when generating the
# pull request, we need to set this git configuration. This way, "hub"
# will not incorrectly assume any remote branch named the same as the
# local branch, is the tracking branch.
#
git config push.default upstream

#
# Opening a pull request may fail if there already exists a pull request
# for the branch; e.g. if a previous pull request was previously made,
# but not yet merged by the time we run this "sync" script again. Thus,
# rather than causing the automation to report a failure in this case,
# we swallow the error and report success.
#
# Additionally, as long as the git branch was properly updated (via the
# "git push" above), the existing PR will have been updated as well, so
# the "hub" command is unnecessary (hence ignoring the error).
#
git log -1 --format=%B |
	hub pull-request -F - \
	-b "${DOWNSTREAM_BRANCH}" \
	-h "projects/sync-with-upstream/${DOWNSTREAM_BRANCH}" || true
