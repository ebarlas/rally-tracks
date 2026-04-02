# Audit Bulk Indexing (x-pack security audit logging)

This track measures the performance impact of **x-pack security audit logging** on **bulk indexing throughput**, focusing on the `access_granted` audit event.

It runs the same bulk indexing workload with audit event emission effectively **off** vs **on** (only `access_granted`) across multiple shard counts and concurrency levels.

## Prerequisites

- Elasticsearch must run with **x-pack security enabled** (so requests are authenticated / authorized).
- Elasticsearch must be started with **audit logging enabled** (static setting):

```yaml
xpack.security.audit.enabled: true
```

Within a race, the track toggles audit event emission using the **dynamic** cluster setting:

- `xpack.security.audit.logfile.events.include`
- `xpack.security.audit.logfile.events.exclude`

`audit_mode=off` is implemented as `exclude: ["_all"]` so no audit events are emitted.

## Workload

- **Documents**: trivial synthetic docs generated in the runner:

```json
{"@timestamp":"2024-01-01T00:00:00.000Z","message":"test","counter":0}
```

- **Bulk request size**: 100 docs per request by default (`bulk_size`)
- **Index variants**: 1 / 100 primary shards (0 replicas by default)
- **Concurrency**: configurable `client_counts`

## Parameters

| Parameter | Default | Description |
|---|---:|---|
| `shard_counts` | `[1, 100]` | Shard counts to test |
| `client_counts` | `[4, 8, 16]` | Bulk indexing concurrency levels |
| `bulk_size` | `100` | Documents per bulk request |
| `total_docs` | `500000` | Approx docs indexed (per configuration, across all clients) in the measured phase |
| `warmup_docs` | `50000` | Approx docs indexed (per configuration, across all clients) in the warmup phase |
| `number_of_replicas` | `0` | Replica count |
| `max_shards_per_node` | `50000` | Value for `cluster.max_shards_per_node` to allow large-shard scenarios |

## Running

Example (benchmark-only against a running cluster):

```bash
esrally race \
  --track-path=~/Code/rally-tracks/audit_bulk_indexing \
  --pipeline=benchmark-only \
  --target-hosts=localhost:9200 \
  --client-options="basic_auth_user:'elastic',basic_auth_password:'password'" \
  --track-params="shard_counts:[1,100],client_counts:[4,8,16],bulk_size:100,total_docs:500000,warmup_docs:50000"
```

Quick single-point run:

```bash
esrally race \
  --track-path=~/Code/rally-tracks/audit_bulk_indexing \
  --pipeline=benchmark-only \
  --target-hosts=localhost:9200 \
  --client-options="basic_auth_user:'elastic',basic_auth_password:'password'" \
  --track-params="shard_counts:[1],client_counts:[8],total_docs:100000,warmup_docs:20000"
```

## Interpreting results

Each measured bulk step is named:

- `bulk--<shards>s--audit-<on|off>--<clients>c`

Compare throughput (docs/s) and service time / latency between the corresponding `audit-off` and `audit-on` steps for each `(shards, clients)` pair.

### Comparing “audit enabled” vs “audit disabled”

Because `xpack.security.audit.enabled` is **static**, comparing “audit trail not constructed at all” requires running a separate race with:

```yaml
xpack.security.audit.enabled: false
```

