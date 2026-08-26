# V1 Release Checklist

Prepare for `v1.0.0`, a moving `v1` tag, and GitHub Marketplace publication.

Do **not** create tags/releases or publish to Marketplace until intentionally ready.

## Checklist

1. Tests pass: `PYTHONPATH=. python -m pytest -q`
2. Docker builds: `docker build -t ai-code-review-agent-test .`
3. Sandbox PR review works end-to-end in a real repository
4. Duplicate prevention verified (rerun same head SHA → skip)
5. Clean PR verified (can publish “No meaningful issues found.”)
6. JS/TS/React buggy PR verified (meaningful findings)
7. README verified (setup, secrets, permissions, inputs)
8. LICENSE present (MIT)
9. Create `v1.0.0` tag
10. Create/update stable `v1` tag to the same commit
11. Create GitHub Release for `v1.0.0`
12. Publish to GitHub Marketplace

## Suggested sandbox scenarios

### A. Buggy TypeScript / React PR

Open a PR that introduces a deliberate bug, for example:

```tsx
export function UserCard({ user }: { user?: { name: string } }) {
  // Concrete runtime bug: user may be undefined
  return <div>{user.name.toUpperCase()}</div>;
}

export function renderSecret(token: string) {
  // Security smell: secret logged
  console.log("auth token", token);
  return token;
}

export function deadStyle() {
  const unused = 1; // objective unused local if lint-like style is visible
  return <span>ok</span>;
}
```

Expect:
- correctness and/or security findings on changed lines
- no invented issues beyond the supplied evidence

### B. Clean PR

Open a PR with a small, correct change and no secrets/logging issues.

Expect:
- no or very few findings
- summary may say “No meaningful issues found.”

### C. Duplicate prevention

1. Run the Action on head SHA `abc123` → review published
2. Re-run the same workflow for the same SHA
3. Logs should include: `Review already published for this commit. Skipping.`
4. Push a new commit `def456` → a new review is allowed

## Notes

- Marketplace publication is a separate GitHub UI/API step after the release exists.
- Keep Action branding/inputs in `action.yml` accurate before submitting.
