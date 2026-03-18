import { Button } from "../../../../components/ui/button";
import { Spinner } from "../../../../components/ui/spinner";
import { cn } from "../../../../lib/utils";
import { useFormContext } from "../../hooks/form";

interface SubmitButtonProps extends Omit<React.ComponentProps<typeof Button>, "type" | "disabled"> {
	/** Button text when not submitting */
	label: string;
	/** Button text while submitting */
	loadingLabel?: string;
	/** Form id to associate with (for buttons outside form element) */
	form?: string;
}

const isSubmittingSelector = (state: { isSubmitting: boolean }) => state.isSubmitting;

/**
 * Submit button that subscribes to form submission state.
 * Disables interaction during submission and provides visual feedback.
 */
export function SubmitButton({
	label,
	loadingLabel = "Applying…",
	className,
	form: formId,
	...props
}: SubmitButtonProps) {
	const form = useFormContext();
	return (
		<form.Subscribe selector={isSubmittingSelector}>
			{(isSubmitting: boolean) => (
				<Button
					type="submit"
					form={formId}
					className={cn("w-full", className)}
					disabled={isSubmitting}
					aria-label={isSubmitting ? loadingLabel : label}
					aria-busy={isSubmitting}
					{...props}
				>
					{isSubmitting && <Spinner className="mr-2" aria-hidden="true" />}
					<span aria-live="polite">{isSubmitting ? loadingLabel : label}</span>
				</Button>
			)}
		</form.Subscribe>
	);
}
