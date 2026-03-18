import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { CardLayout } from "../../../components/layouts/card-layout";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { StatusAlert } from "../../../components/alerts/status-alert";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/sdk-data";
import { ROUTES, AUTH_PLACEHOLDERS } from "../authenticationConfig";
import { newPasswordSchema } from "../authHelpers";
import { handleApiResponse, getErrorMessage } from "../utils/helpers";

export default function ResetPassword() {
	const [searchParams] = useSearchParams();
	const token = searchParams.get("token");
	const [success, setSuccess] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: { newPassword: "", confirmPassword: "" },
		validators: { onChange: newPasswordSchema, onSubmit: newPasswordSchema },
		onSubmit: async ({ value }) => {
			setSubmitError(null);
			setSuccess(false);
			try {
				// [Dev Note] Custom Apex Endpoint: /auth/reset-password
				// You must ensure this Apex class exists in your org
				const sdk = await createDataSDK();
				const response = await sdk.fetch!("/services/apexrest/auth/reset-password", {
					method: "POST",
					body: JSON.stringify({ token, newPassword: value.newPassword }),
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json",
					},
				});
				await handleApiResponse(response, "Password reset failed");
				setSuccess(true);
				// Scroll to top of page after successful submission so user sees it
				window.scrollTo({ top: 0, behavior: "smooth" });
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Password reset failed"));
			}
		},
		onSubmitInvalid: () => {},
	});

	if (!token) {
		return (
			<CenteredPageLayout title={ROUTES.RESET_PASSWORD.TITLE}>
				<CardLayout title="Reset Password">
					<StatusAlert>
						Reset token is invalid or expired.{" "}
						<Link to={ROUTES.FORGOT_PASSWORD.PATH} className="underline underline-offset-4">
							Request a new password reset link.
						</Link>
					</StatusAlert>
				</CardLayout>
			</CenteredPageLayout>
		);
	}

	return (
		<CenteredPageLayout title={ROUTES.RESET_PASSWORD.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Reset Password"
					description="Enter your new password below"
					error={submitError}
					success={
						success && (
							<>
								Password reset successfully!{" "}
								<Link to={ROUTES.LOGIN.PATH} className="underline">
									Sign in
								</Link>
							</>
						)
					}
					submit={{ text: "Reset Password", loadingText: "Resetting…" }}
					footer={{ text: "Remember your password?", link: ROUTES.LOGIN.PATH, linkText: "Sign in" }}
				>
					<form.AppField name="newPassword">
						{(field) => (
							<field.PasswordField
								label="New Password"
								placeholder={AUTH_PLACEHOLDERS.PASSWORD_NEW}
								autoComplete="new-password"
								disabled={success}
							/>
						)}
					</form.AppField>
					<form.AppField name="confirmPassword">
						{(field) => (
							<field.PasswordField
								label="Confirm Password"
								placeholder={AUTH_PLACEHOLDERS.PASSWORD_NEW_CONFIRM}
								autoComplete="new-password"
								disabled={success}
							/>
						)}
					</form.AppField>
				</AuthForm>
			</form.AppForm>
		</CenteredPageLayout>
	);
}
