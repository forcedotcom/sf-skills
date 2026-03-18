import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router";
import { z } from "zod";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/sdk-data";
import { ROUTES } from "../authenticationConfig";
import { emailSchema, getStartUrl, type AuthResponse } from "../authHelpers";
import { handleApiResponse, getErrorMessage } from "../utils/helpers";

const loginSchema = z.object({
	email: emailSchema,
	password: z.string().min(1, "Password is required"),
});

export default function Login() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: { email: "", password: "" },
		validators: { onChange: loginSchema, onSubmit: loginSchema },
		onSubmit: async ({ value }) => {
			setSubmitError(null);
			try {
				// [Dev Note] Salesforce Integration:
				// We use the Data SDK fetch to make an authenticated (or guest) call to Salesforce.
				// "/services/apexrest/auth/login" refers to a custom Apex REST resource.
				// You must ensure this Apex class exists in your org and handles the login logic
				// (e.g., creating a session or returning a token).
				const sdk = await createDataSDK();
				const response = await sdk.fetch!("/services/apexrest/auth/login", {
					method: "POST",
					body: JSON.stringify({
						email: value.email.trim().toLowerCase(),
						password: value.password,
						startUrl: getStartUrl(searchParams),
					}),
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json",
					},
				});
				const result = await handleApiResponse<AuthResponse>(response, "Login failed");
				if (result?.redirectUrl) {
					// Hard navigate to the URL which establishes the server session cookie
					window.location.replace(result.redirectUrl);
				} else {
					// In case redirectUrl is null, navigate to home
					navigate("/", { replace: true });
				}
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Login failed"));
			}
		},
		onSubmitInvalid: () => {},
	});

	return (
		<CenteredPageLayout title={ROUTES.LOGIN.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Login"
					description="Enter your email below to login to your account"
					error={submitError}
					submit={{ text: "Login", loadingText: "Logging in…" }}
					footer={{
						text: "Don't have an account?",
						link: ROUTES.REGISTER.PATH,
						linkText: "Sign up",
					}}
				>
					<form.AppField name="email">
						{(field) => <field.EmailField label="Email" />}
					</form.AppField>
					<form.AppField name="password">
						{(field) => (
							<field.PasswordField
								label="Password"
								labelAction={
									<Link
										to={ROUTES.FORGOT_PASSWORD.PATH}
										className="text-sm underline-offset-4 hover:underline"
									>
										Forgot your password?
									</Link>
								}
							/>
						)}
					</form.AppField>
				</AuthForm>
			</form.AppForm>
		</CenteredPageLayout>
	);
}
