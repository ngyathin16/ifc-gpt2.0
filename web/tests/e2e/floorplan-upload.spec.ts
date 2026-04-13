import { test, expect } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { mockAllApiRoutes } from "./fixtures/api-mocks";
import path from "path";
import fs from "fs";
import os from "os";

test.describe("Floor Plan Upload Flow", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
  });

  test("upload tab shows drop zone with accepted formats", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();
    await app.switchToUploadTab();

    await expect(app.floorPlanUpload).toBeVisible();
    await expect(page.locator("text=Drop a floor plan here or click to browse")).toBeVisible();
    await expect(page.locator("text=PDF, PNG, JPEG, TIFF, BMP")).toBeVisible();
  });

  test("selecting a file shows file name and submit button", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();
    await app.switchToUploadTab();

    // Create a temporary test PNG file
    const tmpDir = os.tmpdir();
    const tmpFile = path.join(tmpDir, "test-floorplan.png");
    // Minimal valid PNG: 1x1 transparent pixel
    const pngHeader = Buffer.from([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, // PNG signature
      0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
      0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1
      0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, // RGBA
      0x89, 0x00, 0x00, 0x00, 0x0a, 0x49, 0x44, 0x41, // IDAT
      0x54, 0x78, 0x9c, 0x62, 0x00, 0x00, 0x00, 0x02,
      0x00, 0x01, 0xe5, 0x27, 0xde, 0xfc, 0x00, 0x00,
      0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, // IEND
      0x60, 0x82,
    ]);
    fs.writeFileSync(tmpFile, pngHeader);

    // Use file chooser to select the file
    const fileInput = page.locator("[data-testid='floorplan-upload'] input[type='file']");
    await fileInput.setInputFiles(tmpFile);

    // File name should appear
    await expect(page.locator("text=test-floorplan.png")).toBeVisible();

    // Submit button should appear
    await expect(page.locator("[data-testid='floorplan-submit']")).toBeVisible();
    await expect(page.locator("text=Convert to IFC")).toBeVisible();

    // Cleanup
    fs.unlinkSync(tmpFile);
  });

  test("submitting floor plan triggers job", async ({ page }) => {
    const app = new AppPage(page);
    await app.goto();
    await app.switchToUploadTab();

    // Create temp file
    const tmpDir = os.tmpdir();
    const tmpFile = path.join(tmpDir, "test-plan.png");
    fs.writeFileSync(tmpFile, Buffer.alloc(64, 0));

    const fileInput = page.locator("[data-testid='floorplan-upload'] input[type='file']");
    await fileInput.setInputFiles(tmpFile);

    await page.locator("[data-testid='floorplan-submit']").click();

    // Should show job status
    const statusBadge = page.locator(
      "[data-testid='job-status-queued'], [data-testid='job-status-running'], [data-testid='job-status-complete']"
    );
    await expect(statusBadge.first()).toBeVisible({ timeout: 5000 });

    fs.unlinkSync(tmpFile);
  });
});
