import type { Page } from "@playwright/test";

export interface MockFeature {
  id: string;
  category: string;
  label: string;
  description: string;
  default_for: string[];
  conflicts_with?: string[];
}

export interface MockInferredDefaults {
  building_type: string;
  num_storeys: number;
  floor_to_floor_height: number;
  default_features: string[];
}

export const MOCK_FEATURES: MockFeature[] = [
  {
    id: "rc_frame",
    category: "Structure",
    label: "RC Frame",
    description: "Reinforced concrete frame structure",
    default_for: ["residential", "commercial"],
  },
  {
    id: "curtain_wall",
    category: "Facade",
    label: "Curtain Wall",
    description: "Full glass curtain wall facade",
    default_for: ["commercial"],
    conflicts_with: ["precast_facade"],
  },
  {
    id: "precast_facade",
    category: "Facade",
    label: "Precast Facade",
    description: "Precast concrete facade panels",
    default_for: ["residential"],
    conflicts_with: ["curtain_wall"],
  },
  {
    id: "core_lift",
    category: "Vertical Circulation",
    label: "Lift Core",
    description: "Central lift/elevator core",
    default_for: ["residential", "commercial"],
  },
];

export const MOCK_INFERRED_DEFAULTS: MockInferredDefaults = {
  building_type: "residential",
  num_storeys: 15,
  floor_to_floor_height: 3.0,
  default_features: ["rc_frame", "precast_facade", "core_lift"],
};

export const MOCK_JOB_RESPONSE = {
  job_id: "test-job-123",
  status: "queued" as const,
};

/**
 * Set up all API route mocks for E2E tests.
 * Intercepts fetch calls to /api/* and returns mock data.
 */
export async function mockAllApiRoutes(page: Page) {
  // GET /api/features
  await page.route("**/api/features", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_FEATURES),
      });
    }
    return route.fallback();
  });

  // POST /api/features/infer
  await page.route("**/api/features/infer", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_INFERRED_DEFAULTS),
      });
    }
    return route.fallback();
  });

  // POST /api/generate
  await page.route("**/api/generate", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_JOB_RESPONSE),
      });
    }
    return route.fallback();
  });

  // POST /api/build-from-plan
  await page.route("**/api/build-from-plan", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_JOB_RESPONSE),
      });
    }
    return route.fallback();
  });

  // POST /api/floorplan
  await page.route("**/api/floorplan", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_JOB_RESPONSE),
      });
    }
    return route.fallback();
  });

  // POST /api/voice
  await page.route("**/api/voice", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_JOB_RESPONSE),
      });
    }
    return route.fallback();
  });

  // GET /api/status/*/stream — SSE mock (immediate complete)
  await page.route("**/api/status/*/stream", (route) => {
    return route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        `data: ${JSON.stringify({ status: "running", ifc_url: null, error: null })}`,
        "",
        `data: ${JSON.stringify({ status: "complete", ifc_url: "/workspace/test.ifc", error: null })}`,
        "",
      ].join("\n"),
    });
  });
}

/**
 * Mock the features/infer endpoint to return an error.
 */
export async function mockInferError(page: Page) {
  await page.route("**/api/features/infer", (route) => {
    return route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Inference service unavailable" }),
    });
  });
}

/**
 * Mock the generate endpoint to return an error job.
 */
export async function mockGenerateError(page: Page) {
  await page.route("**/api/generate", (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ job_id: "error-job", status: "error", error: "Generation failed" }),
    });
  });
}
