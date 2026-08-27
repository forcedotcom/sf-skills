// Reference patterns for typing an LWC. Members are illustrative — copy the
// shapes you need into your own class.

import { LightningElement, api } from 'lwc';

interface DataItem {
  id: string;
  name: string;
}

export default class TypePatternsExample extends LightningElement {
  // Property types
  @api title: string = '';
  @api count: number = 0;
  @api isVisible: boolean = false;
  @api items: string[] = [];
  @api config: { enabled: boolean; name: string } = { enabled: false, name: '' };
  @api optionalProp?: string;

  // Method types
  @api
  handleClick(): void {
    /* ... */
  }

  @api
  updateItem(id: string, data: { name: string; value: number }): Promise<void> {
    return Promise.resolve();
  }

  @api
  async loadData(): Promise<DataItem[]> {
    return [];
  }

  // Event handlers
  handleButtonClick(event: MouseEvent): void {
    /* ... */
  }

  handleCustomEvent(event: CustomEvent<{ detail: string }>): void {
    /* ... */
  }
}
