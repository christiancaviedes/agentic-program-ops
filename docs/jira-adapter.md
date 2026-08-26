# Jira Cloud Adapter

`program-ops-jira` performs a read-only Jira Cloud search and maps the returned issues into
the same validated contract used by the CLI and browser compiler. It never updates Jira.

## Authentication

Create a Jira API token with access limited to the projects needed for the program snapshot.
Keep credentials in environment variables; the adapter does not accept a token value on the
command line or write it to output.

```bash
export JIRA_BASE_URL="https://example.atlassian.net"
export JIRA_EMAIL="program-owner@example.com"
export JIRA_API_TOKEN="..."
```

## Import a program snapshot

```bash
program-ops-jira \
  --jql 'project = AIP AND fixVersion = "Pilot" ORDER BY Rank' \
  --metadata examples/jira-program-metadata.json \
  --output build/jira-program.json

program-ops build/jira-program.json --output build/jira-plan
```

The adapter maps Jira keys, summaries, assignees, projects, status, due dates, labels, and
`Blocks` issue links. Inward `Blocks` links become `depends_on` edges when both issues are in
the selected result set. The compiler still rejects unknown references and cycles.

## Trust boundary

- Jira data remains untrusted until contract validation succeeds.
- Search is capped at 100 issues per import.
- The adapter only uses `GET /rest/api/3/search`.
- Imported output is still draft and requires explicit human approval.
- Jira permissions, filters, and field configuration remain administrator responsibilities.
