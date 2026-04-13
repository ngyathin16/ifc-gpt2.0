import type { Locator, Page } from "@playwright/test";

export class FeaturePickerPage {
  readonly page: Page;
  readonly picker: Locator;
  readonly backButton: Locator;
  readonly confirmButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.picker = page.locator("[data-testid='feature-picker']");
    this.backButton = page.locator("[data-testid='feature-back-button']");
    this.confirmButton = page.locator("[data-testid='feature-confirm-button']");
  }

  async clickBack() {
    await this.backButton.click();
  }

  async clickConfirm() {
    await this.confirmButton.click();
  }
}
