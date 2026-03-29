import { Button } from "../../../components/ui/button";
import { Spinner } from "../../../components/ui/spinner";
import { cn } from "../../../lib/utils";
import { useFormContext } from "../hooks/form";

interface SubmitButtonProps extends Omit<React.ComponentProps<typeof Button>, "type"> {
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
 * UX Best Practice:
 * 1. Disables interaction immediately upon click (via isLoading) to prevent
 * accidental double-submissions.
 * 2. Provides immediate visual feedback (Spinner).
 */
export function SubmitButton({
	label,
	loadingLabel = "Submitting…",
	className,
	form: formId,
	disabled,
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
					disabled={isSubmitting || disabled}
					{...props}
				>
					{isSubmitting && <Spinner className="mr-2" aria-hidden="true" />}
					{isSubmitting ? loadingLabel : label}
				</Button>
			)}
		</form.Subscribe>
	);
}
