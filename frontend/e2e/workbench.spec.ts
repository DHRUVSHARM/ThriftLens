import { expect, test, type Page, type Route } from "@playwright/test";

const textJobId = "11111111-1111-4111-8111-111111111111";
const imageJobId = "22222222-2222-4222-8222-222222222222";
const partialJobId = "33333333-3333-4333-8333-333333333333";
const possibleJobId = "44444444-4444-4444-8444-444444444444";

function jsonResponse(route: Route, payload: unknown) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function completeJob(jobId: string, brief: Record<string, unknown>) {
  return {
    jobId,
    status: "complete",
    progressMessage: "Research brief complete.",
    retryable: false,
    providerMode: "SAMPLE_MODE",
    safeError: null,
    partialBrief: null,
    finalBrief: brief,
  };
}

function queuedJob(jobId: string) {
  return {
    jobId,
    status: "queued",
    progressMessage: "Research queued.",
    retryable: false,
    providerMode: "SAMPLE_MODE",
    safeError: null,
    partialBrief: null,
    finalBrief: null,
  };
}

function researchingJob(jobId: string) {
  return {
    jobId,
    status: "researching_sources",
    progressMessage: "Planning source searches.",
    retryable: false,
    providerMode: "SAMPLE_MODE",
    safeError: null,
    partialBrief: null,
    finalBrief: null,
  };
}

async function mockHealth(page: Page, providerMode = "SAMPLE_MODE") {
  await page.route("**/api/health", async (route) =>
    jsonResponse(route, {
      service: "thriftlens-api",
      status: "ok",
      providerMode,
      checks: {
        postgres: true,
        redis: true,
        minio: true,
        geminiConfiguration: true,
        serpapiConfiguration: true,
      },
      missingProviderKeys: [],
      errors: {},
    }),
  );
}

const deskLampBrief = {
  mode: "sample",
  label: "Sample/static result",
  productReference: {
    productType: "desk lamp",
    title: "minimal black desk lamp with wireless charging",
    brand: null,
    color: "black",
    materials: [],
    keyFeatures: ["wireless charging"],
    searchQueries: ["minimal black desk lamp with wireless charging"],
    confidence: 0.82,
    assumptions: ["Sample text flow uses deterministic fixture extraction."],
  },
  trustSummary: "Found a source-backed sample match set.",
  sourceCount: 3,
  freshnessNote: "All source data is deterministic sample/static data.",
  uncertaintyNotes: ["Sample/static data, not live market research."],
  rankedProducts: [
    {
      product: {
        source: "sample-google-shopping",
        title: "Minimal Black Desk Lamp",
        retailer: "Sample Retailer",
        url: "https://example.com/sample-lamp",
        price: 42.5,
        currency: "USD",
        imageUrl: null,
        availability: "in stock",
        freshness: "sample/static",
      },
      score: 0.92,
      group: "closest",
      confidence: "high",
      reason: "Matched source-backed product data.",
    },
    {
      product: {
        source: "sample-google-shopping",
        title: "Budget Desk Lamp",
        retailer: "Sample Outlet",
        url: "https://example.com/sample-budget",
        price: 24.99,
        currency: "USD",
        imageUrl: null,
        availability: "in stock",
        freshness: "sample/static",
      },
      score: 0.68,
      group: "cheaper",
      confidence: "medium",
      reason: "Lower-priced related source result.",
    },
    {
      product: {
        source: "sample-google-shopping",
        title: "Premium Desk Lamp",
        retailer: "Sample Premium",
        url: "https://example.com/sample-premium",
        price: 89.99,
        currency: "USD",
        imageUrl: null,
        availability: "limited",
        freshness: "sample/static",
      },
      score: 0.65,
      group: "premium",
      confidence: "medium",
      reason: "Premium alternative from source data.",
    },
  ],
  userActions: ["Review matches", "Refine description"],
  statusReason: null,
};

