import { FieldGroup } from "../../../../components/ui/field";
import { StatusAlert } from "../../../../components/alerts/status-alert";
import { CardLayout } from "../../../../components/layouts/card-layout";
import { SubmitButton } from "./submit-button";
import { Button } from "../../../../components/ui/button";
import { useFormContext } from "../../hooks/form";
import { useId, useEffect, useRef } from "react";

const SUCCESS_AUTO_DISMISS_DELAY = 3000;

interface FiltersFormProps extends Omit<React.ComponentProps<"form">, "onSubmit"> {
	title: string;
	description?: string;
	error?: React.ReactNode;
	success?: React.ReactNode;
	submit: {
		text: string;
		loadingText?: string;
	};
	reset?: {
		text: string;
		onReset: () => void;
	};
	onSuccessDismiss?: () => void;
}

/**
 * Wrapper component that provides consistent layout and error/success alert positioning
 * for all filter forms.
 */
export function FiltersForm({
	id: providedId,
	title,
	description,
	error,
	success,
	children,
	submit,
	reset,
	onSuccessDismiss,
	...props
}: FiltersFormProps) {
	const form = useFormContext();
	const generatedId = useId();
	const id = providedId ?? generatedId;

	const isSubmittingSelector = (state: { isSubmitting: boolean }) => state.isSubmitting;
	const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(() => {
		if (timeoutRef.current) {
			clearTimeout(timeoutRef.current);
			timeoutRef.current = null;
		}

		if (success && onSuccessDismiss) {
			timeoutRef.current = setTimeout(() => {
				onSuccessDismiss();
				timeoutRef.current = null;
			}, SUCCESS_AUTO_DISMISS_DELAY);
		}

		return () => {
			if (timeoutRef.current) {
				clearTimeout(timeoutRef.current);
				timeoutRef.current = null;
			}
		};
	}, [success, onSuccessDismiss]);

	return (
		<CardLayout title={title} description={description}>
			<div className="space-y-6">
				{error && <StatusAlert variant="error">{error}</StatusAlert>}
				{success && <StatusAlert variant="success">{success}</StatusAlert>}

				<form
					id={id}
					onSubmit={(e) => {
						e.preventDefault();
						e.stopPropagation();
						form.handleSubmit();
					}}
					{...props}
				>
					<FieldGroup>{children}</FieldGroup>
					<div className="flex flex-col sm:flex-row gap-2 pt-4">
						<SubmitButton
							form={id}
							label={submit.text}
							loadingLabel={submit.loadingText}
							className="flex-1"
						/>
						{reset && (
							<form.Subscribe selector={isSubmittingSelector}>
								{(isSubmitting: boolean) => (
									<Button
										type="button"
										variant="outline"
										onClick={reset.onReset}
										className="flex-1"
										disabled={isSubmitting}
									>
										{reset.text}
									</Button>
								)}
							</form.Subscribe>
						)}
					</div>
				</form>
			</div>
		</CardLayout>
	);
}
