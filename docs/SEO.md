# Search and AI discoverability

## Implemented

- Complete semantic HTML for the public homepage, two practical guides and privacy.
- Unique titles/descriptions, canonical URLs, Open Graph/Twitter metadata and a
  real 1200×630 social image.
- SoftwareApplication and TechArticle structured data matching visible content.
- Crawlable internal links, sitemap.xml and robots.txt.
- A concise llms.txt with source links, product boundaries and model evidence.
- A self-hosted variable font, no third-party tracking scripts and no frontend
  framework bundle required to read the public content.
- Private workspace routes excluded from indexing; private responses no-store.
- Useful search language: safety incident triage, corrective action tracking,
  safety shift handover, explainable severity classification, open-source safety
  operations workspace. Content uses these naturally, without keyword stuffing.

The Cloud Run URL is the current canonical origin. On a future custom domain,
update `BASE` in apps/web/routes.py and scripts/build_web.py, regenerate HTML,
add redirects from the previous origin and resubmit the new sitemap.

## Owner follow-up

1. Verify the deployed origin in Google Search Console (or a custom domain using
   DNS verification), then submit `/sitemap.xml`.
2. Inspect homepage and guide URLs for crawl/index status after deployment.
3. Connect the public GitHub repository homepage and relevant topics.
4. Publish an honest project walkthrough linking to the website and source.
5. Gather actual user feedback before claiming adoption, retention or time savings.

Search Console account access/verification is not configured by this repository.
No search-engine submission or ranking is claimed unless separately recorded.

## What this does not promise

Indexing, ranking, rich results and AI recommendations are outside the project's
control. Google's own guidance says the same SEO fundamentals apply to AI features;
there is no special required AI file or schema. llms.txt is a convenience for
agents, not a ranking mechanism. Structured data must remain factual; do not add
fake reviews, customers, safety outcomes or unsupported performance claims.

Primary reference: https://developers.google.com/search/docs/appearance/ai-features