const bottleBrief = {
  ...deskLampBrief,
  productReference: {
    productType: "water bottle",
    title: "stainless steel insulated water bottle",
    brand: null,
    color: "silver",
    materials: ["stainless steel"],
    keyFeatures: ["insulated", "reusable"],
    searchQueries: ["stainless steel insulated water bottle"],
    confidence: 0.84,
    assumptions: ["Sample image flow uses deterministic fixture metadata."],
  },
  rankedProducts: [
    {
      product: {
        source: "sample-google-shopping",
        title: "Insulated Steel Bottle",
        retailer: "Sample Retailer",
        url: "https://example.com/sample-bottle",
        price: 31.0,
        currency: "USD",
        imageUrl: null,
        availability: "in stock",
        freshness: "sample/static",
      },
      score: 0.89,
      group: "closest",
      confidence: "high",
      reason: "Matched bottle reference terms with source-backed product data.",
    },
  ],
};

const partialBrief = {
  mode: "sample",
  label: "Sample/static result",
  productReference: deskLampBrief.productReference,
  trustSummary: "Reference extracted, but source-backed research is unavailable.",
  sourceCount: 0,
  freshnessNote: "No source data was available for this run.",
  uncertaintyNotes: ["research_unavailable", "Try again when research sources are available."],
  rankedProducts: [],
  userActions: ["Retry research", "Refine the product reference"],
  statusReason: "research_unavailable",
};

const possibleOnlyBrief = {
  ...deskLampBrief,
  trustSummary: "No verified exact match was found in the source-backed sample set.",
  uncertaintyNotes: ["No verified exact match was found; showing possible alternatives instead."],
  rankedProducts: [
    {
      product: {
        source: "sample-google-shopping",
        title: "Adjustable Black Desk Lamp",
        retailer: "Sample Retailer",
        url: "https://example.com/sample-possible",
        price: 39.99,
        currency: "USD",
        imageUrl: null,
        availability: "in stock",
        freshness: "sample/static",
      },
      score: 0.48,
      group: "possible",
      confidence: "low",
      reason: "Related product, but not enough overlap for a verified match.",
    },
  ],
  statusReason: "possible_matches_only",
};

async function mockJobFlow(page: Page, jobId: string, finalPayload: Record<string, unknown>, inputType: "text" | "image") {
  await page.route("**/api/research-jobs", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }

    const postData = route.request().postData() || "";
    if (inputType === "text") {
      expect(route.request().postDataJSON()).toMatchObject({
        inputType: "text",
        textDescription: expect.any(String),
      });
    } else {
      expect(postData).toContain('name="inputType"');
      expect(postData).toContain("image");
      expect(postData).toContain("targetDescription");
    }

    return jsonResponse(route, queuedJob(jobId));
  });

  await page.route(`**/api/research-jobs/${jobId}`, async (route) => jsonResponse(route, finalPayload));
}

test("renders the unified workbench and has no horizontal mobile overflow", async ({ page }) => {
  await mockHealth(page);
  await page.setViewportSize({ width: 390, height: 820 });
  await page.goto("/");

  await expect(page.getByRole("link", { name: "ThriftLens" })).toBeVisible();
  await expect(page.getByPlaceholder("Describe the product you want to find")).toBeVisible();
  await expect(page.getByText("Drop or upload image")).toBeVisible();
  await page.getByRole("button", { name: /theme/i }).click();

  const hasNoHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(hasNoHorizontalOverflow).toBe(true);
});

test("submits a text job, polls to complete results, and copies a source-backed summary", async ({ page }) => {
  await mockHealth(page);
  await page.addInitScript(() => {
    let copiedText = "";
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: async (value: string) => {
          copiedText = value;
        },
        readText: async () => copiedText,
      },
      configurable: true,
    });
  });
  await mockJobFlow(page, textJobId, completeJob(textJobId, deskLampBrief), "text");

  await page.goto("/");
  await page.getByPlaceholder("Describe the product you want to find").fill("minimal black desk lamp with wireless charging");
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page.getByText("Preparing research").first()).toBeVisible();
  await expect(page.getByText("Sample/static").first()).toBeVisible({ timeout: 7_000 });
  await expect(page.getByRole("heading", { name: "Best match" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Minimal Black Desk Lamp", exact: true })).toBeVisible();
  await expect(page.getByText("$42.50", { exact: true })).toBeVisible();
  await expect(page.getByText("Matched source-backed product data.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Source" }).first()).toHaveAttribute("href", "https://example.com/sample-lamp");

  await page.getByRole("button", { name: "Copy" }).click();
  await expect(page.getByRole("button", { name: "Copied" })).toBeVisible();
  const copiedText = await page.evaluate(() => navigator.clipboard.readText());
  expect(copiedText).toContain("ThriftLens research brief (Sample/static result)");
  expect(copiedText).toContain("https://example.com/sample-lamp");
});

