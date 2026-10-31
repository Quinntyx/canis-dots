# Personal hosting and checkout

Read this file during Stage 2: Establish source and Stage 5: Publish source of SKILL.md.
It supplies the personal setup convention without requiring another skill.

## Create a new repository

1. Bind the validated one-segment `name` and chosen visibility. Bind
   `container="$HOME/docs/src/$name"`, `primary="$container/main"`, and
   `development="$container/dev"`. Verify tools, authenticated host accounts, and an eligible
   Forgejo Actions runner label and action runtime. Existing paths retain their contents.
2. Read `~/.local/share/forgejo-cli/keys.json` in memory and select
   `hosts["git.quinntyx.dev"].token`. Use API base `https://git.quinntyx.dev/api/v1` and the HTTP
   header `Authorization: token ...`, inserting the credential in memory. Keep output redacted.
   Inspect the installed Forgejo OpenAPI schema before adapting an endpoint or request field.
3. Query `GET /repos/quinntyx/{name}` and
   `gh repo view "Quinntyx/$name" --json nameWithOwner,isPrivate,defaultBranchRef`.
   Two definite not-found results and an absent container permit step 4. Otherwise report the
   existing state or access failure through Stage 10: Report and resolve reuse explicitly.
4. Create the empty canonical repository with `POST /user/repos`, setting `name`, the selected
   `private` Boolean, `auto_init: false`, and `default_branch: main`.
   Create the same-visibility empty mirror using `gh repo create "Quinntyx/$name"` with the
   chosen `--private` or `--public` flag. Re-read both hosts to verify owner, visibility, and state.
5. Read `GET /repos/quinntyx/{name}/push_mirrors`. Create an absent mirror with
   `POST /repos/quinntyx/{name}/push_mirrors`, setting
   `remote_address: ssh://github.com/Quinntyx/{name}.git`, `interval: 8h0m0s`, and
   `sync_on_commit: true`. Use the server's established GitHub credentials and verify these fields.
6. Enable and verify Actions with `PATCH /repos/quinntyx/{name}` and `enable_actions: true`.
   Bind the verified runner label for the test workflow. An unavailable runner becomes a precise
   prerequisite report at Stage 10: Report; a ready runner continues at step 7.
7. Create the empty container and run
   `fj repo clone "quinntyx/$name" "$primary" -H https://git.quinntyx.dev -S false`.
   Verify an ordinary `.git` directory, unborn HEAD, and only canonical Forgejo `origin`.
   Run `git -C "$primary" symbolic-ref HEAD refs/heads/main` on that verified empty clone.
   Bind `target="$primary"` and return to Stage 3: Bootstrap in SKILL.md.
8. For a failed write, retain repositories, mirror, paths, and the original error. Proceed to
   Stage 10: Report. An authorized resume re-reads identity and retained state, then resumes the
   first incomplete step here. Conflicting state receives a reuse or reconciliation decision.

## Locate and clone existing source

1. Derive `name` and repository identity from the actual package source or its upstream metadata.
   Honor a supplied checkout. For personal repositories bind the same `container` and `primary`
   layout above; a genuine foreign clone uses `~/docs/src/<owner>_<name>/main` instead.
2. Verify origin identity and inspect expected paths and worktrees. Reuse matching source clones.
   For an absent personal anchor, verify hosting and run the clone command above. An explicit
   GitHub repository can use `gh repo clone "$repo_url" "$primary" --no-upstream`.
3. Preserve the existing branch/folder association and all edits. A foreign fork retains its
   genuine upstream. Canonical personal clones retain a single Forgejo `origin`; GitHub mirroring
   runs server-side. Return to Stage 2: Establish source, step 4, in SKILL.md.

## Check mirror preservation before publication

1. Bind `forge_url="https://git.quinntyx.dev/quinntyx/$name.git"` and
   `mirror_url="https://github.com/Quinntyx/$name.git"`. Inspect every branch and tag with
   `git ls-remote --heads --tags "$forge_url"` and the same command for `mirror_url`.
2. Equal refs or an empty GitHub mirror return to the calling operation in
   Stage 5: Publish source in SKILL.md.
   Otherwise compare each GitHub ref with Forgejo. An absent Forgejo ref or changed tag requires
   a preservation decision at Stage 10: Report before publishing or requesting synchronization.
3. For a differing branch head, bind its `ref`, `mirror_sha`, and `forge_sha`. Bind an absent
   `inspection` path in task artifacts and create it with `git init --bare "$inspection"`.
   Fetch that branch with `git -C "$inspection" fetch "$forge_url" "$ref"` and
   `git -C "$inspection" fetch "$mirror_url" "$ref"`. Require
   `git -C "$inspection" merge-base --is-ancestor "$mirror_sha" "$forge_sha"`.
4. Proven containment for all differing heads returns to the calling operation in
   Stage 5: Publish source. A fetch failure, race, or divergence proceeds to Stage 10: Report.
   Re-read both hosts immediately before a manual sync; preserve any newly divergent refs first.

## Verify publication and mirroring

1. After the source push, inspect the exact branch commit with
   `git -C "$target" ls-remote --heads origin "refs/heads/$branch"` and verify `delivery_sha`.
   Inspect the Forgejo Actions run for that same revision through authenticated host API or UI.
   Require the test job's completed successful result, rather than queue acceptance.
2. Re-read remote refs and verify preservation using the check above, then continue here.
   Read all pages of `GET /repos/quinntyx/{name}/push_mirrors`; verify destination and options.
   Queue `POST /repos/quinntyx/{name}/push_mirrors-sync` and poll within a bounded wait.
   Require a completed synchronization timestamp after publication and an empty `last_error`.
3. Compare every branch and tag using `git ls-remote --heads --tags "$forge_url"` and the same
   command for `mirror_url`.
   Verify the delivery ref resolves to `delivery_sha` at both hosts.
4. For a newly created project, verify both default branches are `main`. Reconcile the Forgejo
   default with `PATCH /repos/quinntyx/{name}` and `default_branch: main`, and GitHub with
   `gh repo edit "Quinntyx/$name" --default-branch main` when required.
5. Matching refs, mirror options, and completed synchronization return to Stage 6: Select the
   installed ref. A pending timeout or mismatch proceeds to Stage 10: Report with retained state.
   Existing divergent mirrors require explicit history reconciliation before a force/prune sync.
6. Authentication and host-key failures receive a server repair decision at Stage 10: Report.
   Report stored canonical origin separately from effective transport when Git URL rewrites apply.
   Keep canonical Pi package declarations on Forgejo for personal projects.
