import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router";
import { z } from "zod";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/platform-sdk";
import { ROUTES } from "../authenticationConfig";
import { emailSchema, getStartUrl, type AuthResponse } from "../authHelpers";
import { ApiError, handleApiResponse } from "../utils/helpers";

const loginSchema = z.object({
	email: emailSchema,
	password: z.string().min(1, "Password is required"),
});

export default function Login() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const [submitError, setSubmitError] = useState<React.ReactNode>(null);

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
				const result = await handleApiResponse<AuthResponse>(response);
				if (result?.redirectUrl) {
					// Hard navigate to the URL which establishes the server session cookie
					window.location.replace(result.redirectUrl);
				} else {
					// In case redirectUrl is null, navigate to home
					navigate("/", { replace: true });
				}
			} catch (err) {
				console.error("Login failed", err);
				if (err instanceof ApiError) {
					setSubmitError(
						err.errors.length === 1 ? (
							err.errors[0]
						) : (
							<ul>
								{err.errors.map((e, i) => (
									<li key={i}>{e}</li>
								))}
							</ul>
						),
					);
				} else {
					setSubmitError("Login failed");
				}
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