test("shows only the current substate while source research is running", async ({ page }) => {
  const jobId = "55555555-5555-4555-8555-555555555555";
  await mockHealth(page);
  await page.route("**/api/research-jobs", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    return jsonResponse(route, researchingJob(jobId));
  });
  await page.route(`**/api/research-jobs/${jobId}`, async (route) => jsonResponse(route, researchingJob(jobId)));

  await page.goto("/");
  await page.getByPlaceholder("Describe the product you want to find").fill("minimal black desk lamp with wireless charging");
  await page.getByRole("button", { name: "Start research" }).click();

  const progress = page.getByLabel("Research progress");
  await expect(progress.getByText("Searching sources").first()).toBeVisible();
  await expect(progress.getByText("Source plan", { exact: true })).toBeVisible();
  await expect(progress.getByText("Product profile", { exact: true })).toHaveCount(0);
  await expect(progress.getByText("Search context", { exact: true })).toHaveCount(0);
  await expect(progress.getByText("Live source search", { exact: true })).toHaveCount(0);
  await expect(progress.getByText("Normalize results", { exact: true })).toHaveCount(0);
});

test("validates image input and submits an image job", async ({ page }) => {
  await mockHealth(page);
  await mockJobFlow(page, imageJobId, completeJob(imageJobId, bottleBrief), "image");

  await page.goto("/");
  await page.getByRole("button", { name: "Start research" }).click();
  await expect(page.getByText("Add a product image, a description, or both before starting research.")).toBeVisible();

  await page.setInputFiles("#product-image", {
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("not an image"),
  });
  await expect(page.getByText("Unsupported image type. Use JPEG, PNG, or WebP.")).toBeVisible();

  await page.setInputFiles("#product-image", {
    name: "bottle.png",
    mimeType: "image/png",
    buffer: Buffer.from("fake png bytes"),
  });
  await expect(page.getByText("bottle.png")).toBeVisible();
  await page.getByPlaceholder("What should ThriftLens focus on in this image?").fill("the silver bottle in the center");
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page.getByText("stainless steel insulated water bottle")).toBeVisible({ timeout: 7_000 });
  await expect(page.getByRole("heading", { name: "Insulated Steel Bottle", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("article").getByText("$31.00", { exact: true })).toBeVisible();
});

test("renders research unavailable partial state without fake product cards", async ({ page }) => {
  await mockHealth(page);
  await page.route("**/api/research-jobs", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    return jsonResponse(route, queuedJob(partialJobId));
  });
  await page.route(`**/api/research-jobs/${partialJobId}`, async (route) =>
    jsonResponse(route, {
      jobId: partialJobId,
      status: "partial",
      progressMessage: "Product reference extracted, but research sources are unavailable.",
      retryable: true,
      providerMode: "SAMPLE_MODE",
      safeError: null,
      partialBrief,
      finalBrief: null,
    }),
  );

  await page.goto("/");
  await page.getByPlaceholder("Describe the product you want to find").fill("minimal black desk lamp with wireless charging");
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page.getByText("Research sources are unavailable", { exact: true })).toBeVisible({ timeout: 7_000 });
  await expect(page.getByText("Reference extracted, but source-backed research is unavailable.").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Source" })).toHaveCount(0);
});

test("separates possible matches when no verified match exists", async ({ page }) => {
  await mockHealth(page);
  await mockJobFlow(page, possibleJobId, completeJob(possibleJobId, possibleOnlyBrief), "text");

  await page.goto("/");
  await page.getByPlaceholder("Describe the product you want to find").fill("no verified black desk lamp");
  await page.getByRole("button", { name: "Start research" }).click();

  await expect(page.getByRole("heading", { name: "Best available match" })).toBeVisible({ timeout: 7_000 });
  await expect(page.getByText("Review caveats")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Adjustable Black Desk Lamp", exact: true }).first()).toBeVisible();
  await expect(page.getByText("Related product, but not enough overlap for a verified match.")).toBeVisible();
});
