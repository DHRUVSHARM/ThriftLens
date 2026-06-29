# PRD: ThriftLens

Status: Product-approved draft; technical design decisions reflected

## 1. Summary

Build an AI-assisted product research app for two related shopping moments: when a user already has a product image, and when a user only has a rough idea in words. The app should identify or structure the product concept, help the user say "yes, similar to this," then research current pricing and comparable products.

- Problem category: README option 2, a deployable AI mini-app for a small problem from the author's own life.
- Target user: inspiration shoppers using text to describe a product vibe, and deal/comparison shoppers using an existing product image to find price context and alternatives.
- Primary V1 job: support both "I have an image of a product" and "I have a product idea in words" as first-class starting points.
- Product coverage: general product research; examples may focus on specific categories for validation, but the product should not rely on category-specific hardcoding.
- Positioning: practical smart-shopping assistant with a source-backed research workbench underneath. The hook is fast value-aware shopping help; the UI should support analytical comparison.
- Core workflow: upload image or enter text description -> identify or create a searchable product reference -> extract product attributes -> research web/product sources -> return current price context and similar products.
- AI role: vision-based extraction, text-to-product-reference interpretation, clarification when the description is insufficient, structured product normalization, web research synthesis, similarity/ranking, and recommendation explanation.
- Desired user moment: user starts with either a product image or a fuzzy text idea and gets a usable product reference, latest price context, and comparable real-product suggestions without manually searching across multiple sites.

## 2. User and Problem

### Target User

The first target users are:

- Inspiration shoppers who can describe a product idea, style, or vibe in words and need a product reference they can confirm before searching for real similar products.
- Deal/comparison shoppers who already have a product image or screenshot and want to find current price context plus similar alternatives.

### Current Pain

Product research is fragmented. A user may have an image, screenshot, or vague description, but finding the actual product, current pricing, comparable alternatives, and price-range context requires manual searching across shopping pages, search engines, image search, marketplaces, and review pages. When the user only has words, there is an extra gap: they need the app to turn the concept into a structured reference before searching for real similar products.

### Why Existing Solutions Fall Short

Normal search works best when the user already knows the product name or exact terms. Image search can find visually similar items but often leaves the user to compare prices and product quality manually. Chat tools can reason about a product description, but they may not reliably ground claims in current web data or present comparable options in a structured way.

### Success Criteria

The user should be able to provide an image or description and quickly receive a searchable product reference plus a structured, source-aware product brief that identifies the best match and the best-value alternatives worth checking next.

## 3. Core Use Case

### Input

What does the user provide?

Primary inputs:
- Product image upload for "I have this product/image" research
- Text description for "I am thinking of a product like this" research

Text-description input requires a concept-to-reference step: the app should turn the user's words into a structured product reference that the user can confirm or refine. If the description is too vague, the app should ask for targeted clarification. This reference is not treated as a real purchasable product; it is a search anchor for finding similar real products.

### Output

What concrete artifact does the app produce?

The app produces a product research brief:
- search reference or input summary, clearly labeled as either user-provided or generated
- likely product identity or category
- extracted visual/text attributes
- exact source-backed prices where available
- similar products
- observed source-backed price-range comparison when multiple products or sources exist
- recommendation or ranking notes
- source links and confidence/uncertainty

### Primary Flow

1. User uploads a product image or enters a product description.
2. If the input is text-only, the app converts the description into a structured product reference, asking targeted clarification questions only when needed.
3. App/AI extracts product category, visible/textual attributes, likely brand/model signals, and search terms.
4. App uses a research client layer to query web/product sources for matching and similar products.
5. App/AI reasons about likely matches, pricing context, and comparable alternatives.
6. App produces the product reference and structured research brief together.
7. User reviews source links, confidence, similar products, and next actions.
8. User can refine the reference, description, or preferences and rerun research.

## 4. AI Workflow

### Agent Goal

The AI agent's fixed goal is to turn a product image or text description into a grounded, reviewable product research brief. For image input, it should identify and research the product. For text-only input, it should create a structured product reference and use it to research similar real products in the same flow, asking clarifying questions only when the input is too ambiguous to proceed. Generated visual references are out of scope for V1; if added later, they must be treated as search anchors, not as real product listings.

### Perception

What the AI must identify from the input:

- Facts: visual or textual product attributes, apparent product category, possible brand/model clues, materials, color, style, and visible identifiers.
- Entities: product type, brand candidates, model/product-name candidates, retailers/marketplaces, similar items.
- Constraints: user-provided price range, preferred ordering, similarity preference, or shopping context if provided.
- Dates/times: current pricing freshness and source timestamp where available.
- Preferences: optional user preference such as similar price range, cheaper alternatives, premium alternatives, or closest visual match.
- Missing information: unclear brand/model, insufficient image quality, unavailable current pricing, unavailable source confidence.
- Contradictions: cases where image-derived attributes and web results disagree.

### Reasoning

What the AI must decide or infer:

- Priorities: likely exact match first, then visually/functionally similar products, then price-range alternatives.
- Tradeoffs: exact visual match vs. better price, same category vs. same brand, current price vs. confidence in match.
- Risks: hallucinated product identity, stale price data, affiliate/SEO spam, visually similar but functionally different products.
- Confidence: confidence should be shown for product identification and price/source reliability.
- Recommendation: default ranking should lead with the closest verified match, then organize alternatives into cheaper, similar-price, and premium groups when enough source data exists. When source coverage and confidence are sufficient, the app should also label picks such as best overall, best match, best value, cheapest, and premium pick.
- Follow-up questions: ask only when necessary, such as when the image is too ambiguous or the user has not specified whether they want cheaper, similar, or premium alternatives.

### Action / Output

What the AI is allowed to produce:

- Product attribute extraction
- Product concept interpretation from text
- Search reference generation for text-only concepts, after structured reference extraction
- Search queries or research strategy
- Structured product research brief
- Ranked similar products with explanations
- Confidence and uncertainty notes

What the AI is not allowed to do:

- Invent exact prices without source support
- Claim a product is an exact match when confidence is low
- Present a generated product reference as a real purchasable product
- Hide uncertainty about stale or unavailable pricing
- Purchase, add to cart, or perform external side effects automatically

### Feedback / Validation Loop

How we decide whether output is usable:

- Required fields: input summary, extracted attributes, product/category hypothesis, price context, similar products, source links, confidence notes.
- Schema validation: product brief must be structured before rendering.
- Confidence threshold: low-confidence matches should be labeled as possible matches, not exact matches.
- Missing-info handling: show what could not be determined and suggest a better image or more description.
- Repair/retry behavior: retry or repair invalid structured output; preserve user input if model or research fails.

### Structured Product Reference

The structured product reference is the durable artifact passed from the vision/text extraction step to downstream research and ranking agents. V1 should include:

- Product category
- Short product description
- Visual/text attributes
- Style or aesthetic tags
- Color and materials
- Notable features
- Possible brand/model clues
- Generated search queries
- Confidence
- Missing information or warnings

## 5. Product Scope

### In Scope for V1

- Product image upload as primary input.
- Text product description as secondary input.
- Text-only product ideas should not require a separate confirmation step before research unless the input is too ambiguous; the app should show the reference and results together, then support refinement and rerun.
- Structured product reference creation from text is required; generated visual reference creation is out of scope for V1.
- Targeted clarification questions are allowed when the text description lacks enough information to create a useful product reference.
- Clear labeling that generated or synthesized product references are only references for finding similar real products.
- AI extraction of product attributes and likely search terms.
- Web/product research for current price context and similar products.
- Structured product research brief with source links and uncertainty.

### Out of Scope for V1

- Purchasing or checkout.
- User accounts and saved history. These may be useful later, but V1 should prove the core research workflow without requiring identity or persistence.
- Long-term price tracking or alerts.
- Browser extension.
- Full marketplace inventory ingestion.
- Full market research or competitive analysis.
- Guaranteed exact product identification.
- Claiming generated references are available to buy.
- Automatic external actions without user confirmation.
- Multi-turn visual design iteration beyond lightweight product-reference refinement.

### Future Roadmap / V2

- User accounts and saved research history.
- Price tracking, alerts, and change notifications.
- Browser extension or share-sheet workflow for researching products from any page.
- More marketplace, retailer, and shopping/search adapters behind the research client layer.
- Richer generated product reference images.
- Multi-turn visual refinement for product ideas.
- Product comparison collections or boards.
- Broader market/competitive research after the product-comparison workflow is proven.

### Example Inputs

Include realistic examples for development, validation, and walkthroughs. The product should support general products rather than being hardcoded to these examples.

- Upload a product photo/screenshot and find current price plus similar alternatives.
- Enter a text description such as "minimal black desk lamp with wireless charging" and get comparable product suggestions.
- Enter a fuzzy product idea, create a structured search reference, confirm "similar to this," then research similar real products.

