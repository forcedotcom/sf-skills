import { useState } from "react";
import { z } from "zod";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/sdk-data";
import { ROUTES, AUTH_PLACEHOLDERS } from "../authenticationConfig";
import { handleApiResponse, getErrorMessage } from "../utils/helpers";

const forgotPasswordSchema = z.object({
	username: z.string().trim().toLowerCase().email("Please enter a valid username"),
});

export default function ForgotPassword() {
	const [success, setSuccess] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: { username: "" },
		validators: { onChange: forgotPasswordSchema, onSubmit: forgotPasswordSchema },
		onSubmit: async ({ value }) => {
			setSubmitError(null);
			setSuccess(false);
			try {
				// [Dev Note] Custom Apex Endpoint: /auth/forgot-password
				// You must ensure this Apex class exists in your org
				const sdk = await createDataSDK();
				const response = await sdk.fetch!("/services/apexrest/auth/forgot-password", {
					method: "POST",
					body: JSON.stringify({ username: value.username.trim() }),
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json",
					},
				});
				await handleApiResponse(response, "Failed to send reset link");
				setSuccess(true);
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Failed to send reset link"));
			}
		},
		onSubmitInvalid: () => {},
	});

	return (
		<CenteredPageLayout title={ROUTES.FORGOT_PASSWORD.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Forgot Password"
					description="Enter your username and we'll send you a reset link"
					error={submitError}
					success={
						success &&
						"If that username exists in our system, you will receive a reset link shortly."
					}
					submit={{ text: "Send Reset Link", loadingText: "Sending…", disabled: success }}
					footer={{ text: "Remember your password?", link: ROUTES.LOGIN.PATH, linkText: "Sign in" }}
				>
					<form.AppField name="username">
						{(field) => (
							<field.TextField
								label="Username"
								placeholder={AUTH_PLACEHOLDERS.USERNAME}
								autoComplete="username"
								disabled={success}
							/>
						)}
					</form.AppField>
				</AuthForm>
			</form.AppForm>
		</CenteredPageLayout>
	);
}
