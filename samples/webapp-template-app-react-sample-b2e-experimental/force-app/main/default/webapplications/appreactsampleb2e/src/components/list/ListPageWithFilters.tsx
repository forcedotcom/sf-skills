import type { ReactNode } from "react";
import type { Filter } from "../../features/global-search/types/filters/filters";
import { PageContainer } from "../layout/PageContainer";
import { PageLoadingState } from "../feedback/PageLoadingState";
import { PageErrorState } from "../feedback/PageErrorState";
import { FilterErrorAlert } from "../feedback/FilterErrorAlert";
import { ListPageFilterRow } from "../filters/ListPageFilterRow";

/** Compatible with feature picklist option shape. */
interface PicklistOption {
	label?: string;
	value: string;
}

export interface ListPageWithFiltersProps {
	filterProps: {
		filters: Filter[];
		picklistValues: Record<string, PicklistOption[]>;
		formValues: Record<string, string>;
		onFormValueChange: (key: string, value: string) => void;
		onApply: () => void;
		onReset: () => void;
		ariaLabel: string;
	};
	filterError: string | null;
	loading: boolean;
	error: string | null;
	loadingMessage: string;
	isEmpty: boolean;
	/** When set, a search input is shown that syncs with URL ?q= and drives list search. */
	searchPlaceholder?: string;
	searchAriaLabel?: string;
	children: ReactNode;
}

export function ListPageWithFilters({
	filterProps,
	filterError,
	loading,
	error,
	loadingMessage,
	isEmpty,
	children,
}: ListPageWithFiltersProps) {
	if (error) {
		return <PageErrorState message={error} />;
	}

	if (loading && isEmpty) {
		return <PageLoadingState message={loadingMessage} />;
	}

	return (
		<PageContainer>
			<div className="max-w-7xl mx-auto space-y-6">
				<ListPageFilterRow
					filters={filterProps.filters}
					picklistValues={filterProps.picklistValues}
					formValues={filterProps.formValues}
					onFormValueChange={filterProps.onFormValueChange}
					onApply={filterProps.onApply}
					onReset={filterProps.onReset}
					ariaLabel={filterProps.ariaLabel}
				/>
				{filterError && <FilterErrorAlert message={filterError} />}
				{children}
			</div>
		</PageContainer>
	);
}
