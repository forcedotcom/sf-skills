import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { createDataSDK } from "@salesforce/platform-sdk";
import { getStartUrl } from "../authHelpers";

/**
 * Social Login (IDP) Component for React Experience Cloud Sites.
 *
 * Replicates the OOTB community_login/socialLogin LWC behavior which does not
 * render on React (Site Container) sites due to a platform restriction
 * (isSiteContainer check in node-loginsettings.ftl).
 *
 * Behavior:
 * - On mount, fetches configured Auth Providers + SAML Providers
 * - If only one IDP is configured and username/password is disabled, auto-redirects
 * - Renders a button per provider with icon (Auth Providers) or without (SAML)
 * - On click, redirects to the SSO URL to initiate the OAuth/SAML flow
 *
 * Backend: UIBundleSocialLoginConfig.cls (Apex REST endpoint)
 * Uses: Auth.AuthConfiguration API
 */

interface AuthProviderInfo {
	developerName: string;
	friendlyName: string;
	iconUrl: string | null;
	ssoUrl: string;
}

interface SamlProviderInfo {
	id: string;
	masterLabel: string;
	ssoUrl: string;
}

interface SocialLoginConfigResponse {
	authProviders: AuthProviderInfo[];
	samlProviders: SamlProviderInfo[];
	autoRedirectUrl: string | null;
}

interface SocialLoginProps {
	/** Whether to show header text above buttons. Default: true */
	showHeader?: boolean;
	/** Header text. Default: "Or log in using:" */
	headerText?: string;
}

async function fetchSocialLoginConfig(startUrl: string): Promise<SocialLoginConfigResponse | null> {
	try {
		const sdk = await createDataSDK();
		const response = await sdk.fetch!(
			`/services/apexrest/auth/social-login-config?startURL=${encodeURIComponent(startUrl)}`,
			{
				method: "GET",
				headers: { Accept: "application/json" },
			},
		);

		if (!response.ok) {
			return null;
		}

		return await response.json();
	} catch {
		return null;
	}
}

export function SocialLogin({
	showHeader = true,
	headerText = "Or log in using:",
}: SocialLoginProps) {
	const [searchParams] = useSearchParams();
	const startUrl = getStartUrl(searchParams);

	const [authProviders, setAuthProviders] = useState<AuthProviderInfo[]>([]);
	const [samlProviders, setSamlProviders] = useState<SamlProviderInfo[]>([]);

	useEffect(() => {
		fetchSocialLoginConfig(startUrl).then((config) => {
			if (!config) return;

			if (config.autoRedirectUrl) {
				window.location.assign(config.autoRedirectUrl);
				return;
			}

			setAuthProviders(config.authProviders || []);
			setSamlProviders(config.samlProviders || []);
		});
	}, [startUrl]);

	const hasProviders = authProviders.length > 0 || samlProviders.length > 0;

	if (!hasProviders) return null;

	return (
		<div className="mt-6">
			{showHeader && (
				<div className="relative">
					<div className="absolute inset-0 flex items-center">
						<span className="w-full border-t" />
					</div>
					<div className="relative flex justify-center text-xs uppercase">
						<span className="bg-background px-2 text-muted-foreground">{headerText}</span>
					</div>
				</div>
			)}

			<div className="mt-4 grid gap-2">
				{authProviders.map((provider) => (
					<button
						key={provider.developerName}
						type="button"
						onClick={() => window.location.assign(provider.ssoUrl)}
						aria-label={`Sign in with ${provider.friendlyName}`}
						className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
					>
						{provider.iconUrl && (
							<img src={provider.iconUrl} alt="" className="h-4 w-4" aria-hidden="true" />
						)}
						<span>{provider.friendlyName}</span>
					</button>
				))}

				{samlProviders.map((provider) => (
					<button
						key={provider.id}
						type="button"
						onClick={() => window.location.assign(provider.ssoUrl)}
						aria-label={`Sign in with ${provider.masterLabel}`}
						className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
					>
						<span>{provider.masterLabel}</span>
					</button>
				))}
			</div>
		</div>
	);
}
