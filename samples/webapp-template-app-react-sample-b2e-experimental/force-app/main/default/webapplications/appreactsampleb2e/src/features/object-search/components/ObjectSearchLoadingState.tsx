import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";

export interface ObjectSearchLoadingStateProps {
	/** Page title (e.g. "Applications") */
	title: string;
	/** Page description for the header */
	description: string;
	/** Filter row to show above the skeleton (e.g. ObjectSearchFilterRow) so layout stays consistent */
	filterRow: React.ReactNode;
	/** Skeleton content that reflects the rendered page (table, grid of cards, etc.) to avoid layout shift */
	children: React.ReactNode;
}

/**
 * Shared loading state for object-search pages. Renders the same layout (header + filters) with
 * skeleton content in place of the list/table. Pass page-specific skeleton as children.
 */
export function ObjectSearchLoadingState({
	title,
	description,
	filterRow,
	children,
}: ObjectSearchLoadingStateProps) {
	return (
		<>
			<PageHeader title={title} description={description} />
			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}
					{children}
				</div>
			</PageContainer>
		</>
	);
}
