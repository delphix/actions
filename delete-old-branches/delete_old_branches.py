#!/usr/bin/env python3

import os
import json
import typing
import urllib.error
import urllib.parse
import urllib.request
import re
import email
import subprocess
import functools

#
# Load settings
#
class Settings:
    def __init__(self):
        print(os.environ)
        self.base_uri=os.environ["GITHUB_API_URL"]
        self.workspace=os.environ["GITHUB_WORKSPACE"]
        self.repository=os.environ["GITHUB_REPOSITORY"]

        self.repo_token=os.environ["INPUT_REPO_TOKEN"]
        self.date=os.environ["INPUT_DATE"]
        self.dry_run=os.environ.get("INPUT_DRY_RUN", "true") == "true"

        self.branch_regex=os.environ.get("INPUT_BRANCH_REGEX", "")

        self.excluded_branches = os.environ.get("INPUT_EXCLUDED_BRANCHES", "main,master,develop").split(",")
        self.excluded_branch_regex=os.environ.get("INPUT_EXCLUDED_BRANCH_REGEX", "")
        self.exclude_open_pr_branches=os.environ.get("INPUT_EXCLUDE_OPEN_PR_BRANCHES", "true") == "true"


SETTINGS = Settings()

#
# GitHub API client
#
class Response(typing.NamedTuple):
    body: str
    headers: email.message
    status: int

    def json(self) -> typing.Any:
        try:
            return json.loads(self.body)
        except Exception as e:
            raise Exception({"body": self.body, "headers": self.headers, "status": self.status}) from e

def request(
    url: str,
    method: str = "GET",
    data: dict | None = None,
) -> Response:
    """
    A simple function to make calls to GitHub
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {SETTINGS.repo_token}"
    }

    if data:
        url += "?" + urllib.parse.urlencode(data, doseq=True, safe="/")


    httprequest = urllib.request.Request(
        url, headers=headers, method=method
    )

    try:
        with urllib.request.urlopen(httprequest) as httpresponse:
            response = Response(
                headers=httpresponse.headers,
                status=httpresponse.status,
                body=httpresponse.read().decode(
                    httpresponse.headers.get_content_charset("utf-8")
                ),
            )
    except urllib.error.HTTPError as e:
        response = Response(
            body=str(e.reason),
            headers=e.headers,
            status=e.code,
        )

    return response

#
# Branch checks
#
def _excluded_branch(branch: str) -> bool:
    """
    Return True if the branch is an excluded branch
    """
    for excluded_branch in SETTINGS.excluded_branches:
        if branch == excluded_branch:
            return True

    return False


def _included_branch(branch: str) -> bool:
    """
    Return True if the branch should be included based on its name.
    """
    return bool(re.fullmatch(SETTINGS.branch_regex, branch))


def _excluded_branch_regex(branch: str) -> bool:
    """
    Return True if the branch should be excluded based on its name.
    """
    return bool(re.fullmatch(SETTINGS.excluded_branch_regex, branch))


@functools.cache
def _open_pull_request_branches() -> list[str]:
    """
    Return a cached list of all branches associated with open pull
    requests.
    """
    def _helper(page: int) -> typing.Iterable[str]:
        """
        yield the pull request branches from the given page number until the last page
        """
        #
        # Make the request
        #
        response = request(
            f"{SETTINGS.base_uri}/repos/{SETTINGS.repository}/pulls",
            data={
                "page": page,
            },
        )

        #
        # Parse the request
        #
        # Get all branches
        for pull in response.json():
            yield pull["head"]["ref"]

        # Determine if there are more results
        next_page = None
        if link_header := response.headers['Link']:
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    if match := re.search(r"[?&]page=(\d+)", link):
                        next_page = int(match.group(1))

        #
        # Recurse
        #
        if next_page:
            yield from _helper(page=next_page)

    return list(_helper(page=1))


def _open_pr_branch(branch: str) -> bool:
    """
    Return True if there are any open PRs associdated with this branch
    """
    if not SETTINGS.exclude_open_pr_branches:
        return False

    for pull_request_branch in _open_pull_request_branches():
        if branch == pull_request_branch:
            return True

    return False

def _delete_branch(branch):
    """
    Delete the branch via the GitHub API
    """
    response = request(
        f"{SETTINGS.base_uri}/repos/{SETTINGS.repository}/git/refs/heads/{branch}",
        method="DELETE",
    )
    if response.status != 204:
        raise Exception(f"Failed to delete {branch}")


def _has_been_updated_recently(branch):
    """
    Return True if the repository has been updated "recently"
    """
    #
    # Here we see if the branch has any commits since the given
    # date. If there is such a commit there will be output.
    #
    output = subprocess.check_output(["git", "log", "--oneline", "-1", f"--since='{SETTINGS.date}'", f"origin/{branch}"], text=True)
    return bool(output)


#
# Main
#
def main():
    #
    # Define was_dry_run output for the github action
    #
    print(f"::set-output name=was_dry_run::{SETTINGS.dry_run}")

    #
    # Set some git properties. First mark the repository as safe so we
    # can interact with it. Secondly automatically convert SSH URLs to
    # to https so that git-fetch will work from inside the `act`
    # docker container when testing locally.
    #
    subprocess.check_call(["git", "config", "--global", "--add", "safe.directory", SETTINGS.workspace])
    subprocess.check_call(["git", "config", "url.https://github.com/.insteadOf", "git@github.com:"])

    #
    # Find all branches in the repository. First perform a fetch from
    # upstream then list them.
    #
    try:
        # When running in GitHub actions we are mostly likely given a
        # a shallow repository. When we fetch we also want to make
        # sure that the repository is not shallow. If running through
        # `act` however its possible for the clone to be a complete
        # clone. In the case where the repository is non-shallow,
        # unshallow will fail.
        subprocess.check_call(["git", "fetch", "--all", "--prune", "--unshallow"])
    except:
        subprocess.check_call(["git", "fetch", "--all", "--prune"])
    raw_branches = subprocess.check_output(["git", "ls-remote", "-q", "--heads", "--refs"], text=True)
    branches = []
    for line in raw_branches.split("\n"):
        if line:
            _sha, ref = line.split("\t")
            branches.append(ref.removeprefix("refs/heads/"))

    #
    # Go through all branches and determine if the branch should be
    # deleted or skipped. If any clause triggers we do not perform the
    # delete.
    #
    deleted_branches = []
    almost_deleted_branches = []
    for branch in branches:
        if not _included_branch(branch):
            print(f"{branch} is not included. Skipping")
        elif _excluded_branch(branch):
            print(f"{branch} is an excluded branch. Skipping")
        elif _has_been_updated_recently(branch):
            print(f"{branch} has been updated recently. Skipping")
        elif _excluded_branch_regex(branch):
            print(f"{branch} is explicitly protected. Skipping")
        elif _open_pr_branch(branch):
            print(f"{branch} has an open pull request. Skipping")
        else:
            # There is no reason to skip the deletion so lets delete
            if SETTINGS.dry_run:
                print(f"DRY RUN: Deleting {branch}")
                deleted_branches.append(branch)
            else:
                print(f"Deleting {branch}")
                try:
                    _delete_branch(branch)
                    deleted_branches.append(branch)
                except:
                    almost_deleted_branches.append(branch)

    if almost_deleted_branches:
        raise Exception(f"A few branches were not deleted [{','.join(almost_deleted_branches)}]")

    print(f"::set-output name=deleted_branches::[{','.join(deleted_branches)}]")

if __name__ == "__main__":
    main()
