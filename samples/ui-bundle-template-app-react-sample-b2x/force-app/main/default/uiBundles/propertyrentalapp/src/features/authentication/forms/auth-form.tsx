import { FieldGroup } from "../../../components/ui/field";
import { StatusAlert } from "../../../components/alerts/status-alert";
import { FooterLink } from "../footers/footer-link";
import { SubmitButton } from "./submit-button";
import { CardLayout } from "../../../components/layouts/card-layout";
import { useFormContext } from "../hooks/form";
import { useId } from "react";

/**
 * [Dev Note] A wrapper component that enforces consistent layout (Card) and error/success alert positioning
 * for all authentication forms.
 */
interface AuthFormProps extends Omit<React.ComponentProps<"form">, "onSubmit"> {
	title: string;
	description: string;
	error?: React.ReactNode;
	success?: React.ReactNode;
	submit: {
		text: string;
		loadingText?: string;
		disabled?: boolean;
	};
	footer?: {
		text?: string;
		link: string;
		linkText: string;
	};
}

/**
 * [Dev Note] Standardized Authentication Layout:
 * Wraps the specific logic of Login/Register forms with a consistent visual frame (Card),
 * title, and error alert placement. Extends form element props for flexibility.
 * This ensures all auth-related pages look and behave similarly.
 */
export function AuthForm({
	id: providedId,
	title,
	description,
	error,
	success,
	children,
	submit,
	footer,
	...props
}: AuthFormProps) {
	const form = useFormContext();
	const generatedId = useId();
	const id = providedId ?? generatedId;

	return (
		<CardLayout title={title} description={description}>
			<div className="space-y-6">
				{/* [Dev Note] Global form error alert (e.g. "Invalid Credentials") */}
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
					<SubmitButton
						form={id}
						label={submit.text}
						loadingLabel={submit.loadingText}
						disabled={submit.disabled}
						className="mt-6"
					/>
				</form>
				{/* [Dev Note] Navigation links (e.g. "Forgot Password?") */}
				{footer && <FooterLink text={footer.text} to={footer.link} linkText={footer.linkText} />}
			</div>
		</CardLayout>
	);
}
