/**
 * GlobalSearchBox — pure launcher component for global search.
 *
 * A self-contained search input + button that navigates to `/search?q=...`
 * when the user submits a query of at least MIN_QUERY_LENGTH characters.
 *
 * Props are purely cosmetic (className, placeholder, autoFocus) — all behavior
 * (the gate, the route, the query key) is owned by this component, not the caller.
 *
 * Usage:
 * ```tsx
 * import { GlobalSearchBox } from "../features/search";
 * <GlobalSearchBox className="mb-8" placeholder="Search everything..." />
 * ```
 */

import { Search } from "lucide-react";
import { useId, useState } from "react";
import { useNavigate } from "react-router";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { GLOBAL_QUERY_KEY } from "../utils/filterUtils";
import { MIN_QUERY_LENGTH } from "../constants";

export interface GlobalSearchBoxProps {
	/** Optional CSS class for container styling/placement. */
	className?: string;
	/** Placeholder text for the search input. */
	placeholder?: string;
	/** Whether the input should autofocus on mount. */
	autoFocus?: boolean;
	/**
	 * Accessible (screen-reader) label for the input. Exposed as a prop so
	 * callers can localize it; defaults to English. */
	label?: string;
	/** Visible text for the submit button. Exposed for localization. */
	submitLabel?: string;
	/**
	 * Minimum length of keyword required by search. `{min}` is replaced with
	 * {@link MIN_QUERY_LENGTH}. Exposed for localization. */
	minLengthHint?: string;
}

export function GlobalSearchBox({
	className,
	placeholder = "Search…",
	autoFocus,
	label = "Search",
	submitLabel = "Search",
	minLengthHint = "Enter at least {min} characters to search.",
}: GlobalSearchBoxProps) {
	const navigate = useNavigate();
	const [text, setText] = useState("");
	const inputId = useId();
	const hintId = useId();

	const canSearch = text.trim().length >= MIN_QUERY_LENGTH;
	const hintText = minLengthHint.replace("{min}", String(MIN_QUERY_LENGTH));

	const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		if (!canSearch) return;
		const params = `?${GLOBAL_QUERY_KEY}=${encodeURIComponent(text.trim())}`;
		navigate(`/search${params}`);
	};

	return (
		<form onSubmit={handleSubmit} className={className} role="search">
			<label htmlFor={inputId} className="sr-only">
				{label}
			</label>
			<div className="flex gap-2">
				<div className="relative flex-1">
					<Search
						aria-hidden="true"
						className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
					/>
					<Input
						id={inputId}
						type="text"
						value={text}
						onChange={(e) => setText(e.target.value)}
						placeholder={placeholder}
						autoFocus={autoFocus}
						className="pl-9"
						aria-describedby={hintId}
					/>
				</div>
				<Button type="submit" disabled={!canSearch}>
					{submitLabel}
				</Button>
			</div>
			<p id={hintId} className="sr-only">
				{hintText}
			</p>
		</form>
	);
}
