import { test, expect } from "@playwright/test";
import { ChatPage } from "./pages/ChatPage";
import { FeaturePickerPage } from "./pages/FeaturePickerPage";
import { mockAllApiRoutes, mockInferError } from "./fixtures/api-mocks";

test.describe("Chat → Feature Pick → Generate Flow", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
  });

  test("Next button is disabled when input is empty", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await expect(chat.nextButton).toBeDisabled();
  });

  test("Next button enables when user types a message", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await chat.fillMessage("Create a 15-storey residential tower");
    await expect(chat.nextButton).toBeEnabled();
  });

  test("submitting prompt navigates to feature picker", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await chat.submitMessage("Create a 15-storey residential tower");

    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).toBeVisible({ timeout: 5000 });

    // Verify inferred defaults are displayed
    await expect(page.locator("text=residential")).toBeVisible();
    await expect(page.locator("text=15")).toBeVisible();
    await expect(page.locator("text=Building Features")).toBeVisible();
  });

  test("feature picker shows Back and Generate buttons", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a 10-storey commercial building");

    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).toBeVisible({ timeout: 5000 });
    await expect(featurePicker.backButton).toBeVisible();
    await expect(featurePicker.confirmButton).toBeVisible();
  });

  test("clicking Back returns to chat panel", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a building");

    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).toBeVisible({ timeout: 5000 });

    await featurePicker.clickBack();
    await expect(chat.chatPanel).toBeVisible();
    await expect(featurePicker.picker).not.toBeVisible();
  });

  test("confirming features triggers generation and shows job status", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a 15-storey residential tower");

    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).toBeVisible({ timeout: 5000 });

    await featurePicker.clickConfirm();

    // Should show a job status badge (queued or running)
    const queuedOrRunning = page.locator(
      "[data-testid='job-status-queued'], [data-testid='job-status-running'], [data-testid='job-status-complete']"
    );
    await expect(queuedOrRunning.first()).toBeVisible({ timeout: 5000 });
  });

  test("feature inference error falls back to direct generation", async ({ page }) => {
    // Override the infer mock to return 500
    await mockInferError(page);

    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a building");

    // Should skip feature picker and go straight to generation
    // The job status should appear since it falls back to dispatch("generate", ...)
    const statusBadge = page.locator(
      "[data-testid='job-status-queued'], [data-testid='job-status-running'], [data-testid='job-status-complete'], [data-testid='job-status-error']"
    );
    await expect(statusBadge.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Chat — Enter Key Submission", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllApiRoutes(page);
  });

  test("pressing Enter submits the form", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await chat.chatInput.fill("Create a building");
    await chat.chatInput.press("Enter");

    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).toBeVisible({ timeout: 5000 });
  });

  test("pressing Shift+Enter does not submit (allows newline)", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await chat.chatInput.fill("Line one");
    await chat.chatInput.press("Shift+Enter");

    // Feature picker should NOT appear
    const featurePicker = new FeaturePickerPage(page);
    await expect(featurePicker.picker).not.toBeVisible({ timeout: 1000 });

    // Chat panel should still be visible
    await expect(chat.chatPanel).toBeVisible();
  });
});
