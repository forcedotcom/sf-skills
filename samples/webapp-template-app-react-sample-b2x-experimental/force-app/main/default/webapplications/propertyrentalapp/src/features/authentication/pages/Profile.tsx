import { useState, useEffect } from "react";
import { z } from "zod";

import { CenteredPageLayout } from "../layout/centered-page-layout";
import { CardSkeleton } from "../layout/card-skeleton";
import { AuthForm } from "../forms/auth-form";
import { useAppForm } from "../hooks/form";
import { ROUTES } from "../authenticationConfig";
import { emailSchema } from "../authHelpers";
import { getErrorMessage } from "../utils/helpers";
import { getUser } from "../context/AuthContext";
import { fetchUserProfile, updateUserProfile } from "../api/userProfileApi";

const optionalString = z
	.string()
	.trim()
	.transform((val) => (val === "" ? null : val))
	.nullable()
	.optional();

const profileSchema = z.object({
	FirstName: z.string().trim().min(1, "First name is required"),
	LastName: z.string().trim().min(1, "Last name is required"),
	Email: emailSchema,
	Phone: optionalString,
	Street: optionalString,
	City: optionalString,
	State: optionalString,
	PostalCode: optionalString,
	Country: optionalString,
});

type ProfileFormValues = z.infer<typeof profileSchema>;

export default function Profile() {
	const user = getUser();
	const [profile, setProfile] = useState<ProfileFormValues | null>(null);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [success, setSuccess] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);

	const form = useAppForm({
		defaultValues: {} as ProfileFormValues,
		validators: { onChange: profileSchema, onSubmit: profileSchema },
		onSubmit: async ({ value }) => {
			setSubmitError(null);
			setSuccess(false);
			try {
				const updated = await updateUserProfile<Partial<ProfileFormValues>>(user.id, value);
				// Merge with submitted values so missing fields (e.g. due to FLS) don't break the form
				setProfile({
					FirstName: updated.FirstName ?? value.FirstName ?? "",
					LastName: updated.LastName ?? value.LastName ?? "",
					Email: updated.Email ?? value.Email ?? "",
					Phone: updated.Phone ?? value.Phone ?? null,
					Street: updated.Street ?? value.Street ?? null,
					City: updated.City ?? value.City ?? null,
					State: updated.State ?? value.State ?? null,
					PostalCode: updated.PostalCode ?? value.PostalCode ?? null,
					Country: updated.Country ?? value.Country ?? null,
				});
				setSuccess(true);
				window.scrollTo({ top: 0, behavior: "smooth" });
			} catch (err) {
				setSubmitError(getErrorMessage(err, "Failed to update profile"));
			}
		},
		onSubmitInvalid: () => {},
	});

	useEffect(() => {
		let mounted = true;
		fetchUserProfile<Partial<ProfileFormValues>>(user.id)
			.then((data) => {
				if (mounted) {
					// Merge with defaults so missing fields (e.g. due to FLS) don't break the form
					setProfile({
						FirstName: data.FirstName ?? "",
						LastName: data.LastName ?? "",
						Email: data.Email ?? "",
						Phone: data.Phone ?? null,
						Street: data.Street ?? null,
						City: data.City ?? null,
						State: data.State ?? null,
						PostalCode: data.PostalCode ?? null,
						Country: data.Country ?? null,
					});
				}
			})
			.catch((err: any) => {
				if (mounted) {
					setLoadError(getErrorMessage(err, "Failed to load profile"));
				} else {
					console.error("Failed to load profile", err);
				}
			});
		return () => {
			mounted = false;
		};
	}, [user.id]);

	useEffect(() => {
		if (profile) {
			const formData = profileSchema.parse(profile);
			form.reset(formData);
		}
	}, [profile]);

	if (!profile && !loadError) {
		return <CardSkeleton contentMaxWidth="md" loadingText="Loading profile…" />;
	}

	return (
		<CenteredPageLayout contentMaxWidth="md" title={ROUTES.PROFILE.TITLE}>
			<form.AppForm>
				<AuthForm
					title="Profile"
					description="Update your account information"
					error={loadError ?? submitError}
					success={success && "Profile updated!"}
					submit={{ text: "Save Changes", loadingText: "Saving…" }}
					footer={{ link: ROUTES.CHANGE_PASSWORD.PATH, linkText: "Change password" }}
				>
					<form.AppField name="Email">
						{(field) => <field.EmailField label="Email" disabled />}
					</form.AppField>
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 items-start">
						<form.AppField name="FirstName">
							{(field) => <field.TextField label="First name" autoComplete="given-name" />}
						</form.AppField>
						<form.AppField name="LastName">
							{(field) => <field.TextField label="Last name" autoComplete="family-name" />}
						</form.AppField>
					</div>
					<form.AppField name="Phone">
						{(field) => <field.TextField label="Phone" type="tel" autoComplete="tel" />}
					</form.AppField>
					<form.AppField name="Street">
						{(field) => <field.TextField label="Street" autoComplete="street-address" />}
					</form.AppField>
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 items-start">
						<form.AppField name="City">
							{(field) => <field.TextField label="City" autoComplete="address-level2" />}
						</form.AppField>
						<form.AppField name="State">
							{(field) => <field.TextField label="State" autoComplete="address-level1" />}
						</form.AppField>
					</div>
					<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 items-start">
						<form.AppField name="PostalCode">
							{(field) => <field.TextField label="Postal Code" autoComplete="postal-code" />}
						</form.AppField>
						<form.AppField name="Country">
							{(field) => <field.TextField label="Country" autoComplete="country-name" />}
						</form.AppField>
					</div>
				</AuthForm>
			</form.AppForm>
		</CenteredPageLayout>
	);
}