## 6. Requirements

### Functional Requirements

Input and setup:
- User can start from a product image upload.
- User can start from a text description of a product idea.
- User can optionally provide preference signals such as ranking preference, desired price range/budget, cheaper alternatives, closest visual match, premium alternatives, or category constraints.
- User may provide location or marketplace/source preference if supported by the research layer, but V1 should not require these inputs to run.
- User can run the workflow without creating an account.

Product reference creation:
- For image input, the system extracts a product reference from the uploaded image.
- For text input, the system creates a structured product reference from the user's description.
- If text input is too vague, the system asks targeted clarification questions instead of guessing.
- If a generated or synthesized visual reference is used, the system must label it as a non-purchasable reference for finding similar real products.
- User can inspect, edit, or refine the product reference after seeing research results, then rerun research.

AI extraction:
- AI must extract product category, visible/textual attributes, style, color, materials, notable features, and possible brand/model clues.
- AI must identify uncertainty, missing information, and possible contradictions between user input and researched results.
- AI must produce structured output that can be validated before display.

Research and comparison:
- System researches real matching or similar products through a pluggable research client layer.
- The research layer may use shopping/search APIs, retailer-specific adapters, or other source connectors selected during technical design.
- System returns exact source-backed prices where available.
- System returns observed source-backed price ranges when multiple sources or comparable products exist.
- System returns similar product suggestions with source links.
- System should support progressive result quality: at minimum, return one verified match or clearly state no verified match; when enough source data is available, return multiple alternatives; ideally organize alternatives into cheaper, similar-price, and premium groups.
- System should organize suggestions with the closest verified match first, followed by cheaper, similar-price, and premium groups when enough source data exists.
- System should add recommendation labels such as best overall, best match, best value, cheapest, or premium pick when supported by source data and confidence.
- Weak or partial matches should be shown separately as possible matches, not mixed with verified matches.
- When only weak or partial matches are available, the app should preserve the product reference, show possible matches with low-confidence labels, and ask the user to refine the image, description, or preferences.
- System must not invent exact prices, retailers, or product availability without source support.

Results and review:
- App displays a structured product research brief with product reference, extracted attributes, price context, similar products, source links, confidence, and uncertainty.
- User can inspect why a product was suggested.
- Each product result should show trust signals where available: source links, confidence label, match reasoning, and pricing/source freshness timestamp.
- User can open source links and product links.
- User can copy or share the research brief.
- User can rerun research after editing the description, reference, or preferences.
- System must clearly separate generated/search-reference content from real product listings.

### Non-Functional Requirements

- Scalability: the service architecture should be able to scale to more users, product searches, and marketplace/source integrations without coupling UI, AI extraction, research, and result-ranking logic into one brittle path.
- Extensibility: research sources should be abstracted behind a client/server boundary, such as an MCP-style research client, so shopping/search APIs and retailer-specific sources can be added or swapped without rewriting the core product flow.
- Low latency: the service should minimize end-to-end wait time where possible by avoiding unnecessary model calls, parallelizing independent research steps when safe, caching repeatable work, and showing progress for slower AI/web research operations.
- Availability: the API should remain available for users who depend on product-price research, with graceful degradation when AI providers, web research, or individual marketplace sources are unavailable.
- Reliability: product matches, price context, and similar-product suggestions should be as verifiable as possible through source links, confidence labels, and clear separation between observed facts and AI interpretation.
- Accuracy: the system should prefer saying "not enough information" or "no verified match found" over presenting low-confidence product identities, prices, retailers, or availability as facts.
- Source grounding: any exact price, retailer, availability, or product listing claim must be backed by a visible source link or clearly marked unavailable/uncertain.
- Price context: use exact source-backed prices where available, plus observed source-backed price ranges when multiple products or sources exist. Do not invent unsupported market estimates.
- Privacy/security: uploaded images may be stored temporarily on the server only long enough to support vision extraction, retries, and the active workflow. Raw images should be deleted after a strict TTL or workflow completion. The durable artifact should be the structured product reference, not the raw image.
- Accessibility: image upload and text input should be usable with keyboard and clear labels.
- Fresh container setup: app must run from documented commands.
- Fallback/sample mode: if live AI or web research is unavailable, show clearly labeled sample results only as a way to demonstrate the interface. Sample results must not be presented as live prices or fresh research.

## 7. Failure States

