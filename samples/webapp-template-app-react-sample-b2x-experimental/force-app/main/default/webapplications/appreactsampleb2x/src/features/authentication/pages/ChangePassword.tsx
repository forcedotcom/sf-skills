import { useState } from "react";
import { Link } from "react-router";
import { z } from "zod";
import { CenteredPageLayout } from "../layout/centered-page-layout";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { createDataSDK } from "@salesforce/sdk-data";
import { ROUTES, AUTH_PLACEHOLDERS } from "../authenticationConfig";
import { newPasswordSchema } from "../authHelpers";
import { handleApiResponse, getErrorMessage } from "../utils/helpers";

const changePasswordSchema = z
	.object({
		currentPassword: z.string().min(1, "Current password is required"),
	})
	.and(newPasswordSchema);

export default function ChangePassword() {
	const [success, setSuccess] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
		validators: { onChange: changePasswordSchema, onSubmit: changePasswordSchema },
		onSubmit: async ({ value: formFieldValues }) => {
			setSubmitError(null);
			setSuccess(false);
			try {
				// [Dev Note] Custom Apex Endpoint: /auth/change-password
				// You must ensure this Apex class exists in your org
				const sdk = await createDataSDK();
				const response = await sdk.fetch!("/services/apexrest/auth/change-password", {
					method: "POST",
					body: JSON.stringify({
						currentPassword: formFieldValues.currentPassword,
						newPassword: formFieldValues.newPassword,
					}),
					headers: {
						"Content-Type": "application/json",
						Accept: "application/json",
					},
				});
				await handleApiResponse(response, "Password change failed");
				setSuccess(true);
				form.reset();
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Password change failed"));
			}
		},
		onSubmitInvalid: () => {},
	});

	return (
		<CenteredPageLayout title={ROUTES.CHANGE_PASSWORD.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Change Password"
					description="Enter your current and new password below"
					error={submitError}
					success={
						success && (
							<>
								Password changed successfully!{" "}
								<Link to={ROUTES.PROFILE.PATH} className="underline">
									Back to Profile
								</Link>
							</>
						)
					}
					submit={{ text: "Change Password", loadingText: "Changing…", disabled: success }}
					footer={{ link: ROUTES.PROFILE.PATH, linkText: "Back to Profile" }}
				>
					<form.AppField name="currentPassword">
						{(field) => (
							<field.PasswordField
								label="Current Password"
								placeholder={AUTH_PLACEHOLDERS.PASSWORD}
								autoComplete="current-password"
								disabled={success}
							/>
						)}
					</form.AppField>
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
