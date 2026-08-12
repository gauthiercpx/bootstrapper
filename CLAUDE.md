# Working in this repository

## Commit identity

Every commit must be authored **and** committed by the repository owner's
GitHub profile — not just carry their name.

```
user.name  = gauthiercpx
user.email = gauthier.coppeaux@gmail.com
```

GitHub links a commit to a profile by matching the author/committer **email**
against a verified email on the account. The name field has no effect. Using
any other address produces a commit that renders with no avatar and no profile
link, even when the name reads correctly.

Verify linkage through the API rather than by eye — `GET /repos/{owner}/{repo}/commits`
returns a top-level `author` object only when GitHub resolved the email to an
account. If that object is absent, the commit is unlinked.

Do not add `Co-Authored-By:` trailers, `Claude-Session:` trailers, or any other
assistant attribution to commit messages, PR titles, PR bodies, or code
comments.
