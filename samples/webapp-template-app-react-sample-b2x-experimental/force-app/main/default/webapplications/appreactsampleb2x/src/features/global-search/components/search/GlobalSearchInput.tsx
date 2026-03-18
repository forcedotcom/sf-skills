/**
 * GlobalSearchInput Component
 *
 * Search input with two actions: Search (navigate to results for query) and
 * Browse All (navigate to same results UI with all records for the object).
 */
import { useState, useCallback, useMemo, useId } from "react";
import type { KeyboardEvent, ChangeEvent } from "react";
import { useNavigate } from "react-router";
import { Card, CardContent } from "../../../../components/ui/card";
import { Input } from "../../../../components/ui/input";
import { Button } from "../../../../components/ui/button";
import { Search } from "lucide-react";
import { OBJECT_API_NAMES } from "../../constants";
import { useObjectInfoBatch } from "../../hooks/useObjectInfoBatch";

const BROWSE_SEGMENT = "browse__all";

const FALLBACK_LABEL_PLURAL = "records";

export function GlobalSearchInput() {
	const [searchQuery, setSearchQuery] = useState("");
	const navigate = useNavigate();
	const inputId = useId();
	const searchButtonId = useId();
	const browseButtonId = useId();
	const inputDescriptionId = `${inputId}-description`;
	const { objectInfos } = useObjectInfoBatch([...OBJECT_API_NAMES]);
	const labelPlural = (objectInfos[0]?.labelPlural as string | undefined) ?? FALLBACK_LABEL_PLURAL;

	const handleInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
		setSearchQuery(e.target.value);
	}, []);

	const handleSearch = useCallback(() => {
		const trimmed = searchQuery.trim();
		if (trimmed) {
			navigate(`/global-search/${encodeURIComponent(trimmed)}`);
		}
	}, [searchQuery, navigate]);

	const handleBrowseAll = useCallback(() => {
		navigate(`/global-search/${BROWSE_SEGMENT}`);
	}, [navigate]);

	const handleKeyDown = useCallback(
		(e: KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				e.preventDefault();
				handleSearch();
			}
		},
		[handleSearch],
	);

	const isSearchDisabled = useMemo(() => !searchQuery.trim(), [searchQuery]);

	return (
		<div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
			<Card className="w-full">
				<CardContent className="pt-6">
					<div className="flex flex-col sm:flex-row gap-3">
						<div className="flex-1 relative">
							<Search
								className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-600"
								aria-hidden="true"
							/>
							<Input
								id={inputId}
								type="search"
								placeholder={`Search for ${labelPlural}`}
								value={searchQuery}
								onChange={handleInputChange}
								onKeyDown={handleKeyDown}
								className="pl-10"
								aria-label={`Search for ${labelPlural}`}
								aria-describedby={inputDescriptionId}
							/>
							<p id={inputDescriptionId} className="sr-only">
								Enter your search query and press Enter or click Search. Or click Browse All to see
								all {labelPlural}.
							</p>
						</div>

						<div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
							<Button
								id={searchButtonId}
								onClick={handleSearch}
								disabled={isSearchDisabled}
								className="w-full sm:w-auto"
								aria-label="Search"
								aria-describedby={inputDescriptionId}
								variant="default"
							>
								<Search className="h-4 w-4 mr-2" aria-hidden="true" />
								Search
							</Button>
							<Button
								id={browseButtonId}
								variant="outline"
								onClick={handleBrowseAll}
								className="w-full sm:w-auto"
								aria-label={`Browse all ${labelPlural}`}
								aria-describedby={inputDescriptionId}
							>
								Browse All {labelPlural}
							</Button>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
