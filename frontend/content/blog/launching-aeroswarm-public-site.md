---
title: Launching the AeroSwarm public site
excerpt: Why we split the product dashboard from the public surface and what we optimized for in the first SEO pass.
publishedAt: 2026-03-17
author: AeroSwarm Team
tags:
  - launch
  - seo
  - product
---

AeroSwarm started as an operator dashboard first. That is normal for infrastructure-heavy products, but it is not enough when the product needs to be discovered, evaluated, and shared publicly.

The first public-site pass focused on four things:

## 1. Route separation

The authenticated product experience now lives at `/dashboard`, while the root route is free to work as a public homepage. That matters for both human visitors and crawlers.

## 2. Indexable content

We added a blog backed by markdown files so product updates, deployment notes, and launch content can live in the repo and ship with the app.

## 3. Crawl metadata

The public site now exposes page metadata, a sitemap, and a robots policy that keeps the dashboard out of search indexing.

## 4. Trust pages

Security, privacy, terms, and contact pages give prospects somewhere to go when they want operational answers instead of a product demo.

This is the baseline. The next useful step is publishing deeper technical content about deployment, orchestration, and merge review workflows.
