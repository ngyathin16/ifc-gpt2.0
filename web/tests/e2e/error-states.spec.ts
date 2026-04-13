import { test, expect } from "@playwright/test";
import { ChatPage } from "./pages/ChatPage";
import { AppPage } from "./pages/AppPage";
import { mockAllApiRoutes, mockGenerateError } from "./fixtures/api-mocks";

test.describe("Error States", () => {
  test("generation error shows error badge with message", async ({ page }) => {
    await mockAllApiRoutes(page);
    await mockGenerateError(page);

    const chat = new ChatPage(page);
    await chat.goto();

    // Skip feature picker by making infer fail so it falls back to direct generation
    // But that would use the generate mock. Let's trigger generation via the flow.
    // The generate mock returns status: "error" with error message.

    // We need to get past the feature picker. Let's submit, pick features, confirm.
    await chat.submitMessage("Create a building");

    // Feature picker appears (infer still works)
    const confirmBtn = page.locator("[data-testid='feature-confirm-button']");
    await expect(confirmBtn).toBeVisible({ timeout: 5000 });
    await confirmBtn.click();

    // Should show error status badge
    await expect(page.locator("[data-testid='job-status-error']")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("[data-testid='job-error-message']")).toBeVisible();
    await expect(page.locator("[data-testid='job-error-message']")).toContainText("Generation failed");
  });

  test("network error on generate shows error status", async ({ page }) => {
    await mockAllApiRoutes(page);

    // Override generate to simulate network failure
    await page.route("**/api/generate", (route) => {
      return route.abort("connectionrefused");
    });

    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a building");

    const confirmBtn = page.locator("[data-testid='feature-confirm-button']");
    await expect(confirmBtn).toBeVisible({ timeout: 5000 });
    await confirmBtn.click();

    // Should show error state (useJob catch block sets error)
    await expect(page.locator("[data-testid='job-status-error']")).toBeVisible({ timeout: 5000 });
  });

  test("after error, user can return to prompt step", async ({ page }) => {
    await mockAllApiRoutes(page);
    await mockGenerateError(page);

    const chat = new ChatPage(page);
    await chat.goto();
    await chat.submitMessage("Create a building");

    const confirmBtn = page.locator("[data-testid='feature-confirm-button']");
    await expect(confirmBtn).toBeVisible({ timeout: 5000 });
    await confirmBtn.click();

    // Error status shows
    await expect(page.locator("[data-testid='job-status-error']")).toBeVisible({ timeout: 5000 });

    // App should reset to prompt step (effect in page.tsx resets on error)
    await expect(chat.chatPanel).toBeVisible({ timeout: 5000 });
  });
});
