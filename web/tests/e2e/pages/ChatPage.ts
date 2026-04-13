import type { Locator, Page } from "@playwright/test";

export class ChatPage {
  readonly page: Page;
  readonly chatPanel: Locator;
  readonly chatInput: Locator;
  readonly nextButton: Locator;
  readonly voiceButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.chatPanel = page.locator("[data-testid='chat-panel']");
    this.chatInput = page.locator("[data-testid='chat-input']");
    this.nextButton = page.locator("[data-testid='next-button']");
    this.voiceButton = page.locator("[data-testid='voice-button']");
  }

  async goto() {
    await this.page.goto("/");
  }

  async fillMessage(message: string) {
    await this.chatInput.fill(message);
  }

  async clickNext() {
    await this.nextButton.click();
  }

  async submitMessage(message: string) {
    await this.fillMessage(message);
    await this.clickNext();
  }
}
