import type { Locator, Page } from "@playwright/test";

export class AppPage {
  readonly page: Page;
  readonly tabText: Locator;
  readonly tabDraw: Locator;
  readonly tabUpload: Locator;
  readonly dropZone: Locator;
  readonly openIfcButton: Locator;
  readonly floorPlanUpload: Locator;
  readonly jobStatusArea: Locator;

  constructor(page: Page) {
    this.page = page;
    this.tabText = page.locator("[data-testid='tab-text']");
    this.tabDraw = page.locator("[data-testid='tab-draw']");
    this.tabUpload = page.locator("[data-testid='tab-upload']");
    this.dropZone = page.locator("[data-testid='ifc-drop-zone']");
    this.openIfcButton = page.locator("[data-testid='open-ifc-button']");
    this.floorPlanUpload = page.locator("[data-testid='floorplan-upload']");
    this.jobStatusArea = page.locator("[data-testid='job-status-area']");
  }

  async goto() {
    await this.page.goto("/");
  }

  async switchToTextTab() {
    await this.tabText.click();
  }

  async switchToDrawTab() {
    await this.tabDraw.click();
  }

  async switchToUploadTab() {
    await this.tabUpload.click();
  }

  jobStatus(status: string) {
    return this.page.locator(`[data-testid='job-status-${status}']`);
  }

  get jobErrorMessage() {
    return this.page.locator("[data-testid='job-error-message']");
  }
}
