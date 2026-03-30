import { useState, useCallback, type SubmitEvent } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CenteredPageLayout } from "@/features/authentication/layout/centered-page-layout";
import { Loader2 } from "lucide-react";
import { createContactUsLead } from "@/api/leads/leadApi";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { fetchUserProfile } from "@/features/authentication/api/userProfileApi";
import { useCachedAsyncData } from "@/features/object-search/hooks/useCachedAsyncData";
import type { UserInfo } from "@/api/leads/leadApi";

function SuccessCard() {
	return (
		<Card>
			<CardHeader>
				<CardTitle className="text-xl">Message sent</CardTitle>
			</CardHeader>
			<CardContent className="space-y-4">
				<p className="text-muted-foreground">
					Thank you for reaching out. We've received your message and will get back to you soon.
				</p>
				<Button asChild variant="outline">
					<Link to="/">Back to Home</Link>
				</Button>
				<Button asChild>
					<Link to="/contact">Send another message</Link>
				</Button>
			</CardContent>
		</Card>
	);
}

interface ContactFormProps {
	isAuthenticated: boolean;
	userInfo: UserInfo | null;
	onSubmit: (e: SubmitEvent<HTMLFormElement>) => void;
	submitting: boolean;
	submitError: string | null;
	loading?: boolean;
}

function ContactForm({
	isAuthenticated,
	userInfo,
	onSubmit,
	submitting,
	submitError,
	loading,
}: ContactFormProps) {
	const [firstName, setFirstName] = useState("");
	const [lastName, setLastName] = useState("");
	const [email, setEmail] = useState("");
	const [phone, setPhone] = useState("");
	const [subject, setSubject] = useState("");
	const [message, setMessage] = useState("");

	return (
		<Card className="relative">
			{loading && (
				<div className="absolute inset-0 z-10 flex items-center justify-center rounded-[inherit] bg-muted/60">
					<Loader2 className="size-8 animate-spin text-muted-foreground" />
					<span className="sr-only">Loading contact form…</span>
				</div>
			)}
			<CardHeader>
				<CardTitle className="text-lg">Send a message</CardTitle>
			</CardHeader>
			<CardContent>
				<form
					onSubmit={onSubmit}
					className="space-y-4"
					aria-disabled={loading}
					inert={loading ? true : undefined}
				>
					<div className="grid gap-4 sm:grid-cols-2">
						<div className="space-y-2">
							<Label htmlFor="contact-first">First name {!isAuthenticated && "*"}</Label>
							<Input
								id="contact-first"
								name="contact-first"
								type="text"
								value={isAuthenticated ? (userInfo?.FirstName ?? "") : firstName}
								onChange={(e) => setFirstName(e.target.value)}
								disabled={isAuthenticated}
								required={!isAuthenticated}
							/>
						</div>
						<div className="space-y-2">
							<Label htmlFor="contact-last">Last name {!isAuthenticated && "*"}</Label>
							<Input
								id="contact-last"
								name="contact-last"
								type="text"
								value={isAuthenticated ? (userInfo?.LastName ?? "") : lastName}
								onChange={(e) => setLastName(e.target.value)}
								disabled={isAuthenticated}
								required={!isAuthenticated}
							/>
						</div>
					</div>
					<div className="space-y-2">
						<Label htmlFor="contact-email">Email {!isAuthenticated && "*"}</Label>
						<Input
							id="contact-email"
							name="contact-email"
							type="email"
							value={isAuthenticated ? (userInfo?.Email ?? "") : email}
							onChange={(e) => setEmail(e.target.value)}
							disabled={isAuthenticated}
							required={!isAuthenticated}
						/>
					</div>
					<div className="space-y-2">
						<Label htmlFor="contact-phone">Phone</Label>
						<Input
							id="contact-phone"
							name="contact-phone"
							type="tel"
							value={isAuthenticated ? (userInfo?.Phone ?? "") : phone}
							onChange={(e) => setPhone(e.target.value)}
							disabled={isAuthenticated}
						/>
					</div>
					<div className="space-y-2">
						<Label htmlFor="contact-subject">Subject</Label>
						<Input
							id="contact-subject"
							name="contact-subject"
							type="text"
							value={subject}
							onChange={(e) => setSubject(e.target.value)}
							placeholder="e.g. General inquiry, Property question"
						/>
					</div>
					<div className="space-y-2">
						<Label htmlFor="contact-message">Message *</Label>
						<textarea
							id="contact-message"
							name="contact-message"
							rows={5}
							value={message}
							onChange={(e) => setMessage(e.target.value)}
							required
							className="min-h-[120px] w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
						/>
					</div>
					{submitError && (
						<p className="text-sm text-destructive">
							Something went wrong. Please try again later.
						</p>
					)}
					<Button type="submit" disabled={submitting} className="bg-teal-600 hover:bg-teal-700">
						{submitting ? "Sending…" : "Send message"}
					</Button>
				</form>
			</CardContent>
		</Card>
	);
}

export default function Contact() {
	const { isAuthenticated, loading, user } = useAuth();
	const [submitting, setSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [submitted, setSubmitted] = useState(false);

	const { data: userInfo } = useCachedAsyncData(
		() => {
			if (!isAuthenticated || !user?.id) return Promise.resolve(null);
			return fetchUserProfile<UserInfo>(user.id);
		},
		[isAuthenticated, user?.id],
		{ key: `contact-user-profile:${user?.id ?? ""}`, ttl: 300_000 },
	);

	const handleSubmit = useCallback(
		async (e: SubmitEvent<HTMLFormElement>) => {
			e.preventDefault();
			setSubmitError(null);
			setSubmitting(true);

			const form = e.currentTarget;
			const formData = new FormData(form);

			try {
				await createContactUsLead({
					FirstName: isAuthenticated
						? (userInfo?.FirstName ?? "")
						: (formData.get("contact-first") as string).trim(),
					LastName: isAuthenticated
						? (userInfo?.LastName ?? "")
						: (formData.get("contact-last") as string).trim(),
					Email: isAuthenticated
						? (userInfo?.Email ?? "")
						: (formData.get("contact-email") as string).trim(),
					Phone: isAuthenticated
						? userInfo?.Phone
						: (formData.get("contact-phone") as string)?.trim() || undefined,
					Subject: (formData.get("contact-subject") as string)?.trim() || undefined,
					Message: (formData.get("contact-message") as string).trim(),
				});
				setSubmitted(true);
			} catch (err) {
				setSubmitError(
					err instanceof Error ? err.message : "Something went wrong. Please try again.",
				);
			} finally {
				setSubmitting(false);
			}
		},
		[isAuthenticated, userInfo],
	);

	const isLoading = loading || (isAuthenticated && !userInfo);

	if (submitted) {
		return (
			<CenteredPageLayout contentMaxWidth="md">
				<h1 className="mb-2 text-2xl font-semibold text-foreground">Contact Us</h1>
				<p className="mb-6 text-muted-foreground">
					Have a question or feedback? Send us a message and we'll respond as soon as we can.
				</p>
				<SuccessCard />
			</CenteredPageLayout>
		);
	}

	return (
		<CenteredPageLayout contentMaxWidth="md">
			<h1 className="mb-2 text-2xl font-semibold text-foreground">Contact Us</h1>
			<p className="mb-6 text-muted-foreground">
				Have a question or feedback? Send us a message and we'll respond as soon as we can.
			</p>
			<ContactForm
				isAuthenticated={isAuthenticated}
				userInfo={userInfo}
				onSubmit={handleSubmit}
				submitting={submitting}
				submitError={submitError}
				loading={isLoading}
			/>
		</CenteredPageLayout>
	);
}
