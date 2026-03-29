import type { ComponentProps } from "react";

export const nonNegativeNumberInputProps: ComponentProps<"input"> = {
	min: 0,
	onKeyDown: (event) => {
		if (event.key === "-" || event.key === "Minus") event.preventDefault();
	},
	onPaste: (event) => {
		if (event.clipboardData.getData("text").includes("-")) event.preventDefault();
	},
};
