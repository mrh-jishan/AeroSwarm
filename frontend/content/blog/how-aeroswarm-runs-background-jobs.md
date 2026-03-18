---
title: How AeroSwarm runs long tasks without blocking the API
excerpt: Session bootstrap and merge preflight now run through a durable worker path instead of tying up request handlers.
publishedAt: 2026-03-17
author: AeroSwarm Team
tags:
  - architecture
  - backend
  - workers
---

Public products need predictable request handling. Long-running work inside an API route is fine for a prototype, but it becomes a reliability problem once real traffic and retries enter the system.

AeroSwarm now uses a durable background job path for the heavy operations that matter most:

- session bootstrap
- repository clone
- task decomposition
- agent launch
- merge preflight

## Why that matters

If a clone or dependency install takes time, the API can return immediately with a queued state instead of holding the request open.

That gives the product three practical benefits:

1. Better user experience in the dashboard
2. Cleaner retry behavior when work fails
3. A real worker boundary that can scale separately from the API

## What the dashboard sees

The UI now treats session and merge operations as asynchronous state machines. Users can see queued, running, failed, and completed outcomes instead of assuming every action is instant.

That is a much more realistic base for staging and public release.
