import { test, expect } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { mockAllApiRoutes } from "./fixtures/api-mocks";

test.describe("App Shell — Page Load & Layout", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
  });

  test("renders left panel with header and tabs", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    // Header branding
    await expect(page.locator("text=IFC-GPT")).toBeVisible();
    await expect(page.locator("text=gpt-5.4-pro")).toBeVisible();

    // Three tabs visible
    await expect(app.tabText).toBeVisible();
    await expect(app.tabDraw).toBeVisible();
    await expect(app.tabUpload).toBeVisible();
  });

  test("renders IFC drop zone in right panel when no model loaded", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    await expect(app.dropZone).toBeVisible();
    await expect(app.openIfcButton).toBeVisible();
    await expect(page.locator("text=Describe a building to get started")).toBeVisible();
  });

  test("Text/Voice tab is active by default and shows chat panel", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    await expect(page.locator("[data-testid='chat-panel']")).toBeVisible();
    await expect(page.locator("[data-testid='chat-input']")).toBeVisible();
  });
});

test.describe("App Shell — Tab Switching", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
  });

  test("switching to Upload tab shows floor plan upload", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    await app.switchToUploadTab();
    await expect(app.floorPlanUpload).toBeVisible();
    await expect(page.locator("text=Drop a floor plan here or click to browse")).toBeVisible();
  });

  test("switching to Draw tab shows visual editor", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    await app.switchToDrawTab();
    // Chat panel should no longer be visible
    await expect(page.locator("[data-testid='chat-panel']")).not.toBeVisible();
  });

  test("switching back to Text tab restores chat panel", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();

    await app.switchToUploadTab();
    await expect(page.locator("[data-testid='chat-panel']")).not.toBeVisible();

    await app.switchToTextTab();
    await expect(page.locator("[data-testid='chat-panel']")).toBeVisible();
  });
});
