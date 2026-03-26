import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { z } from "zod";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/sdk-data";
import { ROUTES, AUTH_PLACEHOLDERS } from "../authenticationConfig";
import { emailSchema, passwordSchema, getStartUrl, type AuthResponse } from "../authHelpers";
import { handleApiResponse, getErrorMessage } from "../utils/helpers";

const registerSchema = z
	.object({
		firstName: z.string().trim().min(1, "First name is required"),
		lastName: z.string().trim().min(1, "Last name is required"),
		email: emailSchema,
		password: passwordSchema,
		confirmPassword: z.string().min(1, "Please confirm your password"),
		startUrl: z.string(),
	})
	.refine((data) => data.password === data.confirmPassword, {
		message: "Passwords do not match",
		path: ["confirmPassword"],
	});

export default function Register() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: {
			firstName: "",
			lastName: "",
			email: "",
			password: "",
			confirmPassword: "",
			startUrl: getStartUrl(searchParams) || "",
		},
		validators: { onChange: registerSchema, onSubmit: registerSchema },
		onSubmit: async ({ value: formFieldValues }) => {
			setSubmitError(null);
			try {
				// [Dev Note] Salesforce Integration:
				// We use the Data SDK fetch to make an authenticated (or guest) call to Salesforce.
				// "/services/apexrest/auth/register" refers to a custom Apex Class exposed as a REST resource.
				// You must ensure this Apex class exists in your org and handles registration
				// (e.g., duplicate checks and user creation such as Site.createExternalUser).
				const { confirmPassword, ...request } = formFieldValues;
				const sdk = await createDataSDK();
				const response = await sdk.fetch!("/services/apexrest/auth/register", {
					method: "POST",
					body: JSON.stringify({ request }),
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json",
					},
				});
				const result = await handleApiResponse<AuthResponse>(response, "Registration failed");
				if (result?.redirectUrl) {
					// Hard navigate to the URL which logs the new user in
					window.location.replace(result.redirectUrl);
				} else {
					// In case redirectUrl is null, redirect to the login page
					navigate(ROUTES.LOGIN.PATH, { replace: true });
				}
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Registration failed"));
			}
		},
		onSubmitInvalid: () => {},
	});

	return (
		<CenteredPageLayout title={ROUTES.REGISTER.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Sign Up"
					description="Enter your information to create an account"
					error={submitError}
					submit={{ text: "Create an account", loadingText: "Creating account…" }}
					footer={{
						text: "Already have an account?",
						link: ROUTES.LOGIN.PATH,
						linkText: "Sign in",
					}}
				>
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 items-start">
						<form.AppField name="firstName">
							{(field) => (
								<field.TextField
									label="First name"
									placeholder={AUTH_PLACEHOLDERS.FIRST_NAME}
									autoComplete="given-name"
								/>
							)}
						</form.AppField>
						<form.AppField name="lastName">
							{(field) => (
								<field.TextField
									label="Last name"
									placeholder={AUTH_PLACEHOLDERS.LAST_NAME}
									autoComplete="family-name"
								/>
							)}
						</form.AppField>
					</div>
					<form.AppField name="email">
						{(field) => <field.EmailField label="Email" />}
					</form.AppField>
					<form.AppField name="password">
						{(field) => (
							<field.PasswordField
								label="Password"
								placeholder={AUTH_PLACEHOLDERS.PASSWORD_CREATE}
								autoComplete="new-password"
							/>
						)}
					</form.AppField>
					<form.AppField name="confirmPassword">
						{(field) => (
							<field.PasswordField
								label="Confirm Password"
								placeholder={AUTH_PLACEHOLDERS.PASSWORD_CONFIRM}
								autoComplete="new-password"
							/>
						)}
					</form.AppField>
				</AuthForm>
			</form.AppForm>
		</CenteredPageLayout>
	);
}