Define expected behavior for:

- Empty input: show validation guidance before creating a research job or making model/provider calls.
- Low-quality input: ask for a clearer image or more description.
- Temporary image unavailable: if the raw image has expired or was deleted after TTL, preserve the structured product reference if available and ask the user to re-upload only if vision extraction must be rerun.
- Product not found: show that no verified match was found, preserve extracted attributes, and suggest how the user can improve the query or image.
- Insufficient product information: show which details are missing, such as brand, model, category, distinguishing features, or price constraints.
- Weak/partial matches only: show them in a separate possible-matches section with low-confidence labels and refinement guidance.
- Missing API key: show clearly labeled sample mode or setup guidance with clear messaging.
- Model timeout: preserve input and allow retry.
- Invalid model output: attempt repair or show recoverable error.
- Web research unavailable: explain that live research is unavailable, preserve extracted product reference, and offer retry or clearly labeled sample mode.
- Degraded dependency: if one marketplace/source/provider fails, show available partial results and clearly mark unavailable sections instead of failing the full workflow when possible.
- Hallucinated or unsupported claims: unsupported prices/products should not be shown as facts.
- Generated reference confusion: label generated/search-reference images or concepts as non-purchasable references and point users toward sourced real-product matches.
- Conflicting user input: surface the conflict and label uncertain matches.
- Partial result: show available extraction/research and mark missing sections.
- Server-side issue: show a clear recoverable error, avoid losing the user's input, and distinguish server failure from "no product found."
- User wants to edit/retry: allow changing description/image and rerunning research.

## 8. UX Notes

### First Screen

The first screen should be a product research workbench, not a landing page or linear wizard. It should give the user immediate access to:

- Image upload and text description input
- Product reference panel with extracted/editable attributes
- Preference controls: ranking preference and optional price/budget input
- Optional advanced controls: location or marketplace/source preference when supported by the research layer
- Research status/progress
- Result cards for verified matches, possible matches, and grouped alternatives

### Key States

- Empty state: invite upload or text description with one sample product.
- Loading state: show extraction/research progress, not a blank spinner.
- Success state: show structured product brief, price context, similar products, sources, confidence, match reasoning, and freshness timestamps when available.
- Error state: explain whether extraction, model call, or research failed.
- Needs-review state: label low-confidence identity or stale/missing pricing clearly.

### Review/Edit Behavior

User should be able to inspect extracted attributes, edit/refine the product description or reference, and rerun research. The default flow should avoid blocking pre-research confirmation unless clarification is necessary.

### Export / Save Behavior

V1 should support copying or sharing the research brief and opening source/product links. Account-based saved history is out of scope; users can refine and rerun the current result in-session.

## 9. Acceptance Criteria

- [ ] User can complete the core flow end-to-end.
- [ ] AI output is structured and validated before display.
- [ ] User can distinguish extracted facts from assumptions or recommendations.
- [ ] If research succeeds, the app returns at least one verified product match or clearly explains why no verified match was found.
- [ ] Weak or partial matches are separated from verified matches and clearly labeled.
- [ ] Product pricing claims include source links or are clearly marked unavailable/uncertain.
- [ ] Similar product suggestions include enough context to understand why they were suggested.
- [ ] Result trust signals include source links, confidence labels, match reasoning, and freshness timestamps when available.
- [ ] Recommendation labels are only shown when supported by source data and confidence.
- [ ] When enough source data exists, results can show cheaper, similar-price, and premium alternatives.
- [ ] Generated or synthesized product references are clearly labeled as references, not real purchasable products.
- [ ] Product-not-found and insufficient-information states are clear and actionable.
- [ ] Web research unavailable/server-side failure states are distinct from "no product found."
- [ ] Fallback/sample results are clearly labeled and never presented as live research.
- [ ] Missing API key has clear setup guidance or sample-mode behavior.
- [ ] Invalid model output does not crash the app.
- [ ] User can edit or reject AI output before relying on it.
- [ ] The app is runnable from documented setup commands.
- [ ] Core AI failure modes have tests or documented smoke checks.

## 10. Validation Examples

Use these representative examples for fixtures, tests, and walkthroughs. They should validate general product behavior without hardcoding category-specific logic.

- Text-description flow: "minimal black desk lamp with wireless charging"
- Image-style flow: a clear product photo/screenshot fixture for a stainless steel insulated water bottle

Generated reference images are out of scope for V1 and belong in the future roadmap.
